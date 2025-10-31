# Implementation Plan: SMS Campaign Orchestrator

**Branch**: `001-sms-campaign-orchestrator` | **Date**: 2025-10-31 | **Spec**: specs/001-sms-campaign-orchestrator/spec.md
**Input**: Feature specification from specs/001-sms-campaign-orchestrator/spec.md

## Summary

Redesign the existing SMS campaign generator as a modular, library-first system with CLI interface, enforcing TDD and constitution compliance. The system will generate buyer/non-buyer campaign datasets from Netlife portal jobs, with filtering, deduplication, and multiple output formats.

## Technical Context

- **Programming Language**: Python 3.12
- **Framework**: None (pure Python with stdlib, optional libraries for CLI parsing, HTTP, JSON)
- **Architecture**: Library-first with 3 projects: campaign-core (business logic), campaign-cli (entry point), campaign-contracts (schemas/tests)
- **Data Sources**: Netlife/portal APIs, local DB for caching
- **Output**: CSV (default), JSON (optional), S3 upload support
- **Deployment**: AWS Lambda or ECS with Blue/Green strategy
- **Security**: AWS IAM, secrets in SSM/Parameter Store, PII masking in logs
- **Performance**: <500ms for simple ops, SLA-compliant for batches
- **Testing**: Contract tests first, integration with real DB/services, unit tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- ✅ I. Library-First: Split into campaign-core, campaign-cli, campaign-contracts
- ✅ II. CLI Interface: Text I/O with stdin/stdout, JSON support
- ✅ III. Test-First: TDD enforced, contract tests define schemas
- ✅ IV. Integration Testing: Tests for contracts, DB, APIs
- ✅ V. Observability: Structured JSON logs to stdout
- ✅ Simplicity: ≤3 projects, no over-abstraction
- ✅ Security: No secrets in code, validation, masking
- ✅ Governance: PR reviews, CI gates, constitution compliance

## Project Structure

### Source Code (repository root)

```
campaign-core/
├── __init__.py
├── models.py          # Job, Activity, Subject, Contact entities
├── services.py        # Portal client, enrichment, filtering logic
├── contracts.py       # Output schema definitions
└── utils.py           # Deduplication, sorting helpers

campaign-cli/
├── __init__.py
├── cli.py             # Argparse-based CLI
└── main.py            # Entry point

campaign-contracts/
├── __init__.py
├── test_contracts.py  # Contract tests for CSV/JSON schemas
└── schemas/           # JSON schema files
```

### Tests

```
tests/
├── unit/
│   ├── test_core.py
│   └── test_cli.py
├── integration/
│   ├── test_portal_integration.py
│   └── test_db_integration.py
└── contract/
    └── test_output_contracts.py
```

### Configuration

```
config/
├── default.json       # Default settings
└── environments/      # Prod, staging configs
```

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations identified. The 3-project structure maintains simplicity while enabling modularity.</content>
<parameter name="filePath">/home/allenroque/netlife-env/sms_quick/specs/001-sms-campaign-orchestrator/plan.md