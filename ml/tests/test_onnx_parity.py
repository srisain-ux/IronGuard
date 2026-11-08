import numpy as np
import onnx
import onnxruntime as ort
import pytest
import torch

from ironguard_ml.data import ROOT
from ironguard_ml.export import INPUT, OPSET, OUTPUTS, export, load_net
from ironguard_ml.features import MAX_TURNS, TURN_DIM
from ironguard_ml.preynet import PreyNet, pack

ARTIFACTS = ROOT / "ml/artifacts"
TOLERANCE = 1e-4  # §7: max abs diff over 50 random prefixes


def random_prefixes(n=50, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        k = int(rng.integers(1, MAX_TURNS + 1))
        emb = rng.normal(size=(k, TURN_DIM - 1))
        emb /= np.linalg.norm(emb, axis=1, keepdims=True)  # MiniLM vectors are L2-normalized
        out.append(np.hstack([emb, rng.integers(0, 2, (k, 1))]).astype(np.float32))
    return out


def assert_parity(net: PreyNet, onnx_path):
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    assert [o.name for o in session.get_outputs()] == list(OUTPUTS)
    worst = 0.0
    for seq in random_prefixes():
        with torch.no_grad():
            ref = net(*pack([seq]))
        got = dict(zip(OUTPUTS, session.run(None, {INPUT: seq[None]}), strict=True))
        for name in OUTPUTS:
            expected = ref[name].numpy()
            if name == "attention":
                expected = expected[:, : len(seq)]  # ONNX attention covers the real turns only
            assert got[name].shape == expected.shape, name
            worst = max(worst, float(np.abs(got[name] - expected).max()))
    assert worst < TOLERANCE, f"max abs diff {worst:.2e}"


def test_export_matches_pytorch(tmp_path):
    torch.manual_seed(0)
    net = PreyNet().eval()
    path = tmp_path / "preynet.onnx"
    export(net, path)
    assert not net.training  # export must not switch dropout back on in the caller's net
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    assert model.opset_import[0].version == OPSET
    assert_parity(net, path)


def test_committed_onnx_matches_committed_weights():
    if not (ARTIFACTS / "preynet.onnx").exists():
        pytest.skip("ml/artifacts/preynet.onnx not exported yet (run `make export`)")
    assert_parity(load_net(ARTIFACTS), ARTIFACTS / "preynet.onnx")
