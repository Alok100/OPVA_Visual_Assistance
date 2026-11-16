import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config
from app.storage import UploadValidationError, load_manifest, save_image


@pytest.fixture(autouse=True)
def isolated_experiments_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXPERIMENTS_ROOT", tmp_path)
    import app.storage as storage_module

    monkeypatch.setattr(storage_module, "EXPERIMENTS_ROOT", tmp_path)
    yield tmp_path


def _fake_jpeg_bytes(size=(20, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 200, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def test_save_image_rejects_bad_content_type():
    with pytest.raises(UploadValidationError):
        save_image("insp-1", "f.txt", "text/plain", b"not an image")


def test_save_image_rejects_oversized_file(monkeypatch):
    import app.config as cfg

    monkeypatch.setattr(cfg, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(UploadValidationError):
        save_image("insp-1", "f.jpg", "image/jpeg", _fake_jpeg_bytes())


def test_save_image_rejects_corrupt_image():
    with pytest.raises(UploadValidationError):
        save_image("insp-1", "f.jpg", "image/jpeg", b"\xff\xd8not really a jpeg")


def test_save_image_persists_and_appends_manifest():
    data = _fake_jpeg_bytes((30, 40))
    stored = save_image("insp-1", "bolt.jpg", "image/jpeg", data)
    assert stored.width == 30
    assert stored.height == 40
    manifest = load_manifest("insp-1")
    assert len(manifest) == 1
    assert manifest[0].image_id == stored.image_id


def test_save_image_rejects_unsafe_inspection_id():
    with pytest.raises(UploadValidationError):
        save_image("../../etc", "bolt.jpg", "image/jpeg", _fake_jpeg_bytes())
