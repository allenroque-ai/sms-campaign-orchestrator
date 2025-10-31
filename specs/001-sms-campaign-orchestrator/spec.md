# Feature Specification: SMS Campaign Orchestrator

**Feature Branch**: `001-sms-campaign-orchestrator`  
**Created**: 2025-10-31  
**Status**: Draft  
**Input**: User description: "Build a library-first, CLI-driven, TDD-enforced redesign of the SMS Buyer/Non-Buyer campaign generator complying with the engineering constitution. The tool connects to Netlife/portal backends, enumerates jobs/activities in webshop selling status, enriches subjects, builds campaign dataset with buyers/non-buyers, applies filters, deduplicates, and writes CSV for downstream SMS tooling."

## User Scenarios & Testing

### User Story 1 - Generate Buyer Campaign Dataset (Priority: P1)

As a campaign manager, I want to generate a CSV dataset of buyers from portal jobs so that I can send targeted SMS campaigns to customers who have made purchases.

**Why this priority**: Core business functionality for buyer segmentation and targeted marketing.

**Independent Test**: Can be fully tested by running the CLI with buyer filter and verifying the output CSV contains only buyer contacts with correct enrichment.

**Acceptance Scenarios**:

1. **Given** jobs in "webshop (selling)" status exist in portal, **When** I run `campaign-cli build --buyers`, **Then** I get a CSV with buyer contacts, consent timestamps, and prioritized delivery info.
2. **Given** no buyer activities found, **When** I run `campaign-cli build --buyers`, **Then** I get an empty CSV with headers.
3. **Given** portal connection fails, **When** I run `campaign-cli build --buyers`, **Then** CLI exits with error code and logs the failure.

---

### User Story 2 - Generate Non-Buyer Campaign Dataset (Priority: P1)

As a campaign manager, I want to generate a CSV dataset of non-buyers from portal jobs so that I can send promotional SMS campaigns to prospects.

**Why this priority**: Core business functionality for prospect outreach and conversion.

**Independent Test**: Can be fully tested by running the CLI with non-buyers filter and verifying the output CSV contains prospect contacts.

**Acceptance Scenarios**:

1. **Given** jobs with non-buyer subjects exist, **When** I run `campaign-cli build --non-buyers`, **Then** I get a CSV with non-buyer contacts and enrichment data.
2. **Given** mixed buyer/non-buyer data, **When** I run `campaign-cli build --non-buyers`, **Then** only non-buyer records are included.

---

### User Story 3 - Apply Filters and Deduplication (Priority: P2)

As a campaign manager, I want to filter campaigns by buyer/contact/group/job criteria and ensure deduplication so that contacts receive appropriate, non-duplicate SMS.

**Why this priority**: Ensures data quality and prevents spam/duplicates.

**Independent Test**: Can be tested by providing input with duplicates and filters, verifying output is deduplicated and filtered correctly.

**Acceptance Scenarios**:

1. **Given** input with duplicate activity+subject combinations, **When** I run build, **Then** output has no duplicates.
2. **Given** filter criteria, **When** I run build with filters, **Then** only matching records are included.

---

### User Story 4 - Export in Multiple Formats (Priority: P2)

As a downstream system integrator, I want to receive campaign data in both CSV and JSON formats so that I can integrate with various SMS tooling.

**Why this priority**: Enables flexible integration with existing SMS infrastructure.

**Independent Test**: Can be tested by running with --json flag and verifying JSON schema matches CSV structure.

**Acceptance Scenarios**:

1. **Given** campaign data, **When** I run `campaign-cli build --json`, **Then** I get JSON output with same data as CSV.
2. **Given** no data, **When** I run `campaign-cli build --json`, **Then** I get empty JSON array.

---

### User Story 5 - Parallel Processing and Performance (Priority: P3)

As an operations engineer, I want the tool to support parallel job batching with configurable concurrency so that large campaigns process efficiently within SLAs.

**Why this priority**: Performance optimization for scalability.

**Independent Test**: Can be tested with mock data and timing measurements.

**Acceptance Scenarios**:

1. **Given** large job set, **When** I run with `--concurrency 4`, **Then** processing completes faster than single-threaded.
2. **Given** rate limits, **When** I run with high concurrency, **Then** backoff is applied to respect limits.

---

### Edge Cases

- What happens when portal APIs return empty results?
- How does system handle network timeouts or connection failures?
- What if job counts exceed expected O(10-100) range?
- How handle subjects with missing consent data?
- What happens with malformed input data?
- How system behaves with very large subject sets (O(10^4+))?
- What if access key generation fails?

## Requirements

### Functional Requirements

- **FR-001**: System MUST be split into ≤3 projects: `campaign-core` (pure library), `campaign-cli` (thin CLI), `campaign-contracts` (schemas/tests).
- **FR-002**: CLI MUST accept input via stdin/args/files and emit output to stdout in CSV format by default, with optional JSON via `--json`.
- **FR-003**: System MUST enforce TDD with Red-Green-Refactor cycle and contract tests defining output schemas.
- **FR-004**: System MUST support integration tests for contracts, DB access, and service calls using real instances where feasible.
- **FR-005**: System MUST provide structured logging to stdout with trace IDs, timings, and counters.
- **FR-006**: System MUST achieve <500ms response for lightweight operations and maintain current SLA performance.
- **FR-007**: System MUST implement security best practices with no secrets in code, input validation, and PII masking.
- **FR-008**: CI/CD MUST enforce unit/integration tests, contract tests, maintainer review, and manual prod approval.
- **FR-009**: System MUST comply with `constitution.md` with PR checklists and amendment processes.
- **FR-010**: Deployment MUST use AWS Blue/Green strategy with health checks and traffic shifting.
- **FR-011**: CLI MUST support `--concurrency` and backoff controls for parallel processing.
- **FR-012**: System MUST ensure idempotent runs with deterministic sorting and stable keys.
- **FR-013**: System MUST support pluggable data sources via config.
- **FR-014**: CLI command MUST be `campaign-cli build [--jobs FILE|--jobs-url URL|--job-id ID ...] [--buyers|--non-buyers|--both] [--json] [--out PATH|s3://bucket/key] [--concurrency N] [--dry-run]`

### Key Entities

- **Job**: Represents a portal job with status (webshop selling), contains activities.
- **Activity**: Individual selling activity within a job, linked to subjects.
- **Subject**: Customer/prospect with contact info, consent data, purchase history.
- **Contact**: Communication endpoint (phone) with prioritization (user → deliveries).
- **Campaign Dataset**: Generated output with enriched contacts, filters applied, deduplicated.

## Success Criteria

### Measurable Outcomes

- **SC-001**: CLI startup time <1 second and simple queries complete in <500ms.
- **SC-002**: Output CSV/JSON schema matches current tool exactly.
- **SC-003**: All contract tests pass with 100% coverage of defined schemas.
- **SC-004**: Batch processing handles O(100) jobs and O(10^4) subjects within current SLAs.
- **SC-005**: System processes campaigns without direct SMS dispatch (MVP scope).
- **SC-006**: Parallel processing with `--concurrency` improves performance by 2-4x for large datasets.
- **SC-007**: Idempotent runs produce identical output for same input.
- **SC-008**: Security audit passes with no high-severity vulnerabilities.
- **SC-009**: CI/CD gates prevent deployment of non-compliant code.
- **SC-010**: AWS Blue/Green deployments complete without downtime.</content>
<parameter name="filePath">/home/allenroque/netlife-env/sms_quick/specs/001-sms-campaign-orchestrator/spec.md