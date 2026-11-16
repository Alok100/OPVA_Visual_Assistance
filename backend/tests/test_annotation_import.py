import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.config as config
from app.annotation_import import (
    AnnotationImportError,
    detect_format,
    import_annotations_batch,
    parse_coco,
    parse_custom,
    parse_labelme,
    parse_supervisely,
    validate_box,
    RawBox,
)
from app.models import AnnotationFormat
from app.storage import save_image


@pytest.fixture(autouse=True)
def isolated_experiments_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EXPERIMENTS_ROOT", tmp_path)
    import app.storage as storage_module

    monkeypatch.setattr(storage_module, "EXPERIMENTS_ROOT", tmp_path)
    import app.annotation_import as ai_module

    monkeypatch.setattr(ai_module, "load_manifest", storage_module.load_manifest)
    yield tmp_path


def _fake_jpeg_bytes(size=(200, 100)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(255, 200, 0)).save(buf, format="JPEG")
    return buf.getvalue()


# --- format detection ---------------------------------------------------


def test_detect_format_coco():
    assert detect_format({"images": [], "annotations": []}) == AnnotationFormat.COCO


def test_detect_format_labelme():
    assert detect_format({"shapes": [], "imagePath": "a.jpg"}) == AnnotationFormat.LABELME


def test_detect_format_supervisely():
    assert detect_format({"size": {"width": 10, "height": 10}, "objects": []}) == AnnotationFormat.SUPERVISELY


def test_detect_format_supervisely_not_misread_as_custom():
    # Regression: a real Supervisely/DatasetNinja file's top-level keys
    # (description/tags/size/objects) were previously misread as
    # "filename: [box,...]" entries by the custom-format fallback.
    data = {
        "description": "",
        "tags": [{"name": "captured by authors"}],
        "size": {"height": 2736, "width": 3648},
        "objects": [],
    }
    assert detect_format(data) == AnnotationFormat.SUPERVISELY


def test_detect_format_custom_dict():
    assert detect_format({"a.jpg": []}) == AnnotationFormat.CUSTOM


def test_detect_format_custom_list():
    assert detect_format([{"filename": "a.jpg", "boxes": []}]) == AnnotationFormat.CUSTOM


def test_detect_format_rejects_unrecognized():
    with pytest.raises(AnnotationImportError):
        detect_format("not an object or array")


# --- parsers --------------------------------------------------------------


def test_parse_coco_links_annotations_to_filenames():
    data = {
        "images": [{"id": 1, "file_name": "bolt1.jpg"}, {"id": 2, "file_name": "bolt2.jpg"}],
        "annotations": [
            {"image_id": 1, "bbox": [10, 20, 30, 40], "category_id": 5},
            {"image_id": 2, "bbox": [1, 2, 3, 4], "category_id": 5},
        ],
        "categories": [{"id": 5, "name": "bolt"}],
    }
    result = parse_coco(data)
    assert set(result.keys()) == {"bolt1.jpg", "bolt2.jpg"}
    box = result["bolt1.jpg"][0]
    assert (box.x, box.y, box.width, box.height) == (10, 20, 30, 40)
    assert box.label == "bolt"


def test_parse_coco_rejects_dangling_image_id():
    data = {"images": [{"id": 1, "file_name": "a.jpg"}], "annotations": [{"image_id": 99, "bbox": [0, 0, 1, 1]}]}
    with pytest.raises(AnnotationImportError):
        parse_coco(data)


def test_parse_labelme_rectangle():
    data = {
        "imagePath": "bolt1.jpg",
        "shapes": [{"label": "bolt", "shape_type": "rectangle", "points": [[10, 20], [40, 60]]}],
    }
    result = parse_labelme(data)
    box = result["bolt1.jpg"][0]
    assert (box.x, box.y, box.width, box.height) == (10, 20, 30, 40)
    assert box.label == "bolt"


def test_parse_labelme_polygon_uses_bounding_rect_and_flags_it():
    data = {
        "imagePath": "bolt1.jpg",
        "shapes": [
            {
                "label": "bolt",
                "shape_type": "polygon",
                "points": [[10, 10], [50, 10], [50, 50], [10, 50]],
            }
        ],
    }
    result = parse_labelme(data)
    box = result["bolt1.jpg"][0]
    assert (box.x, box.y, box.width, box.height) == (10, 10, 40, 40)
    assert "bounding rect" in box.label


def test_parse_supervisely_rectangle_derives_filename_from_json_name():
    data = {
        "description": "",
        "tags": [],
        "size": {"height": 2736, "width": 3648},
        "objects": [
            {
                "classTitle": "bolt nut",
                "geometryType": "rectangle",
                "points": {"exterior": [[1719, 1223], [1855, 1356]], "interior": []},
            }
        ],
    }
    result = parse_supervisely(data, "AUT-0001.jpg.json")
    assert set(result.keys()) == {"AUT-0001.jpg"}
    box = result["AUT-0001.jpg"][0]
    assert (box.x, box.y, box.width, box.height) == (1719, 1223, 136, 133)
    assert box.label == "bolt nut"


def test_parse_supervisely_non_rectangle_uses_bounding_rect_and_flags_it():
    data = {
        "objects": [
            {
                "classTitle": "bolt nut",
                "geometryType": "polygon",
                "points": {"exterior": [[10, 10], [50, 10], [50, 50], [10, 50]], "interior": []},
            }
        ]
    }
    result = parse_supervisely(data, "a.jpg.json")
    box = result["a.jpg"][0]
    assert (box.x, box.y, box.width, box.height) == (10, 10, 40, 40)
    assert "bounding rect" in box.label


def test_parse_custom_dict_form():
    data = {"bolt1.jpg": [{"x": 1, "y": 2, "width": 3, "height": 4, "label": "bolt"}]}
    result = parse_custom(data)
    assert result["bolt1.jpg"][0] == RawBox(x=1, y=2, width=3, height=4, label="bolt")


def test_parse_custom_list_form_with_bbox_array():
    data = [{"filename": "bolt1.jpg", "boxes": [{"bbox": [1, 2, 3, 4]}]}]
    result = parse_custom(data)
    assert result["bolt1.jpg"][0].width == 3


def test_parse_custom_missing_field_raises():
    with pytest.raises(AnnotationImportError):
        parse_custom({"bolt1.jpg": [{"x": 1, "y": 2}]})


# --- box validation ---------------------------------------------------


def test_validate_box_accepts_in_bounds():
    assert validate_box(RawBox(10, 10, 50, 50), 200, 200) is None


def test_validate_box_rejects_non_positive_size():
    assert validate_box(RawBox(0, 0, 0, 10), 200, 200) is not None


def test_validate_box_rejects_negative_coords():
    assert validate_box(RawBox(-5, 0, 10, 10), 200, 200) is not None


def test_validate_box_rejects_out_of_bounds():
    assert validate_box(RawBox(190, 190, 50, 50), 200, 200) is not None


# --- end-to-end import_annotations_batch ----------------------------------


def test_import_batch_single_custom_file_matches_and_validates():
    stored = save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))

    payload = {
        stored.filename: [
            {"x": 10, "y": 10, "width": 20, "height": 20, "label": "bolt"},
            {"x": -5, "y": 0, "width": 10, "height": 10},  # invalid: negative coord
        ],
        "nonexistent.jpg": [{"x": 0, "y": 0, "width": 5, "height": 5}],
    }
    result = import_annotations_batch("insp-1", [("anno.json", json.dumps(payload).encode())])

    assert result.detected_formats == [AnnotationFormat.CUSTOM]
    assert result.unmatched_filenames == ["nonexistent.jpg"]
    assert result.total_box_count == 2
    assert result.invalid_box_count == 1
    assert len(result.matched_images) == 1
    matched = result.matched_images[0]
    assert matched.image_id == stored.image_id
    valid_boxes = [b for b in matched.boxes if b.valid]
    invalid_boxes = [b for b in matched.boxes if not b.valid]
    assert len(valid_boxes) == 1
    assert len(invalid_boxes) == 1
    assert invalid_boxes[0].issue is not None
    assert valid_boxes[0].status.value == "imported_not_reviewed"
    assert result.file_errors == []


def test_import_batch_rejects_when_every_file_is_invalid_json():
    with pytest.raises(AnnotationImportError):
        import_annotations_batch("insp-1", [("bad.json", b"{not json")])


def test_import_batch_preserves_every_original_file():
    save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes())
    raw = json.dumps({"bolt1.jpg": [{"x": 1, "y": 1, "width": 2, "height": 2}]}).encode()
    result = import_annotations_batch("insp-1", [("my-annotations.json", raw)])

    from app.config import EXPERIMENTS_ROOT

    assert len(result.original_files_saved_as) == 1
    saved_path = EXPERIMENTS_ROOT / result.original_files_saved_as[0]
    assert saved_path.exists()
    assert saved_path.read_bytes() == raw


def test_import_batch_handles_one_labelme_file_per_image():
    img1 = save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    img2 = save_image("insp-1", "bolt2.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))

    file1 = json.dumps(
        {"imagePath": "bolt1.jpg", "shapes": [{"label": "bolt", "points": [[10, 10], [30, 30]]}]}
    ).encode()
    file2 = json.dumps(
        {"imagePath": "bolt2.jpg", "shapes": [{"label": "bolt", "points": [[5, 5], [25, 25]]}]}
    ).encode()

    result = import_annotations_batch("insp-1", [("bolt1.json", file1), ("bolt2.json", file2)])

    assert result.detected_formats == [AnnotationFormat.LABELME]
    assert len(result.original_files_saved_as) == 2
    matched_ids = {m.image_id for m in result.matched_images}
    assert matched_ids == {img1.image_id, img2.image_id}
    assert result.total_box_count == 2
    # Earlier files importing a batch must not be clobbered by later ones —
    # this is the bug multi-file LabelMe import would hit with a
    # single-file-overwrite implementation.
    for m in result.matched_images:
        assert len(m.boxes) == 1


def test_import_batch_one_bad_file_does_not_abort_the_rest():
    save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    good = json.dumps({"bolt1.jpg": [{"x": 1, "y": 1, "width": 2, "height": 2}]}).encode()

    result = import_annotations_batch("insp-1", [("good.json", good), ("bad.json", b"{not json")])

    assert len(result.matched_images) == 1
    assert len(result.file_errors) == 1
    assert result.file_errors[0].filename == "bad.json"


def test_import_batch_handles_supervisely_files_one_per_image():
    img1 = save_image("insp-1", "AUT-0001.jpg", "image/jpeg", _fake_jpeg_bytes((2000, 1500)))
    img2 = save_image("insp-1", "AUT-0002.jpg", "image/jpeg", _fake_jpeg_bytes((2000, 1500)))

    def supervisely_file(x, y, w, h):
        return json.dumps(
            {
                "description": "",
                "tags": [],
                "size": {"height": 1500, "width": 2000},
                "objects": [
                    {
                        "classTitle": "bolt nut",
                        "geometryType": "rectangle",
                        "points": {"exterior": [[x, y], [x + w, y + h]], "interior": []},
                    }
                ],
            }
        ).encode()

    result = import_annotations_batch(
        "insp-1",
        [
            ("AUT-0001.jpg.json", supervisely_file(100, 100, 50, 50)),
            ("AUT-0002.jpg.json", supervisely_file(200, 200, 60, 60)),
        ],
    )

    assert result.detected_formats == [AnnotationFormat.SUPERVISELY]
    assert result.file_errors == []
    assert result.unmatched_filenames == []
    matched_ids = {m.image_id for m in result.matched_images}
    assert matched_ids == {img1.image_id, img2.image_id}
    assert result.total_box_count == 2


def test_import_batch_merges_boxes_for_same_image_across_files():
    stored = save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    file1 = json.dumps({stored.filename: [{"x": 1, "y": 1, "width": 2, "height": 2}]}).encode()
    file2 = json.dumps({stored.filename: [{"x": 5, "y": 5, "width": 2, "height": 2}]}).encode()

    result = import_annotations_batch("insp-1", [("a.json", file1), ("b.json", file2)])

    assert len(result.matched_images) == 1
    assert len(result.matched_images[0].boxes) == 2


def test_import_batch_assigns_unique_stable_box_ids():
    # Microtask 3.2: every ImportedBox needs an id so the manual editor can
    # persist edits against a specific box across reloads.
    stored = save_image("insp-1", "bolt1.jpg", "image/jpeg", _fake_jpeg_bytes((200, 100)))
    payload = {
        stored.filename: [
            {"x": 1, "y": 1, "width": 2, "height": 2},
            {"x": 5, "y": 5, "width": 2, "height": 2},
        ]
    }
    result = import_annotations_batch("insp-1", [("anno.json", json.dumps(payload).encode())])
    ids = [b.id for b in result.matched_images[0].boxes]
    assert all(ids)
    assert len(set(ids)) == len(ids)
