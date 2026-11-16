"""Tests for the manual annotation editing / review / approve persistence
layer (Microtask 3.2) — app/annotation_review.py plus the new
.../annotations/current endpoints in app/main.py."""

import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config
from app.annotation_import import import_annotations_batch
from app.annotation_review import (
    AnnotationTransitionError,
    get_approved_boxes_for_training,
    get_current_annotations,
    replace_current_boxes_for_image,
    seed_current_from_import,
    update_box_status,
)
from app.models import AnnotationStatus, BoundingBox, CurrentBoxInput
from app.storage import load_parsed_annotations, save_image


@pytest.fixture(autouse=True)
def isolated_experiments_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXPERIMENTS_ROOT", tmp_path)
    import app.storage as storage_module

    monkeypatch.setattr(storage_module, "EXPERIMENTS_ROOT", tmp_path)
    yield tmp_path


def _fake_jpeg_bytes(size=(200, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 200, 0)).save(buf, format="JPEG")
    return buf.getvalue()


def _box_input(box_id, x, y, w, h, label=None):
    return CurrentBoxInput(id=box_id, bbox=BoundingBox(x=x, y=y, width=w, height=h), label=label)


# --- GET .../annotations/current via TestClient (exercises the real route,
# including seed_current_from_import being wired into the import endpoint) --


def test_import_endpoint_seeds_current_annotations():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    upload = client.post(
        "/inspections/insp-1/images",
        files=[("files", ("bolt1.jpg", io.BytesIO(_fake_jpeg_bytes()), "image/jpeg"))],
    )
    image_id = upload.json()["stored"][0]["image_id"]

    payload = {"bolt1.jpg": [{"x": 10, "y": 10, "width": 20, "height": 20, "label": "bolt"}]}
    files = {"files": ("anno.json", json.dumps(payload).encode(), "application/json")}
    imp = client.post("/inspections/insp-1/annotations/import", files=files)
    assert imp.status_code == 200

    current = client.get("/inspections/insp-1/annotations/current")
    assert current.status_code == 200
    body = current.json()
    assert len(body) == 1
    assert body[0]["image_id"] == image_id
    assert len(body[0]["boxes"]) == 1
    box = body[0]["boxes"][0]
    assert box["origin"] == "imported"
    assert box["status"] == "imported_not_reviewed"
    assert box["edited"] is False
    assert box["original_bbox"] is None


def test_get_current_annotations_includes_images_with_no_boxes():
    stored = save_image("insp-1", "lonely.jpg", "image/jpeg", _fake_jpeg_bytes())
    views = get_current_annotations("insp-1")
    assert len(views) == 1
    assert views[0].image_id == stored.image_id
    assert views[0].boxes == []


# --- PUT (replace_current_boxes_for_image) ---------------------------------


def test_put_marks_brand_new_box_human_added_and_verified():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    result = replace_current_boxes_for_image(
        "insp-1", stored, [_box_input("new-1", 10, 10, 20, 20, "bolt")]
    )
    assert len(result.boxes) == 1
    box = result.boxes[0]
    assert box.origin == "human_added"
    assert box.status == "human_verified"
    assert box.edited is False  # no import record to diff against


def test_put_absent_box_id_deletes_it():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image(
        "insp-1", stored, [_box_input("b1", 10, 10, 20, 20), _box_input("b2", 30, 30, 20, 20)]
    )
    result = replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20)])
    assert [b.id for b in result.boxes] == ["b1"]


def test_put_preserves_status_on_noop_resave():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20, "bolt")])
    update_box_status("insp-1", stored.image_id, "b1", AnnotationStatus.APPROVED_FOR_TRAINING)

    result = replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20, "bolt")])
    assert result.boxes[0].status == "approved_for_training"


def test_put_demotes_approved_box_when_geometry_changes():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20, "bolt")])
    update_box_status("insp-1", stored.image_id, "b1", AnnotationStatus.APPROVED_FOR_TRAINING)

    result = replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 15, 15, 20, 20, "bolt")])
    assert result.boxes[0].status == "human_verified"


def test_put_demotes_approved_box_when_label_changes():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20, "bolt")])
    update_box_status("insp-1", stored.image_id, "b1", AnnotationStatus.APPROVED_FOR_TRAINING)

    result = replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20, "nut")])
    assert result.boxes[0].status == "human_verified"


def test_put_revalidates_geometry_against_real_image_dimensions():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    result = replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 5000, 5000, 20, 20)])
    assert result.boxes[0].valid is False
    assert result.boxes[0].issue is not None
    # Invalid + brand-new -> not auto-verified (see annotation_review.py).
    assert result.boxes[0].status == "imported_not_reviewed"


def test_put_never_mutates_annotations_imported_json():
    stored = save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    raw = json.dumps({"bolt1.jpg": [{"x": 10, "y": 10, "width": 20, "height": 20}]}).encode()
    import_result = import_annotations_batch("insp-1", [("anno.json", raw)])
    seed_current_from_import("insp-1", import_result)

    before = load_parsed_annotations("insp-1")
    box_id = import_result.matched_images[0].boxes[0].id
    replace_current_boxes_for_image("insp-1", stored, [_box_input(box_id, 12, 12, 20, 20)])
    after = load_parsed_annotations("insp-1")

    assert before == after


def test_put_ignores_client_supplied_status_field_in_payload():
    # CurrentBoxInput has no `status` field — constructing one from a dict
    # that includes an extra "status" key must simply drop it (pydantic's
    # default extra="ignore"), so a client can't smuggle an approval
    # through the edit endpoint.
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    sneaky = CurrentBoxInput.model_validate(
        {"id": "b1", "bbox": {"x": 1, "y": 1, "width": 2, "height": 2}, "status": "approved_for_training"}
    )
    assert not hasattr(sneaky, "status")
    result = replace_current_boxes_for_image("insp-1", stored, [sneaky])
    assert result.boxes[0].status == "human_verified"  # the new-box default, not approved


# --- PATCH status (update_box_status) ---------------------------------------


def test_patch_status_allows_legal_forward_chain():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    raw = json.dumps({"a.jpg": [{"x": 10, "y": 10, "width": 20, "height": 20}]}).encode()
    import_result = import_annotations_batch("insp-1", [("anno.json", raw)])
    seed_current_from_import("insp-1", import_result)
    box_id = import_result.matched_images[0].boxes[0].id

    step1 = update_box_status("insp-1", stored.image_id, box_id, AnnotationStatus.HUMAN_VERIFIED)
    assert step1.status == "human_verified"
    step2 = update_box_status("insp-1", stored.image_id, box_id, AnnotationStatus.APPROVED_FOR_TRAINING)
    assert step2.status == "approved_for_training"


def test_patch_status_rejects_skip_to_approved():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    raw = json.dumps({"a.jpg": [{"x": 10, "y": 10, "width": 20, "height": 20}]}).encode()
    import_result = import_annotations_batch("insp-1", [("anno.json", raw)])
    seed_current_from_import("insp-1", import_result)
    box_id = import_result.matched_images[0].boxes[0].id

    with pytest.raises(AnnotationTransitionError):
        update_box_status("insp-1", stored.image_id, box_id, AnnotationStatus.APPROVED_FOR_TRAINING)


def test_patch_status_rejects_downgrade():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 10, 10, 20, 20)])
    update_box_status("insp-1", stored.image_id, "b1", AnnotationStatus.APPROVED_FOR_TRAINING)

    with pytest.raises(AnnotationTransitionError):
        update_box_status("insp-1", stored.image_id, "b1", AnnotationStatus.HUMAN_VERIFIED)


def test_patch_status_rejects_unknown_box():
    save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    with pytest.raises(KeyError):
        update_box_status("insp-1", "insp-1", "no-such-box", AnnotationStatus.HUMAN_VERIFIED)


def test_patch_status_rejects_unknown_image():
    with pytest.raises(KeyError):
        update_box_status("insp-1", "no-such-image", "b1", AnnotationStatus.HUMAN_VERIFIED)


def test_patch_status_rejects_invalid_box():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image("insp-1", stored, [_box_input("b1", 5000, 5000, 20, 20)])
    with pytest.raises(AnnotationTransitionError):
        update_box_status("insp-1", stored.image_id, "b1", AnnotationStatus.HUMAN_VERIFIED)


def test_patch_status_endpoint_returns_422_not_500_on_illegal_transition():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    upload = client.post(
        "/inspections/insp-1/images",
        files=[("files", ("a.jpg", io.BytesIO(_fake_jpeg_bytes()), "image/jpeg"))],
    )
    image_id = upload.json()["stored"][0]["image_id"]
    client.put(
        f"/inspections/insp-1/annotations/current/{image_id}",
        json=[{"id": "b1", "bbox": {"x": 10, "y": 10, "width": 20, "height": 20}}],
    )
    # b1 is human_added -> already human_verified; skip straight further is fine,
    # but re-requesting the same human_verified status is not a legal transition.
    res = client.patch(
        f"/inspections/insp-1/annotations/current/{image_id}/boxes/b1/status",
        json={"status": "human_verified"},
    )
    assert res.status_code == 422

    res_404 = client.patch(
        f"/inspections/insp-1/annotations/current/{image_id}/boxes/does-not-exist/status",
        json={"status": "human_verified"},
    )
    assert res_404.status_code == 404


# --- get_approved_boxes_for_training -----------------------------------------


def test_get_approved_boxes_for_training_excludes_everything_else():
    stored = save_image("insp-1", "a.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    replace_current_boxes_for_image(
        "insp-1",
        stored,
        [_box_input("human-added-1", 10, 10, 20, 20), _box_input("human-added-2", 40, 40, 20, 20)],
    )
    update_box_status("insp-1", stored.image_id, "human-added-1", AnnotationStatus.APPROVED_FOR_TRAINING)
    # human-added-2 stays at human_verified — must NOT show up below.

    approved = get_approved_boxes_for_training("insp-1")
    assert len(approved) == 1
    image_id, box = approved[0]
    assert image_id == stored.image_id
    assert box.id == "human-added-1"
    assert box.status == "approved_for_training"
