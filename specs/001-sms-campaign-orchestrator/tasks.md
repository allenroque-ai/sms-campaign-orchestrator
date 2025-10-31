# Tasks: SMS Campaign Orchestrator

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan (campaign-core, campaign-cli, campaign-contracts)
- [ ] T002 Initialize Python 3.12 projects with pyproject.toml and dependencies (requests, pydantic, click)
- [ ] T003 [P] Configure linting (ruff) and formatting (black) tools
- [ ] T004 [P] Setup pre-commit hooks for code quality

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Setup data models in campaign-core/models.py (Job, Activity, Subject, Contact)
- [ ] T006 Implement portal client service in campaign-core/services.py
- [ ] T007 Setup contract tests framework in campaign-contracts/
- [ ] T008 Configure structured JSON logging in campaign-core/utils.py
- [ ] T009 Setup input validation and PII masking utilities
- [ ] T010 Create base CLI structure in campaign-cli/

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Generate Buyer Campaign Dataset (Priority: P1) 🎯 MVP

**Purpose**: Core buyer campaign functionality

### Implementation for User Story 1 (Priority: P1)

- [ ] T011 Implement buyer filtering logic in campaign-core/services.py
- [ ] T012 Add enrichment service for buyer subjects
- [ ] T013 Implement deduplication by activity+subject
- [ ] T014 Add CSV output formatter in campaign-core/
- [ ] T015 Wire CLI --buyers flag to buyer campaign generation

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] Contract test for buyer CSV schema in campaign-contracts/test_contracts.py
- [ ] T017 [P] Integration test for portal buyer data fetching
- [ ] T018 [P] Unit test for buyer filtering and deduplication logic

---

## Phase 4: User Story 2 - Generate Non-Buyer Campaign Dataset (Priority: P1) 🎯 MVP

**Purpose**: Core non-buyer campaign functionality

### Implementation for User Story 2 (Priority: P1)

- [ ] T019 Implement non-buyer filtering logic
- [ ] T020 Add enrichment for prospect subjects
- [ ] T021 Integrate with existing deduplication
- [ ] T022 Wire CLI --non-buyers flag

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T023 [P] Contract test for non-buyer CSV schema
- [ ] T024 [P] Integration test for non-buyer data
- [ ] T025 [P] Unit test for non-buyer filtering

---

## Phase 5: User Story 3 - Apply Filters and Deduplication (Priority: P2)

**Purpose**: Enhanced data quality and filtering

### Implementation for User Story 3 (Priority: P2)

- [ ] T026 Implement buyer/contact/group/job filters
- [ ] T027 Add strict deduplication logic
- [ ] T028 Add filter validation and error handling
- [ ] T029 Update CLI with filter options

### Tests for User Story 3

- [ ] T030 [P] Test filter combinations
- [ ] T031 [P] Test deduplication edge cases

---

## Phase 6: User Story 4 - Export in Multiple Formats (Priority: P2)

**Purpose**: Flexible output formats

### Implementation for User Story 4 (Priority: P2)

- [ ] T032 Add JSON output formatter
- [ ] T033 Implement --json CLI flag
- [ ] T034 Ensure schema consistency between CSV/JSON

### Tests for User Story 4

- [ ] T035 [P] Contract test for JSON schema
- [ ] T036 [P] Test format switching

---

## Phase 7: User Story 5 - Parallel Processing and Performance (Priority: P3)

**Purpose**: Scalability and performance

### Implementation for User Story 5 (Priority: P3)

- [ ] T037 Add --concurrency option with async processing
- [ ] T038 Implement backoff and rate limiting
- [ ] T039 Add performance monitoring and logging

### Tests for User Story 5

- [ ] T040 [P] Performance tests with large datasets
- [ ] T041 [P] Concurrency stress tests

---

## Phase 8: Security and Deployment (Priority: P1)

**Purpose**: Production readiness

### Implementation for Security/Deployment

- [ ] T042 Implement AWS IAM least privilege setup
- [ ] T043 Add secrets management (SSM/Parameter Store)
- [ ] T044 Configure Blue/Green deployment pipeline
- [ ] T045 Add health checks and monitoring

### Tests for Security/Deployment

- [ ] T046 [P] Security audit and penetration testing
- [ ] T047 [P] Deployment smoke tests

---

## Phase 9: Documentation and Validation

**Purpose**: Complete the feature

- [ ] T048 Update README with CLI usage
- [ ] T049 Create runbooks for operations
- [ ] T050 Final integration testing across all user stories
- [ ] T051 Performance validation against SLAs</content>
<parameter name="filePath">/home/allenroque/netlife-env/sms_quick/specs/001-sms-campaign-orchestrator/tasks.md