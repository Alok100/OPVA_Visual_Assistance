"""Tests for POST /inspections/{id}/images/{image_id}/infer — the real
(non-demo) detect -> color-check -> verdict pipeline, wired to the API for
the first time in this test. Only ever called explicitly, never as a side
effect of upload or annotation import (see app/main.py's docstring there).
"""

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config


@pytest.fixture(autouse=True)
def isolated_experiments_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXPERIMENTS_ROOT", tmp_path)
    import app.storage as storage_module

    monkeypatch.setattr(storage_module, "EXPERIMENTS_ROOT", tmp_path)
    yield tmp_path


def _fake_jpeg_bytes(size=(300, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 200, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def test_infer_returns_404_for_unknown_image():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.post("/inspections/insp-1/images/does-not-exist/infer")
    assert res.status_code == 404


def test_infer_runs_real_pipeline_and_returns_image_result():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    upload = client.post(
        "/inspections/insp-1/images",
        files=[("files", ("test.jpg", io.BytesIO(_fake_jpeg_bytes()), "image/jpeg"))],
    )
    assert upload.status_code == 200
    image_id = upload.json()["stored"][0]["image_id"]

    res = client.post(f"/inspections/insp-1/images/{image_id}/infer")
    assert res.status_code == 200
    body = res.json()
    assert body["image_id"] == image_id
    assert body["filename"] == "test.jpg"
    assert body["status"] == "processed"
    # A solid-color synthetic image has no real bolts — asserting the real
    # pipeline ran and returned a well-formed result, not asserting a
    # specific detection count (that depends on the actual model weights).
    assert isinstance(body["bolts"], list)
    assert body["detection_quality"] in ("ok", "review", "not_processed")
