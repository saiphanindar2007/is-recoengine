"""Tests for document-processing reliability: extension/content validation
and clause-level (not blind-truncation) tender document processing."""
import io


def test_upload_rejects_unsupported_extension(client, register_and_login, auth_header):
    token = register_and_login(client, "upload_ext@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post(
        "/api/recommend/upload",
        files={"file": ("tender.exe", io.BytesIO(b"not a real tender"), "application/octet-stream")},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


def test_upload_rejects_content_mismatched_with_extension(client, register_and_login, auth_header):
    """A file named .pdf that isn't actually a PDF (wrong magic bytes) must be
    rejected — extension alone is not trusted."""
    token = register_and_login(client, "upload_magic@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post(
        "/api/recommend/upload",
        files={"file": ("fake.pdf", io.BytesIO(b"this is just plain text, not a pdf"), "application/pdf")},
        headers=auth_header(token),
    )
    assert resp.status_code == 422
    assert "not a valid PDF" in resp.json()["detail"]


def test_upload_rejects_empty_file(client, register_and_login, auth_header):
    token = register_and_login(client, "upload_empty@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post(
        "/api/recommend/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers=auth_header(token),
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_upload_txt_processes_clauses_and_recommends(client, register_and_login, auth_header, seeded_standard):
    """A multi-clause tender document should be split into clauses (not one
    blind truncated excerpt) and produce a per-clause match breakdown."""
    token = register_and_login(client, "upload_clauses@example.gov.in", "OfficerPass1", "OFFICER")

    tender_text = (
        "1. Scope of Work\n"
        "This tender covers the supply and installation of water distribution infrastructure "
        "for a new housing scheme in the district, including all associated civil works.\n\n"
        "2. Pipe Material Requirements\n"
        "Supply of PVC pipes for potable water supply is required, rated for underground laying "
        "and cold water distribution across the scheme, DN 110mm nominal diameter throughout.\n\n"
        "3. Testing and Quality\n"
        "All materials supplied under this tender must comply with applicable Indian Standards "
        "and carry valid certification marks prior to installation and commissioning.\n"
    )
    resp = client.post(
        "/api/recommend/upload",
        files={"file": ("tender.txt", io.BytesIO(tender_text.encode("utf-8")), "text/plain")},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["clauses_processed"] >= 2
    assert len(body["clause_matches"]) == body["clauses_processed"]
    assert body["source_filename"] == "tender.txt"
    # the PVC-pipe clause should have surfaced the seeded PVC standard somewhere
    all_matched_numbers = {m["is_number"] for cm in body["clause_matches"] for m in cm["matches"]}
    assert "IS 0001:2024" in all_matched_numbers


def test_upload_oversized_file_rejected(client, register_and_login, auth_header):
    token = register_and_login(client, "upload_oversized@example.gov.in", "OfficerPass1", "OFFICER")
    big_content = b"a" * (5 * 1024 * 1024 + 1)  # 1 byte over the 5MB limit
    resp = client.post(
        "/api/recommend/upload",
        files={"file": ("big.txt", io.BytesIO(big_content), "text/plain")},
        headers=auth_header(token),
    )
    assert resp.status_code == 413
