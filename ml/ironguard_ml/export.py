"""`make export`: PreyNet → ONNX for the browser (MODEL_SPEC §7).

ONNX input `turn_vecs` float32 [batch, turns, 385], every turn real (the browser left-truncates
to the last 12). Outputs are the last turn's `family_logits` [batch, 7], `stage_logits` [batch, 5],
`tts_logits` [batch, 5], `attention` [batch, turns] and `features` [batch, 640].
"""

import argparse
from pathlib import Path

import torch
from torch import nn

from ironguard_ml.data import ROOT
from ironguard_ml.features import EMB_DIM, TURN_DIM
from ironguard_ml.preynet import PreyNet

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


def load_net(artifacts: Path) -> PreyNet:
    checkpoint = torch.load(artifacts / "preynet.pt", map_location="cpu", weights_only=True)
    net = PreyNet(**checkpoint["config"])
    net.load_state_dict(checkpoint["state_dict"])
    return net.eval()


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
    args = parser.parse_args()
    if not (args.artifacts / "preynet.pt").exists():
        parser.error(f"missing {args.artifacts / 'preynet.pt'} (run `make train`)")
    export(load_net(args.artifacts), args.out)
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes, opset {OPSET})")


if __name__ == "__main__":
    main()
