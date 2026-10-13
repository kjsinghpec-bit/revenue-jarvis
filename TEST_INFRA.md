# E2E Test Infra: Revenue-Jarvis OCR Pipeline & Database Hardening

## Test Philosophy
- Opaque-box, requirement-driven. Verifies behavior strictly against `ORIGINAL_REQUEST.md` and user-facing acceptance criteria.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Interaction Testing + Real-World Workload Testing.

## Feature Inventory & Test Matrix
| # | Feature | Source | Tier 1 (Coverage) | Tier 2 (Boundary/Edge) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|---------|--------|:-----------------:|:----------------------:|:-----------------:|:-----------------:|
| F1 | R1: Blocking OCR Pages Repair (113, 175, 261, 167, 171, 183) | ORIGINAL_REQUEST §R1 | ≥5 cases | ≥5 cases | ✓ | ✓ |
| F2 | R2: Orientation & Tabular Extraction (382, 383, 389) | ORIGINAL_REQUEST §R2 | ≥5 cases | ≥5 cases | ✓ | ✓ |
| F3 | R3: Printed Page Label Coverage (>95%, offset PDF-15) | ORIGINAL_REQUEST §R3 | ≥5 cases | ≥5 cases | ✓ | ✓ |
| F4 | R4: Regression & Grounding Safeguard Verification | ORIGINAL_REQUEST §R4 | ≥5 cases | ≥5 cases | ✓ | ✓ |
| F5 | R5: Staged DB Rebuild & Law Corpus Preservation | ORIGINAL_REQUEST §R5 | ≥5 cases | ≥5 cases | ✓ | ✓ |

## Test Architecture
- Test runner: `PYTHONPATH=src .venv/bin/pytest tests/` (or `uv run pytest`)
- Test files:
  - `tests/test_e2e_ocr_pipeline.py` (E2E Track test suite covering Tiers 1–4)
  - `tests/test_ocr_repairs_grounding.py` (M4 dedicated regression suite)
- Pass/Fail semantics: All tests pass with exit code 0.
- Integrity verification: 0 errors in `check_import`, 100% byte-identical statutory law documents and chunks against `reports/ocr_repair/backup/jarvis.production-20261013-141120.db`.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Grounding validation on legal mutation timeline (Section 39 deadline & Collector fine power) | F1, F4, F5 | High |
| 2 | Land partition precedent citation and measurement verification (2008 (1) LAR 132, 230 ਕਨਾਲ 10 ਮਰਲੇ) | F1, F4, F5 | High |
| 3 | Revenue survey chain link calculations & standard Karam conversion (66 inches, 8/7 links) | F1, F4, F5 | High |
| 4 | Jamabandi 12-column tabular register querying and Khasra Girdawari orientation extraction | F2, F5 | High |
| 5 | Full book citation traversal with printed page offset verification across all body chapters | F3, F5 | High |

## Coverage Thresholds
- Tier 1: ≥25 test cases (5 per feature across F1–F5)
- Tier 2: ≥25 boundary and corner cases (5 per feature)
- Tier 3: ≥5 cross-feature integration cases
- Tier 4: ≥5 realistic end-to-end workload cases
- Total target: ≥60 E2E assertions
