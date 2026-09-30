def test_recommend_returns_relevant_standard(client, register_and_login, auth_header, seeded_standard):
    _, standard_payload = seeded_standard
    officer_token = register_and_login(client, "recommend_officer1@example.gov.in", "OfficerPass1", "OFFICER")

    resp = client.post("/api/recommend", json={
        "query": "PVC pipes for potable water supply in a housing scheme", "top_k": 5,
    }, headers=auth_header(officer_token))
    assert resp.status_code == 200
    body = resp.json()
    is_numbers = [r["is_number"] for r in body["results"]]
    assert "IS 0001:2024" in is_numbers
    assert body["results"][0]["relevance_score"] > 0
    assert isinstance(body["results"][0]["matched_terms"], list)


def test_recommend_rejects_empty_query(client, register_and_login, auth_header):
    token = register_and_login(client, "empty_query@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post("/api/recommend", json={"query": "   "}, headers=auth_header(token))
    assert resp.status_code == 400


def test_recommend_expands_normative_references(client, register_and_login, auth_header, seeded_standard):
    """Verifies the graph traversal fix: normative_references are now walked,
    not just allied_standards. top_k=1 forces only the primary match into
    `results`, so the normatively-referenced standard can only appear via
    expansion — proving the traversal actually runs, not just co-incidentally
    ranking high enough to appear as a second primary match."""
    officer_token = register_and_login(client, "normative_officer@example.gov.in", "OfficerPass1", "OFFICER")

    admin_token, _ = seeded_standard
    create_resp = client.post("/api/standards", json={
        "is_number": "IS 0002:2024",
        "title": "Methods of Test for uPVC Pipes",
        "category": "Testing & Methods",
        "scope": "Specifies test methods referenced by IS 0001:2024.",
        "keywords": ["test method", "pvc pipe testing"],
    }, headers=auth_header(admin_token))
    assert create_resp.status_code in (200, 400)  # 400 = already created by a prior test run

    resp = client.post("/api/recommend", json={"query": "PVC pipes for potable water supply", "top_k": 1},
                        headers=auth_header(officer_token))
    body = resp.json()
    assert body["results"][0]["is_number"] == "IS 0001:2024"
    allied_numbers = [r["is_number"] for r in body["allied_expansion"]]
    assert "IS 0002:2024" in allied_numbers
    matched_entry = next(r for r in body["allied_expansion"] if r["is_number"] == "IS 0002:2024")
    assert "normative" in matched_entry["relations"]


def test_new_standard_is_immediately_searchable(client, register_and_login, auth_header):
    """Proves the index is dynamic, not static: a standard created via the API
    is findable by search in the same test/session, with no restart."""
    admin_token = register_and_login(client, "dynamic_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "dynamic_officer@example.gov.in", "OfficerPass1", "OFFICER")

    unique_title = "Zorbex Smart Irrigation Controllers"
    client.post("/api/standards", json={
        "is_number": "IS 7777:2026",
        "title": unique_title,
        "category": "Agriculture Technology",
        "scope": "Specifies requirements for smart automated irrigation controllers.",
        "keywords": ["irrigation", "smart controller", "zorbex"],
    }, headers=auth_header(admin_token))

    resp = client.post("/api/recommend", json={"query": "zorbex smart irrigation controller", "top_k": 3},
                        headers=auth_header(officer_token))
    is_numbers = [r["is_number"] for r in resp.json()["results"]]
    assert "IS 7777:2026" in is_numbers


def test_deleted_standard_no_longer_searchable(client, register_and_login, auth_header):
    admin_token = register_and_login(client, "delete_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "delete_officer@example.gov.in", "OfficerPass1", "OFFICER")

    client.post("/api/standards", json={
        "is_number": "IS 8888:2026",
        "title": "Quibblesnort Widget Fasteners",
        "category": "Mechanical & Fasteners",
        "scope": "A uniquely-named test standard for deletion verification.",
        "keywords": ["quibblesnort", "widget fastener"],
    }, headers=auth_header(admin_token))

    before = client.post("/api/recommend", json={"query": "quibblesnort widget fastener", "top_k": 3},
                          headers=auth_header(officer_token))
    assert "IS 8888:2026" in [r["is_number"] for r in before.json()["results"]]

    client.delete("/api/standards/IS 8888:2026", headers=auth_header(admin_token))

    after = client.post("/api/recommend", json={"query": "quibblesnort widget fastener", "top_k": 3},
                         headers=auth_header(officer_token))
    assert "IS 8888:2026" not in [r["is_number"] for r in after.json()["results"]]
