import io
import os

from conftest import auth_header
from helpers import subscribe

UPLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


def _upload(client, token, name="probe.png"):
    data = {"file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 400), name)}
    resp = client.post("/api/upload", headers=auth_header(token), data=data,
                       content_type="multipart/form-data")
    assert resp.status_code == 201, resp.get_json()
    url = resp.get_json()["url"]
    return url, os.path.join(UPLOADS, os.path.basename(url))


def test_deleting_a_complaint_removes_its_photos(client, citizen_token):
    subscribe(client, citizen_token)
    url, path = _upload(client, citizen_token)
    assert os.path.exists(path)

    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Marg",
        "image_urls": [url],
    }).get_json()

    assert client.delete(f"/api/requests/{sr['id']}", headers=auth_header(citizen_token)).status_code == 200
    assert not os.path.exists(path), "complaint photo should not outlive the complaint"


def test_deleting_a_complaint_removes_its_evidence_photo(client, admin_token, staff_token, citizen_token):
    subscribe(client, citizen_token)
    url, path = _upload(client, citizen_token, "evidence.png")

    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "road", "description": "Pothole", "address": "MG Marg",
    }).get_json()
    staff_id = client.get("/api/auth/me", headers=auth_header(staff_token)).get_json()["id"]
    client.post("/api/assignments", headers=auth_header(admin_token),
                json={"request_id": sr["id"], "staff_id": staff_id})
    client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(staff_token),
               json={"status": "resolved", "evidence_urls": [url]})
    assert os.path.exists(path)

    # An admin cannot delete a resolved complaint (it is part of the public
    # record), so move it back into the work queue first — the admin is the
    # only role allowed to do that.
    client.put(f"/api/requests/{sr['id']}/status", headers=auth_header(admin_token),
               json={"status": "in_progress"})
    assert client.delete(f"/api/requests/{sr['id']}", headers=auth_header(admin_token)).status_code == 200
    assert not os.path.exists(path), "evidence photo should not outlive the complaint"


def test_deleting_a_post_removes_its_photo(client, citizen_token):
    url, path = _upload(client, citizen_token, "post.png")
    post = client.post("/api/posts", headers=auth_header(citizen_token), json={
        "content": "Something worth showing", "image_urls": [url],
    }).get_json()
    assert os.path.exists(path)

    assert client.delete(f"/api/posts/{post['id']}", headers=auth_header(citizen_token)).status_code == 200
    assert not os.path.exists(path), "post photo should not outlive the post"


def test_a_photo_shared_with_another_record_is_kept(client, citizen_token):
    subscribe(client, citizen_token)
    url, path = _upload(client, citizen_token, "shared.png")

    sr = client.post("/api/requests", headers=auth_header(citizen_token), json={
        "category": "waste", "description": "Overflowing bin", "address": "Kareli",
        "image_urls": [url],
    }).get_json()
    post = client.post("/api/posts", headers=auth_header(citizen_token), json={
        "content": "Same bin, still not collected", "image_urls": [url],
    }).get_json()

    assert client.delete(f"/api/requests/{sr['id']}", headers=auth_header(citizen_token)).status_code == 200
    assert os.path.exists(path), "file still referenced by the post was deleted"
    assert client.get(f"/api/uploads/{os.path.basename(url)}").status_code == 200

    assert client.delete(f"/api/posts/{post['id']}", headers=auth_header(citizen_token)).status_code == 200
    assert not os.path.exists(path)


def test_scanned_paper_is_not_written_to_uploads(client, citizen_token):
    before = set(os.listdir(UPLOADS)) if os.path.isdir(UPLOADS) else set()
    data = {"file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 400), "paper.png")}
    resp = client.post("/api/ai/extract-from-image", headers=auth_header(citizen_token),
                       data=data, content_type="multipart/form-data")
    assert resp.status_code in (200, 422, 502, 503)
    if resp.status_code == 200:
        assert "image_url" not in resp.get_json()
    after = set(os.listdir(UPLOADS)) if os.path.isdir(UPLOADS) else set()
    assert after == before, f"scan left files behind: {sorted(after - before)}"
