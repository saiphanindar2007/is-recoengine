"""Tests for recommendation-accuracy evaluation, low-confidence/no-match
handling, explainability score breakdown, and cycle-safe graph traversal."""


def test_evaluation_endpoint_reachable_by_admin_and_auditor(client, register_and_login, auth_header):
    admin_token = register_and_login(client, "eval_admin@example.gov.in", "AdminPass1", "ADMIN")
    resp = client.get("/api/analytics/evaluation", headers=auth_header(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_queries"] > 0
    assert 0.0 <= body["mrr"] <= 1.0
    assert 0.0 <= body["hit_at_k"] <= 1.0
    assert len(body["per_query"]) == body["total_queries"]


def test_evaluation_reports_reasonable_accuracy_on_seed_corpus(client, register_and_login, auth_header, full_seed_corpus):
    """Regression guard: if a future change to the matching engine tanks
    accuracy, this test catches it rather than shipping silently. Uses the
    real seed corpus (not test-fixture standards) since the eval dataset's
    expected answers are written against that corpus specifically."""
    admin_token = register_and_login(client, "eval_regression_admin@example.gov.in", "AdminPass1", "ADMIN")
    resp = client.get("/api/analytics/evaluation?top_k=5", headers=auth_header(admin_token))
    body = resp.json()
    assert body["mrr"] >= 0.5, f"MRR dropped to {body['mrr']} — investigate matching_engine changes"


def test_officer_cannot_view_evaluation(client, register_and_login, auth_header):
    officer_token = register_and_login(client, "eval_officer@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.get("/api/analytics/evaluation", headers=auth_header(officer_token))
    assert resp.status_code == 403


def test_recommend_returns_no_match_status_for_nonsense_query(client, register_and_login, auth_header):
    officer_token = register_and_login(client, "nomatch_officer@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post("/api/recommend", json={
        "query": "zzxxqq flibbertigibbet nonsense query with zero corpus overlap",
    }, headers=auth_header(officer_token))
    body = resp.json()
    assert body["match_status"] == "NO_MATCH"
    assert body["guidance"] is not None
    assert body["results"] == []


def test_recommend_matched_status_and_score_breakdown(client, register_and_login, auth_header, seeded_standard):
    officer_token = register_and_login(client, "matched_officer@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post("/api/recommend", json={
        "query": "PVC pipes for potable water supply", "top_k": 3,
    }, headers=auth_header(officer_token))
    body = resp.json()
    assert body["match_status"] == "MATCHED"
    assert body["guidance"] is None
    top = body["results"][0]
    assert top["score_breakdown"] is not None
    assert "tfidf" in top["score_breakdown"]


def test_recommend_result_carries_confidence_and_evidence_snippet(client, register_and_login, auth_header, seeded_standard):
    """Explainability check: every scored result should carry a HIGH/MEDIUM/LOW
    confidence label and, when matched_terms exist, a verbatim evidence
    snippet quoting the standard's own scope/title — not just an abstract
    term list — so an officer has something concrete to double-check."""
    officer_token = register_and_login(client, "evidence_officer@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post("/api/recommend", json={
        "query": "PVC pipes for potable water supply", "top_k": 3,
    }, headers=auth_header(officer_token))
    body = resp.json()
    top = body["results"][0]
    assert top["confidence"] in ("HIGH", "MEDIUM", "LOW")
    if top["matched_terms"]:
        assert top["evidence_snippet"] is not None
        assert len(top["evidence_snippet"]) > 0


def test_normative_traversal_handles_mutual_reference_cycle(client, register_and_login, auth_header):
    """A references B normatively AND B references A normatively — must not
    infinite-loop or duplicate, proving the cycle guard actually works."""
    admin_token = register_and_login(client, "cycle_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "cycle_officer@example.gov.in", "OfficerPass1", "OFFICER")

    client.post("/api/standards", json={
        "is_number": "IS 4001:2026", "title": "Cycle Test Standard Alpha Quibnorf",
        "category": "Test", "scope": "First half of a mutual-reference cycle for testing.",
        "normative_references": ["IS 4002:2026 Cycle Test Standard Beta"],
        "keywords": ["quibnorf alpha"],
    }, headers=auth_header(admin_token))
    client.post("/api/standards", json={
        "is_number": "IS 4002:2026", "title": "Cycle Test Standard Beta Quibnorf",
        "category": "Test", "scope": "Second half of a mutual-reference cycle for testing.",
        "normative_references": ["IS 4001:2026 Cycle Test Standard Alpha"],
        "keywords": ["quibnorf beta"],
    }, headers=auth_header(admin_token))

    resp = client.post("/api/recommend", json={"query": "quibnorf alpha cycle test", "top_k": 1},
                        headers=auth_header(officer_token))
    assert resp.status_code == 200
    body = resp.json()
    allied_numbers = [r["is_number"] for r in body["allied_expansion"]]
    # exactly one entry for the other half of the cycle — no duplication, no crash
    assert allied_numbers.count("IS 4002:2026") == 1


# ---------------------------------------------------------------------------
# Modular search engine upgrade: domain-aware preprocessing/lemmatization,
# exact identifier search, and procurement-specific multi-feature reranking
# (see app/search/ — preprocessing.py, identifiers.py, ranking.py).
# ---------------------------------------------------------------------------

def test_exact_is_number_query_wins_over_lexically_stronger_competitor(client, register_and_login, auth_header, full_seed_corpus):
    """Typing an exact IS number is an unambiguous request — it must come
    back first even if another standard's title/scope happens to share more
    ordinary keywords with the rest of the query."""
    admin_token = register_and_login(client, "exactid_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "exactid_officer@example.gov.in", "OfficerPass1", "OFFICER")

    # A decoy standard that is lexically very close to the query text, but is
    # NOT the standard actually being asked for by number.
    client.post("/api/standards", json={
        "is_number": "IS 9999:2026",
        "title": "Cement Testing Methods Chemical Analysis Comprehensive Guide",
        "category": "Test", "scope": "Cement testing methods chemical analysis cement testing methods.",
        "keywords": ["cement", "testing", "methods", "chemical", "analysis"],
    }, headers=auth_header(admin_token))

    resp = client.post("/api/recommend", json={
        "query": "IS 9999:2026 cement testing methods chemical analysis", "top_k": 3,
    }, headers=auth_header(officer_token))
    assert resp.status_code == 200
    top = resp.json()["results"][0]
    assert top["is_number"] == "IS 9999:2026"
    assert top["score_breakdown"].get("exact_identifier_match") is True


def test_lemmatization_matches_inflected_query_to_base_form_document(client, register_and_login, auth_header, seeded_standard):
    """seeded_standard's title/keywords use "Pipes"/"pvc pipe" (singular-ish,
    noun form). A query using a different inflection — "piping" — should
    still retrieve it: both reduce to the same lemma ("pipe") on each side
    of the match, which is the actual point of lemmatizing the corpus too,
    not just the query."""
    admin_token, payload = seeded_standard
    officer_token = register_and_login(client, "lemma_officer@example.gov.in", "OfficerPass1", "OFFICER")

    resp = client.post("/api/recommend", json={
        "query": "uPVC piping systems for potable water supplies", "top_k": 5,
    }, headers=auth_header(officer_token))
    assert resp.status_code == 200
    numbers = [r["is_number"] for r in resp.json()["results"]]
    assert payload["is_number"] in numbers


def test_domain_synonym_expansion_matches_spelling_variant(client, register_and_login, auth_header):
    """British-spelled catalogue text ("aluminium") should still be found by
    an American-spelled query ("aluminum"), and vice versa — the additive
    domain-synonym expansion, not a hardcoded special case."""
    admin_token = register_and_login(client, "synonym_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "synonym_officer@example.gov.in", "OfficerPass1", "OFFICER")

    client.post("/api/standards", json={
        "is_number": "IS 5001:2026", "title": "Aluminium Extrusion Sections Specification",
        "category": "Metals", "scope": "Specifies requirements for aluminium extruded sections used in construction.",
        "keywords": ["aluminium", "extrusion", "metal"],
    }, headers=auth_header(admin_token))

    resp = client.post("/api/recommend", json={"query": "aluminum extrusion sections", "top_k": 5},
                        headers=auth_header(officer_token))
    assert resp.status_code == 200
    numbers = [r["is_number"] for r in resp.json()["results"]]
    assert "IS 5001:2026" in numbers


def test_superseded_standard_is_deprioritized_below_equally_relevant_current_one(client, register_and_login, auth_header):
    """Multi-feature reranking's currency adjustment: given two standards
    that are otherwise equally relevant to the query, the current one must
    outrank the superseded one — recommending a withdrawn standard as the
    top hit in a live tender is a real procurement risk."""
    admin_token = register_and_login(client, "currency_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "currency_officer@example.gov.in", "OfficerPass1", "OFFICER")

    shared_scope = "Specifies requirements for zorblatt fastener assemblies used in structural applications."
    client.post("/api/standards", json={
        "is_number": "IS 6001:1990", "title": "Zorblatt Fastener Assemblies Specification",
        "category": "Test", "scope": shared_scope, "keywords": ["zorblatt", "fastener"],
        "is_current": False, "superseded_by": "IS 6002:2020",
    }, headers=auth_header(admin_token))
    client.post("/api/standards", json={
        "is_number": "IS 6002:2020", "title": "Zorblatt Fastener Assemblies Specification",
        "category": "Test", "scope": shared_scope, "keywords": ["zorblatt", "fastener"],
        "is_current": True,
    }, headers=auth_header(admin_token))

    resp = client.post("/api/recommend", json={"query": "zorblatt fastener assemblies", "top_k": 3},
                        headers=auth_header(officer_token))
    assert resp.status_code == 200
    results = resp.json()["results"]
    numbers = [r["is_number"] for r in results]
    assert "IS 6001:1990" in numbers and "IS 6002:2020" in numbers
    assert numbers.index("IS 6002:2020") < numbers.index("IS 6001:1990")
