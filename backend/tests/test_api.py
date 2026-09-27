from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _make_png_bytes(mode="RGB", size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color=(10, 20, 30) if mode == "RGB" else 100).save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_upload_single_valid_png():
    png = _make_png_bytes()
    r = client.post("/api/upload", files={"files": ("test.png", png, "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert len(body["files"]) == 1
    assert body["files"][0]["format"] == "PNG"
    assert body["files"][0]["width"] == 64
    assert body["input_configuration"] == "single_image"


def test_upload_rejects_bad_bytes():
    r = client.post("/api/upload", files={"files": ("bad.png", b"not an image", "image/png")})
    assert r.status_code == 422


def test_upload_rejects_empty_file():
    r = client.post("/api/upload", files={"files": ("empty.png", b"", "image/png")})
    assert r.status_code == 400


def test_upload_rejects_more_than_two_files():
    png = _make_png_bytes()
    files = [("files", (f"t{i}.png", png, "image/png")) for i in range(3)]
    r = client.post("/api/upload", files=files)
    assert r.status_code == 400


def test_query_single_image_vqa_default():
    png = _make_png_bytes()
    up = client.post("/api/upload", files={"files": ("test.png", png, "image/png")})
    file_id = up.json()["files"][0]["file_id"]

    # Deliberately avoids caption/grounding keywords so it falls through to
    # the default vqa branch (see app/services/router.py classify_task()).
    r = client.post("/api/query", json={"file_ids": [file_id], "query": "Is there a river in this scene?"})
    assert r.status_code == 200
    body = r.json()
    assert body["task"] == "vqa"
    # No real model wired up in this environment -> must be honestly "blocked", never fabricated.
    assert body["status"] == "blocked"
    assert body["answer"] is None
    assert any(step["status"] == "not_implemented" for step in body["execution_trace"])


def test_query_unknown_file_id_errors():
    r = client.post("/api/query", json={"file_ids": ["does-not-exist"], "query": "test"})
    assert r.status_code == 400


def test_query_bitemporal_change_keyword_routes_to_change_vqa():
    png = _make_png_bytes()
    ids = []
    for name in ("before.png", "after.png"):
        up = client.post("/api/upload", files={"files": (name, png, "image/png")})
        ids.append(up.json()["files"][0]["file_id"])

    r = client.post("/api/query", json={"file_ids": ids, "query": "What changed between these before and after images?"})
    assert r.status_code == 200
    assert r.json()["task"] == "change_vqa"


def test_query_two_images_no_modality_hint_is_blocked_not_guessed():
    png = _make_png_bytes()
    ids = []
    for name in ("a.png", "b.png"):
        up = client.post("/api/upload", files={"files": (name, png, "image/png")})
        ids.append(up.json()["files"][0]["file_id"])

    r = client.post("/api/query", json={"file_ids": ids, "query": "analyze these"})
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
