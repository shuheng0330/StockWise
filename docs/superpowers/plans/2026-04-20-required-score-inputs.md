# Required Score Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require the score-driving owner inputs so CSV upload, manual entry, and record edits all preserve high-quality recommendation inputs.

**Architecture:** Tighten the canonical input contract in the shared schema and validation layer, then let normalization and scoring continue consuming the same normalized fields. Keep legacy dataset CSV support by allowing `recent_waste_percentage` to satisfy the waste-signal requirement when `perishability_level` is absent, and update the docs folder to remain the source of truth.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest

---

### Task 1: Add Contract Tests

**Files:**
- Modify: `tests/services/test_validation.py`
- Modify: `tests/api/test_api.py`

- [ ] **Step 1: Write the failing tests**

Add tests covering:
- manual payload rejects missing `price_per_unit`
- manual payload rejects missing `seasonal_factor`
- manual payload rejects when both `perishability_level` and `recent_waste_percentage` are missing
- manual payload accepts `recent_waste_percentage` without `perishability_level`
- manual analysis API payloads include the newly required score inputs

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/services/test_validation.py tests/api/test_api.py -q`
Expected: FAIL with validation expectations not yet enforced

- [ ] **Step 3: Write minimal implementation**

Update the shared contract and validation layer so these tests pass while legacy CSV support remains intact.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/services/test_validation.py tests/api/test_api.py -q`
Expected: PASS

### Task 2: Update Shared Contract and Normalization

**Files:**
- Modify: `src/stockwise_api/contracts.py`
- Modify: `src/stockwise_api/services/validation.py`
- Modify: `src/stockwise_api/schemas.py`
- Modify: `src/stockwise_api/services/manual_input.py`

- [ ] **Step 1: Enforce required score inputs in the canonical schema**

Require:
- `price_per_unit`
- `seasonal_factor`
- one waste signal: `perishability_level` or `recent_waste_percentage`

- [ ] **Step 2: Preserve record-update compatibility**

Keep partial update models partial, but ensure merged records still validate through the stricter canonical contract.

- [ ] **Step 3: Remove no-longer-needed normalization defaults**

Only keep defaults for non-score fields and optional overrides that remain intentionally optional.

- [ ] **Step 4: Run verification**

Run: `python -m pytest tests/services/test_validation.py tests/api/test_api.py tests/services/test_analysis_pipeline.py -q`
Expected: PASS

### Task 3: Update Source-of-Truth Docs

**Files:**
- Modify: `docs/project-requirements.md`
- Modify: `docs/architecture-and-coding-design.md`
- Modify: `docs/project-status.md`

- [ ] **Step 1: Update the documented canonical contract**

Document the new required score-driving fields and the rule that legacy CSV can satisfy the waste-signal requirement through `Waste_Percentage`.

- [ ] **Step 2: Update architecture notes**

Document where the requirement is enforced and which normalization defaults remain.

- [ ] **Step 3: Update project status**

Record the contract change and the expectation that docs stay synced with future schema changes.

- [ ] **Step 4: Run full verification**

Run: `python -m pytest -q`
Expected: PASS
