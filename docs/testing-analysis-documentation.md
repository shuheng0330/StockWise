# StockWise Testing Analysis Documentation

## Document Control
- Project: StockWise (UMHackathon 2026)
- Document type: Quality Assurance Testing Analysis
- Version: 1.0 (analysis baseline)
- Date: 2026-04-24
- Prepared by: GitHub Advisor (GPT-5.3-Codex) based on repository evidence
- Source references:
  - docs/project-requirements.md
  - docs/architecture-and-coding-design.md
  - docs/frontend-pages-and-fields.md
  - docs/project-status.md
  - tests/api/test_api.py
  - tests/services/*.py
  - frontend/src/**/*.test.ts*

## Objective
This document defines the test strategy, execution baseline, risk posture, and release-quality gates for StockWise. It converts current implementation and tests into a traceable QA plan that can be used for hackathon judging, team communication, and CI/CD control.

## Preliminary Round: Test Strategy and Planning

## 1. Scope and Requirements Traceability

### 1.1 In-Scope Core Features
- Inventory ingestion:
  - CSV upload with owner-friendly and legacy header support.
  - Manual analysis with canonical item contract and validation.
- Deterministic analytics:
  - Metric computation and recommendation scoring.
  - KPI summary and ranked actions.
- Record lifecycle:
  - List records.
  - Update item and recompute ranking/KPIs.
  - Delete item/group with safety guardrails.
- Scenario analysis:
  - Item-level reorder simulation.
- AI capability layer:
  - Item explanation endpoint.
  - AI decision brief endpoint.
  - AI Advisor chat endpoint with simulation handoff.
- Persistence and ownership:
  - Supabase observation persistence.
  - Snapshot fallback behavior.
  - User-scoped read/write behavior.
- Frontend unit behavior:
  - Decision brief rendering states.
  - AI Advisor request builders.
  - Navigation/session helpers.

### 1.2 Out-of-Scope (Current MVP)
- Full production-grade non-functional validation (full-scale load/stress/security test suite).
- End-to-end browser automation coverage for all pages.
- Role-based multi-tenant UI testing beyond current auth-scoped API tests.
- Full deployment hardening validation across multi-environment cloud topologies.

### 1.3 Requirements Traceability Matrix (RTM)

| Req ID | Requirement | Implementation Surface | Test Evidence | Status |
|---|---|---|---|---|
| R1 | CSV upload accepts owner-friendly and legacy formats | POST /api/v1/analyses, validation mapping | tests/api/test_api.py, tests/services/test_validation.py | Covered |
| R2 | Manual entry uses canonical fields and strict required score inputs | POST /api/v1/manual-analyses | tests/api/test_api.py, tests/services/test_manual_input.py, tests/services/test_validation.py | Covered |
| R3 | Historical observations collapse to latest item metrics with trend signals | normalize_item_history, upload/manual analysis flow | tests/api/test_api.py, tests/services/test_manual_input.py | Covered |
| R4 | Ranked recommendation output and KPI summary are produced consistently | recommendations + analysis pipeline | tests/services/test_analysis_pipeline.py, tests/api/test_api.py | Covered |
| R5 | Records review/edit/delete updates analysis and enforces guardrails | records GET/PATCH/DELETE routes | tests/api/test_api.py | Covered |
| R6 | Simulation returns scenario metrics and updated recommendation | simulate endpoint + simulation service | tests/api/test_api.py, tests/services/test_analysis_pipeline.py | Covered |
| R7 | Explanation endpoint is safe with retry and deterministic fallback | explanation route + parsing fallback | tests/api/test_api.py, tests/services/test_parsing.py | Covered |
| R8 | AI chat endpoint provides structured scoped responses and fallback | ai-chat route + chat parser | tests/api/test_api.py, tests/services/test_parsing.py | Covered |
| R9 | Decision brief endpoint validates output and falls back safely | decision-brief route + parser | tests/api/test_api.py, tests/services/test_parsing.py | Covered |
| R10 | Supabase persistence stores source observations and supports snapshots | store + app persistence helpers | tests/services/test_supabase_store.py, tests/api/test_api.py | Covered |
| R11 | User ownership and access scoping are enforced for analyses | auth resolver + latest/get routes | tests/api/test_api.py | Covered |
| R12 | Frontend AI helper logic and decision brief rendering states are stable | frontend lib/components | frontend/src/lib/*.test.ts, frontend/src/components/AIDecisionBriefCard.test.tsx | Covered |

## 2. Risk Assessment and Mitigation Strategy

### 2.1 Scoring Criteria (5x5 Matrix)
- Likelihood scale:
  - 1 Rare
  - 2 Unlikely
  - 3 Possible
  - 4 Likely
  - 5 Almost Certain
- Severity scale:
  - 1 Negligible
  - 2 Minor
  - 3 Moderate
  - 4 Major
  - 5 Critical
- Risk score formula:
  - Risk Score = Likelihood x Severity

### 2.2 Risk Register

| Risk ID | Risk Description | Likelihood | Severity | Score | Mitigation | Current State |
|---|---|---:|---:|---:|---|---|
| RK-01 | AI provider mode/environment drift causes unstable or long-running API tests | 4 | 4 | 16 | Pin GLM_MODE=mock in CI test stage, keep dedicated live-smoke stage separate, enforce test env contract | Active concern |
| RK-02 | Hallucinated or schema-invalid AI output reaches frontend | 3 | 5 | 15 | Strict JSON parsing, schema validation, retry once, deterministic fallback | Mitigated by existing parser tests |
| RK-03 | Supabase latency/failure blocks analysis creation path | 3 | 4 | 12 | Optional operation timeout, best-effort persistence fallback, in-memory response path | Mitigated, monitor in integration |
| RK-04 | Snapshot and user-ownership regression exposes cross-user data | 2 | 5 | 10 | Auth-required route tests, user-scoped retrieval tests, migration verification checklist | Mitigated, high-impact if broken |
| RK-05 | Record edit/delete behavior diverges from persistence semantics | 3 | 3 | 9 | Add integration tests against live migrated schema, define snapshot-local vs persistent mutation policy | Open design follow-up |
| RK-06 | Frontend-backend contract drift for typed payloads/fields | 3 | 3 | 9 | Contract-driven tests, schema sync docs, API mock validation in frontend tests | Partially mitigated |

## 3. Test Environment and Execution Strategy

### 3.1 Environment Baseline
- OS: Windows.
- Backend runtime: Python 3.13.12 (project venv).
- Backend framework: FastAPI.
- Frontend runtime: Next.js + Jest.
- Test framework:
  - Backend: pytest.
  - Frontend: jest.

### 3.2 Test Layers

#### Unit and Service Tests
- Scope:
  - Validation mapping and canonical field enforcement.
  - Manual normalization, history collapse, trend/usage derivation.
  - Recommendation and simulation behavior.
  - GLM provider payload shaping and parser safety/fallback.
  - Supabase store persistence behavior with fake client.
- Evidence:
  - tests/services/test_validation.py
  - tests/services/test_manual_input.py
  - tests/services/test_analysis_pipeline.py
  - tests/services/test_parsing.py
  - tests/services/test_glm.py
  - tests/services/test_supabase_store.py
  - tests/services/test_runtime.py

#### API and Route Integration Tests
- Scope:
  - Endpoints for analyses, records, simulation, explanation, decision brief, ai-chat.
  - Auth handling and user ownership behavior.
  - Supabase fallback and timeout behavior.
- Evidence:
  - tests/api/test_api.py

#### Frontend Unit and Component Tests
- Scope:
  - AI Advisor request builders and session state helpers.
  - Navigation and simulation link builders.
  - Decision brief/loading/fallback rendering logic.
- Evidence:
  - frontend/src/lib/aiAdvisor.test.ts
  - frontend/src/lib/analysisSession.test.ts
  - frontend/src/lib/itemIdentity.test.ts
  - frontend/src/lib/navigationTargets.test.ts
  - frontend/src/lib/simulationFlow.test.ts
  - frontend/src/components/AIDecisionBriefCard.test.tsx

### 3.3 Execution Rules and Pass Conditions
- Unit/service pass condition:
  - Expected outputs and invariants hold for happy path, validation, and fallback scenarios.
- API pass condition:
  - HTTP status, payload shape, and behavior match contracts, including failure/fallback paths.
- Frontend pass condition:
  - Deterministic helper output and expected rendering text/state are present.

### 3.4 Regression Testing Rules
- Trigger:
  - Every merge candidate (PR to main).
- Required checks:
  - Backend service tests.
  - Backend API tests.
  - Frontend unit/component tests.
- Block condition:
  - Any failed critical test.

### 3.5 Test Data Strategy
- Deterministic synthetic data is embedded in tests for:
  - Owner-friendly CSV rows.
  - Legacy CSV rows.
  - Historical multi-day item records.
  - Manual payload permutations with required/optional fields.
- Fake Supabase client and store doubles are used for persistence logic without remote dependency.

### 3.6 Quality Thresholds
- Suggested merge threshold:
  - 100% pass for critical contract tests (validation, auth scoping, fallback safety).
  - 98%+ overall pass for backend+frontend test set in CI.
- Suggested release threshold:
  - 100% pass on critical tests and zero unresolved Severity 4-5 defects.

## 4. CI/CD Release Thresholds and Automation Gates

### 4.1 Integration Gate (PR to Main)
- Mandatory gates:
  - Backend tests with GLM_MODE=mock.
  - Frontend jest tests.
  - Lint/type checks (if configured in pipeline).
- Fail-fast conditions:
  - Any failing test in contract-critical modules.
  - Any schema or payload shape regression.

### 4.2 Deployment Gate (Main to Production/Staging)
- Mandatory gates:
  - PR gate must pass.
  - Live-provider smoke tests for explanation/chat/brief in isolated stage.
  - Supabase migration integrity checks.
  - Auth-scoped access checks for latest and explicit analysis retrieval.
- Blockers:
  - Failed live-smoke for AI safety/fallback behavior.
  - Data ownership leakage risk.

## 5. Test Case Specifications (Drafts)

### 5.1 Happy Case (End-to-End Functional Flow)
- ID: TC-HAPPY-01
- Goal: Verify complete owner journey from data ingest to action support.
- Preconditions:
  - Backend running.
  - GLM_MODE=mock.
- Steps:
  - Upload valid owner-friendly CSV.
  - Open dashboard and verify KPI + ranked items.
  - Run simulation on one item.
  - Request explanation and decision brief.
  - Ask AI Advisor question with and without simulation context.
- Expected result:
  - All endpoints return valid schema payloads with deterministic/fallback-safe fields.

### 5.2 Negative/Edge Case
- ID: TC-NEG-01
- Goal: Ensure strict canonical validation and safe API error handling.
- Steps:
  - Submit manual item missing required score-driving fields.
  - Submit invalid usage_period.
  - Attempt unauthorized access to protected route.
- Expected result:
  - Validation error (422 or documented error envelope).
  - Auth error (401).
  - No server crash.

### 5.3 Non-Functional Test: Latency Guard
- ID: TC-NFR-01
- Goal: Ensure optional Supabase operations do not block request path indefinitely.
- Method:
  - Inject slow Supabase store double.
  - Verify response returns under configured timeout behavior.
- Existing evidence:
  - tests/api/test_api.py contains timeout resilience scenario.

### 5.4 Non-Functional Test: Load/Concurrency Draft
- ID: TC-NFR-02
- Goal: Validate stable response behavior under burst uploads and chat requests.
- Draft approach:
  - Use k6/Locust in staging with GLM_MODE=mock baseline first.
  - Measure p95 latency, error rate, and fallback rate.
- Acceptance target:
  - p95 API latency under agreed threshold for key endpoints.
  - Error rate below 1% excluding intentional negative tests.

## 6. AI Output and Boundary Testing (Drafts)

### 6.1 Prompt/Response Test Pairs

| ID | Prompt Type | Expected Acceptable Response | Failure Signal |
|---|---|---|---|
| AI-01 | Explanation request for high waste-risk item | Valid JSON schema, correct item_name/action consistency, concise safe rationale | Invalid JSON, wrong item binding, unsupported profit/revenue claims |
| AI-02 | Dashboard decision brief generation | Structured brief with safe source/safety_status and valid item references | Unknown item IDs, hallucinated entities, missing required keys |
| AI-03 | Advisor query with simulation context | Scope reflects simulation, related_items are bounded to analysis items | Off-scope response, unrelated items, malformed structured arrays |

### 6.2 Oversized Input Test
- Define max accepted prompt/message length for ai-chat payload.
- Verify behavior when exceeded:
  - Graceful validation response, or
  - Controlled truncation plus warning.

### 6.3 Adversarial/Edge Prompt Test
- Example prompt:
  - Off-topic user input mixed with inventory keywords.
- Expected behavior:
  - Deterministic refusal or constrained inventory-focused response.
- Existing evidence:
  - Off-topic refusal test exists in tests/api/test_api.py.

### 6.4 Hallucination Handling
- Required control chain:
  - Parse JSON.
  - Validate schema and allowed entities.
  - Retry once with stricter context.
  - Fallback deterministic payload if still invalid.
- Existing evidence:
  - Parsing and fallback tests in tests/services/test_parsing.py.
  - Route-level fallback tests in tests/api/test_api.py.

## 7. Current Test Execution Baseline (2026-04-24)

### 7.1 Backend Test Discovery
- Collected tests: 111 total.
- Breakdown:
  - tests/api/test_api.py: 41
  - tests/services/test_analysis_pipeline.py: 6
  - tests/services/test_glm.py: 14
  - tests/services/test_manual_input.py: 5
  - tests/services/test_parsing.py: 20
  - tests/services/test_runtime.py: 2
  - tests/services/test_supabase_store.py: 10
  - tests/services/test_validation.py: 13

### 7.2 Backend Execution Result
- Execution mode used for deterministic run: GLM_MODE=mock.
- Outcome:
  - 110 passed
  - 1 failed
- Failing test:
  - tests/services/test_glm.py::test_live_provider_raises_when_stream_has_no_visible_content
- Failure summary:
  - Expected RuntimeError on empty streamed visible content, but provider retried non-streaming and did not raise.

### 7.3 Frontend Execution Result
- Command: npm run test -- --watch=false
- Outcome:
  - Test suites: 6 passed, 6 total
  - Tests: 17 passed, 17 total

### 7.4 Observed Environment Sensitivity
- Running API explanation tests without forcing mock mode can become long-running depending on live-provider environment configuration.
- Confirmed that setting GLM_MODE=mock makes the previously slow test complete quickly.

## 8. Gaps and Recommendations

### 8.1 Key Gaps
- No full browser E2E coverage for the complete frontend journey.
- Limited automated performance/load testing in current repo.
- Live-provider behavior is partially environment-dependent during test execution.

### 8.2 Priority Actions
1. Pin GLM_MODE=mock in CI unit/integration test stage.
2. Add separate opt-in live smoke pipeline for AI provider integration.
3. Fix or align expected behavior in tests/services/test_glm.py for empty-stream handling policy.
4. Add lightweight E2E happy-path test across upload -> dashboard -> simulation -> explanation.
5. Add baseline load test profile for core API endpoints.

## 9. Conclusion
StockWise currently has strong functional and contract-centric test coverage for backend services, API behavior, and key frontend logic paths. The system demonstrates mature defensive behavior around AI output validation and fallback safety. The immediate quality priorities are to stabilize environment-sensitive AI-provider test behavior in CI and extend non-functional and E2E coverage for release readiness.
