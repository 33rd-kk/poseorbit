"""The detectors' first-use downloads, without the network: a stand-in for
huggingface_hub serves the files and records what it is asked."""

import hashlib
import io
import re
import zipfile
from pathlib import Path

import huggingface_hub
import pytest

from poseorbit import detect
from poseorbit.detect import DETECTOR_FILE, POSE_2D_FILE, POSE_3D_FILE, ModelFile, model_file

ONNX = b"pinned onnx"
REVISION = "0" * 40


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zipped(data: bytes) -> bytes:
    """`data` as the onnx inside a zip, with a fixed date so the bytes are the same each time."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(zipfile.ZipInfo("20230928/end2end.onnx", date_time=(2023, 9, 28, 0, 0, 0)), data)
    return buffer.getvalue()


PLAIN = ModelFile("o/r", REVISION, "onnx/m.onnx", _sha(ONNX), "m.onnx", _sha(ONNX))
ZIPPED = ModelFile("o/r", REVISION, "sdk/m.zip", _sha(_zipped(ONNX)), "m.onnx", _sha(ONNX))


@pytest.fixture
def hub(monkeypatch: pytest.MonkeyPatch):
    """Stands in for hf_hub_download: writes `served[filename]` into local_dir, as the real one does."""
    calls: list[dict] = []
    served = {PLAIN.filename: ONNX, ZIPPED.filename: _zipped(ONNX)}

    def fake(repo_id, filename, *, revision, local_dir):
        calls.append({"repo": repo_id, "filename": filename, "revision": revision})
        path = Path(local_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(served[filename])
        return str(path)

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fake)
    monkeypatch.setattr(detect, "_checked", set())
    return calls, served


def test_a_matching_file_is_used_without_a_download(tmp_path, hub):
    calls, _ = hub
    (tmp_path / "m.onnx").write_bytes(ONNX)
    assert model_file(PLAIN, tmp_path) == str(tmp_path / "m.onnx")
    assert calls == []


@pytest.mark.parametrize("spec", [PLAIN, ZIPPED], ids=["onnx", "zip"])
def test_a_file_that_does_not_match_is_fetched_again_from_the_pinned_commit(tmp_path, hub, spec):
    calls, _ = hub
    (tmp_path / "m.onnx").write_bytes(b"from main, before the pin" * 100_000)
    assert Path(model_file(spec, tmp_path)).read_bytes() == ONNX
    assert calls == [{"repo": "o/r", "filename": spec.filename, "revision": REVISION}]
    # Only the onnx stays: no download folder, no zip, no partial file.
    assert sorted(path.name for path in tmp_path.iterdir()) == ["m.onnx"]


@pytest.mark.parametrize("spec", [PLAIN, ZIPPED], ids=["onnx", "zip"])
def test_a_download_that_does_not_match_is_refused_and_leaves_nothing(tmp_path, hub, spec):
    _, served = hub
    served[spec.filename] = b"something else"
    with pytest.raises(RuntimeError, match="pinned SHA-256"):
        model_file(spec, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_zip_whose_onnx_does_not_match_is_refused(tmp_path, hub):
    _, served = hub
    served[ZIPPED.filename] = _zipped(b"another onnx")
    spec = ModelFile("o/r", REVISION, ZIPPED.filename, _sha(served[ZIPPED.filename]), "m.onnx", _sha(ONNX))
    with pytest.raises(RuntimeError, match="pinned SHA-256"):
        model_file(spec, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_checked_file_is_not_hashed_again(tmp_path, hub, monkeypatch):
    (tmp_path / "m.onnx").write_bytes(ONNX)
    model_file(PLAIN, tmp_path)
    monkeypatch.setattr(detect, "_sha256", lambda _path: pytest.fail("hashed twice"))
    model_file(PLAIN, tmp_path)


def test_a_fresh_download_is_not_hashed_again(tmp_path, hub, monkeypatch):
    model_file(ZIPPED, tmp_path)
    monkeypatch.setattr(detect, "_sha256", lambda _path: pytest.fail("hashed twice"))
    model_file(ZIPPED, tmp_path)


def test_the_pins_are_well_formed():
    commit, sha256 = re.compile(r"[0-9a-f]{40}"), re.compile(r"[0-9a-f]{64}")
    for spec in (DETECTOR_FILE, POSE_2D_FILE, POSE_3D_FILE):
        assert commit.fullmatch(spec.revision)
        assert sha256.fullmatch(spec.sha256) and sha256.fullmatch(spec.onnx_sha256)
        assert spec.name.endswith(".onnx")
        if not spec.filename.endswith(".zip"):
            assert spec.sha256 == spec.onnx_sha256
