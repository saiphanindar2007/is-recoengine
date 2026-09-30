"""
Labelled evaluation set for measuring recommendation accuracy against the
seeded standards corpus (backend/app/seed_standards.json).

Each entry is a realistic procurement query paired with the IS number a
domain-reasonable procurement officer would expect as the primary match.
This is intentionally NOT self-generated from the corpus text (which would
make the evaluation tautological and always score ~100%) — queries are
phrased the way an officer would actually write a specification, often
using different vocabulary than the standard's own title (e.g. "geyser"
for "water heater", "TMT bars" for "deformed steel bars").

Run `python -m app.evaluation` to print metrics from the command line, or
GET /api/analytics/evaluation (ADMIN/AUDITOR) for the same computed live
against whatever standards are currently in the database.
"""

EVAL_DATASET = [
    {"query": "PVC pipes for potable water supply in a housing scheme",
     "expected_is_number": "IS 4985:2021"},
    {"query": "TMT reinforcement bars for a multi-storey RCC building",
     "expected_is_number": "IS 1786:2008"},
    {"query": "Portland cement for a bridge construction project",
     "expected_is_number": "IS 1652:2021"},
    {"query": "solar photovoltaic modules for a rooftop installation tender",
     "expected_is_number": "IS 15410:2003"},
    {"query": "lithium-ion battery pack for an electric two-wheeler",
     "expected_is_number": "IS 16046 (Part 2):2018"},
    {"query": "safety requirements for a household mixer grinder",
     "expected_is_number": "IS 302 (Part 2/Sec 3):1994"},
    {"query": "geyser safety standard for a government hostel",
     "expected_is_number": "IS 302 (Part 2/Section 9):1994"},
    {"query": "drinking water quality specification for a municipal supply",
     "expected_is_number": "IS 10500:2012"},
    {"query": "toy safety requirements for retail sale to children",
     "expected_is_number": "IS 2500:2000"},
    {"query": "hot rolled structural steel plates for a warehouse frame",
     "expected_is_number": "IS 2062:2011"},
    {"query": "code of practice for earthing an electrical installation",
     "expected_is_number": "IS 3043:2018"},
    {"query": "PVC insulated electrical wiring cable for a building",
     "expected_is_number": "IS 694:2010"},
    {"query": "safety standard for laptops and desktop computers procurement",
     "expected_is_number": "IS 13252 (Part 1):2010"},
    {"query": "HDPE pipes for agricultural irrigation supply",
     "expected_is_number": "IS 15778:2007"},
    {"query": "mild steel tubes for general engineering piping",
     "expected_is_number": "IS 1239 (Part 1):2004"},
    {"query": "wind load design code for a new government building",
     "expected_is_number": "IS 875 (Part 3):2015"},
    {"query": "hexagon head bolts and nuts for machinery assembly",
     "expected_is_number": "IS 1364 (Part 1):2018"},
    {"query": "food safety management system requirements for a canteen contractor",
     "expected_is_number": "IS 15000 (Part 1):2018"},
]
