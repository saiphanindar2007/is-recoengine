"""Cross-role integration test: officer flags a standard, admin resolves it,
and both actions land in the immutable audit log — exercising the full
governance loop end-to-end in one test, not isolated unit calls."""

def test_full_officer_admin_workflow(client, register_and_login, auth_header, seeded_standard):
    admin_token, standard_payload = seeded_standard
    officer_token = register_and_login(client, "workflow_officer@example.gov.in", "OfficerPass1", "OFFICER")

    # 1. Officer searches and finds the standard
    search = client.post("/api/recommend", json={"query": "PVC pipes potable water", "top_k": 3},
                          headers=auth_header(officer_token))
    assert search.status_code == 200
    assert any(r["is_number"] == "IS 0001:2024" for r in search.json()["results"])

    # 2. Officer saves a specification built from the result
    spec = client.post("/api/specifications", json={
        "title": "Test Housing Scheme Plumbing Spec",
        "source_query": "PVC pipes potable water",
        "standard_numbers": ["IS 0001:2024"],
        "status": "DRAFT",
    }, headers=auth_header(officer_token))
    assert spec.status_code == 200
    spec_id = spec.json()["id"]

    # 3. Officer finalizes it
    finalize = client.put(f"/api/specifications/{spec_id}", json={"status": "FINALIZED"},
                           headers=auth_header(officer_token))
    assert finalize.status_code == 200
    assert finalize.json()["status"] == "FINALIZED"

    # 4. Officer flags the standard as needing review
    flag = client.post("/api/change-requests", json={
        "standard_is_number": "IS 0001:2024", "reason": "Please confirm this is the latest revision.",
    }, headers=auth_header(officer_token))
    assert flag.status_code == 200
    cr_id = flag.json()["id"]
    assert flag.json()["status"] == "OPEN"

    # 5. Admin resolves it
    resolve = client.put(f"/api/change-requests/{cr_id}/resolve", json={
        "status": "RESOLVED", "resolution_note": "Confirmed current.",
    }, headers=auth_header(admin_token))
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "RESOLVED"

    # 6. Both actions are captured in the immutable audit log
    audit = client.get("/api/audit-logs", headers=auth_header(admin_token))
    assert audit.status_code == 200
    actions = [a["action"] for a in audit.json()]
    assert "CHANGE_REQUEST_RAISED" in actions
    assert "CHANGE_REQUEST_RESOLVED" in actions
    assert "STANDARD_CREATE" in actions


def test_officer_cannot_edit_another_officers_specification(client, register_and_login, auth_header, seeded_standard):
    officer_a = register_and_login(client, "spec_owner_a@example.gov.in", "OfficerPass1", "OFFICER")
    officer_b = register_and_login(client, "spec_owner_b@example.gov.in", "OfficerPass1", "OFFICER")

    spec = client.post("/api/specifications", json={
        "title": "Owner A's Spec", "standard_numbers": ["IS 0001:2024"], "status": "DRAFT",
    }, headers=auth_header(officer_a))
    spec_id = spec.json()["id"]

    resp = client.put(f"/api/specifications/{spec_id}", json={"title": "Hijacked"},
                       headers=auth_header(officer_b))
    assert resp.status_code == 403


def test_currency_flag_filters_outdated_standards(client, register_and_login, auth_header):
    admin_token = register_and_login(client, "currency_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "currency_officer@example.gov.in", "OfficerPass1", "OFFICER")

    client.post("/api/standards", json={
        "is_number": "IS 5555:2010", "title": "Legacy Widget Standard Xylophone",
        "category": "Mechanical & Fasteners", "scope": "An outdated legacy standard for testing.",
        "keywords": ["xylophone widget legacy"], "is_current": False, "superseded_by": "IS 5556:2024",
    }, headers=auth_header(admin_token))
    client.post("/api/standards", json={
        "is_number": "IS 5556:2024", "title": "Current Widget Standard Xylophone",
        "category": "Mechanical & Fasteners", "scope": "The current replacement standard for testing.",
        "keywords": ["xylophone widget current"],
    }, headers=auth_header(admin_token))

    all_results = client.post("/api/recommend", json={"query": "xylophone widget standard", "top_k": 5},
                               headers=auth_header(officer_token)).json()
    all_numbers = [r["is_number"] for r in all_results["results"]]
    assert "IS 5555:2010" in all_numbers  # visible by default

    current_only = client.post("/api/recommend", json={
        "query": "xylophone widget standard", "top_k": 5, "only_current": True,
    }, headers=auth_header(officer_token)).json()
    current_numbers = [r["is_number"] for r in current_only["results"]]
    assert "IS 5555:2010" not in current_numbers
    assert "IS 5556:2024" in current_numbers
