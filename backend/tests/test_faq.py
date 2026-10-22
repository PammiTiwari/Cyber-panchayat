from conftest import auth_header


def test_faq_list_is_public(client):
    resp = client.get("/api/faqs")
    assert resp.status_code == 200


def test_only_admin_can_add_faq(client, citizen_token):
    resp = client.post("/api/faqs", headers=auth_header(citizen_token),
                        json={"question": "How?", "answer": "Like this."})
    assert resp.status_code == 403


def test_admin_adds_faq_then_it_appears_in_list(client, admin_token, app):
    add = client.post("/api/faqs", headers=auth_header(admin_token),
                       json={"question": "How do I pay?", "answer": "Use UPI."})
    assert add.status_code == 201
    listing = client.get("/api/faqs").get_json()
    assert any(f["question"] == "How do I pay?" for f in listing)
    from apps.models import FaqEntry
    with app.app_context():
        entry = FaqEntry.query.filter_by(question="How do I pay?").first()
        assert entry is not None
        assert entry.answer == "Use UPI."


def test_faq_feedback_requires_login(client):
    resp = client.post("/api/faqs/feedback", json={"article_id": "cit-file", "helpful": True})
    assert resp.status_code == 403


def test_faq_feedback_tally_visible_to_admin_only(client, admin_token, citizen_token, app):
    client.post("/api/faqs/feedback", headers=auth_header(citizen_token),
                json={"article_id": "cit-file", "helpful": True})
    forbidden = client.get("/api/faqs/feedback", headers=auth_header(citizen_token))
    assert forbidden.status_code == 403
    tally = client.get("/api/faqs/feedback", headers=auth_header(admin_token)).get_json()
    assert tally["cit-file"] == {"yes": 1, "no": 0}
    from apps.models import FaqFeedback
    with app.app_context():
        vote = FaqFeedback.query.filter_by(article_id="cit-file").first()
        assert vote is not None
        assert vote.helpful is True


def test_only_admin_can_delete_an_faq(client, admin_token, citizen_token, app):
    faq = client.post("/api/faqs", headers=auth_header(admin_token),
                       json={"question": "Can this be removed?", "answer": "Yes, by an admin."}).get_json()

    refused = client.delete(f"/api/faqs/{faq['id']}", headers=auth_header(citizen_token))
    assert refused.status_code == 403
    assert any(f["id"] == faq["id"] for f in client.get("/api/faqs").get_json())

    removed = client.delete(f"/api/faqs/{faq['id']}", headers=auth_header(admin_token))
    assert removed.status_code == 200
    assert removed.get_json()["success"] is True
    assert all(f["id"] != faq["id"] for f in client.get("/api/faqs").get_json())

    from apps.models import FaqEntry
    from apps import db
    with app.app_context():
        assert db.session.get(FaqEntry, faq["id"]) is None


def test_only_admin_can_edit_an_faq(client, admin_token, citizen_token):
    faq = client.post("/api/faqs", headers=auth_header(admin_token),
                       json={"question": "Is this clear?", "answer": "Not very."}).get_json()

    refused = client.put(f"/api/faqs/{faq['id']}", headers=auth_header(citizen_token),
                          json={"answer": "Rewritten by a citizen."})
    assert refused.status_code == 403
    unchanged = next(f for f in client.get("/api/faqs").get_json() if f["id"] == faq["id"])
    assert unchanged["answer"] == "Not very."

    edited = client.put(f"/api/faqs/{faq['id']}", headers=auth_header(admin_token),
                         json={"answer": "Much clearer now."})
    assert edited.status_code == 200
    assert edited.get_json()["answer"] == "Much clearer now."


def test_editing_an_faq_keeps_its_helpful_votes(client, admin_token, citizen_token):
    """The point of the endpoint: a rewrite must not orphan the tally.

    Votes are keyed on "custom-<id>", so delete-and-re-add used to reset the
    count to zero. Editing keeps the id, so the count survives the rewrite.
    """
    faq = client.post("/api/faqs", headers=auth_header(admin_token),
                       json={"question": "Does the count survive?", "answer": "Find out."}).get_json()
    article = f"custom-{faq['id']}"
    client.post("/api/faqs/feedback", headers=auth_header(citizen_token),
                json={"article_id": article, "helpful": True})

    client.put(f"/api/faqs/{faq['id']}", headers=auth_header(admin_token),
                json={"question": "Does the count survive an edit?",
                      "answer": "It does, the id does not change."})

    tally = client.get("/api/faqs/feedback", headers=auth_header(admin_token)).get_json()
    assert tally[article] == {"yes": 1, "no": 0}


def test_editing_an_faq_rejects_blank_and_unknown(client, admin_token):
    faq = client.post("/api/faqs", headers=auth_header(admin_token),
                       json={"question": "Keep me.", "answer": "Original answer."}).get_json()

    blank = client.put(f"/api/faqs/{faq['id']}", headers=auth_header(admin_token),
                        json={"answer": "   "})
    assert blank.status_code == 400
    kept = next(f for f in client.get("/api/faqs").get_json() if f["id"] == faq["id"])
    assert kept["answer"] == "Original answer."

    missing = client.put("/api/faqs/999999", headers=auth_header(admin_token),
                          json={"answer": "Nobody home."})
    assert missing.status_code == 404


def test_editing_only_the_category_leaves_the_text_alone(client, admin_token):
    faq = client.post("/api/faqs", headers=auth_header(admin_token),
                       json={"question": "Where does this live?", "answer": "Wrong section.",
                             "category": "complaints"}).get_json()

    moved = client.put(f"/api/faqs/{faq['id']}", headers=auth_header(admin_token),
                        json={"category": "premium"}).get_json()
    assert moved["category"] == "premium"
    assert moved["question"] == "Where does this live?"
    assert moved["answer"] == "Wrong section."
