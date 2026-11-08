"""`make export`: PreyNet → ONNX for the browser (MODEL_SPEC §7) + the chloroplast negative bank.

ONNX input `turn_vecs` float32 [batch, turns, 385], every turn real (the browser left-truncates
to the last 12). Outputs are the last turn's `family_logits` [batch, 7], `stage_logits` [batch, 5],
`tts_logits` [batch, 5], `attention` [batch, turns] and `features` [batch, 640].
"""

import argparse
from pathlib import Path

import torch
from torch import nn

from ironguard_ml.chloroplast import build_negative_bank, save_bank
from ironguard_ml.data import DATA_DIR, ROOT
from ironguard_ml.features import EMB_DIM, TURN_DIM
from ironguard_ml.preynet import PreyNet, load_net
from ironguard_ml.train import load_splits

OPSET = 17
INPUT = "turn_vecs"
OUTPUTS = ("family_logits", "stage_logits", "tts_logits", "attention", "features")


class _AllTurns(nn.Module):
    """PreyNet.forward for one unpadded prefix per row (no mask input; parity-tested against it)."""

    def __init__(self, net: PreyNet):
        super().__init__()
        self.net = net

    def forward(self, turn_vecs):
        net = self.net
        states, _ = net.gru(net.proj(turn_vecs))
        h_t = states[:, -1]
        mask = torch.ones_like(turn_vecs[..., 0], dtype=torch.bool)
        pooled, alpha = net.attention(states, mask, h_t)
        features = torch.cat([pooled, h_t, turn_vecs[..., :EMB_DIM].mean(dim=1)], dim=1)
        return (net.family(features), net.next_stage(features), net.tts(features), alpha, features)


def export(net: PreyNet, out: Path) -> None:
    example = torch.zeros(1, 3, TURN_DIM)
    # export() restores the module's mode afterwards, so the wrapper itself must be in eval mode
    # (a train-mode wrapper would switch dropout back on in the caller's net).
    torch.onnx.export(
        _AllTurns(net).eval(), (example,), str(out), dynamo=False, opset_version=OPSET,
        input_names=[INPUT], output_names=list(OUTPUTS),
        dynamic_axes={INPUT: {0: "batch", 1: "turns"}, "attention": {0: "batch", 1: "turns"},
                      **{name: {0: "batch"} for name in OUTPUTS if name != "attention"}},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "ml/artifacts")
    parser.add_argument("--out", type=Path, default=ROOT / "ml/artifacts/preynet.onnx")
    parser.add_argument("--data", type=Path, default=DATA_DIR / "generated" / "v1",
                        help="dataset whose TRAIN split feeds the chloroplast negative bank")
    args = parser.parse_args()
    if not (args.artifacts / "preynet.pt").exists():
        parser.error(f"missing {args.artifacts / 'preynet.pt'} (run `make train`)")
    net = load_net(args.artifacts)
    export(net, args.out)
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes, opset {OPSET})")
    try:
        splits, _, _ = load_splits(args.data)
    except ValueError as exc:
        parser.error(str(exc))
    bank = save_bank(args.artifacts, *build_negative_bank(net, splits["train"]))
    print(f"Wrote {bank} ({bank.stat().st_size} bytes) from {len(splits['train'])} TRAIN conversations")


if __name__ == "__main__":
    main()
