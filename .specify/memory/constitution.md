# sms_quick Constitution

## Core Principles

### I. Library-First Principle
Every feature MUST begin as a standalone library—no exceptions. This forces modular design from the start. Libraries must be self-contained, independently testable, and documented. Clear purpose required - no organizational-only libraries.

### II. CLI Interface Mandate
Every library MUST expose its functionality through a command-line interface. All CLI interfaces MUST accept text as input (via stdin, arguments, or files) and produce text as output (via stdout). Support JSON format for structured data exchange.

### III. Test-First Imperative (NON-NEGOTIABLE)
TDD mandatory: Tests written → User approved → Tests fail → Then implement. Red-Green-Refactor cycle strictly enforced. Contract tests required before implementation.

### IV. Integration Testing
Focus areas requiring integration tests: New library contract tests, Contract changes, Inter-service communication, Shared schemas. Prefer real databases over mocks. Use actual service instances over stubs.

### V. Observability, Simplicity, and Anti-Abstraction
Text I/O ensures debuggability; Structured logging required. Start simple, YAGNI principles. Use framework features directly rather than wrapping them. Maximum 3 projects for initial implementation. Additional projects require documented justification.

## Additional Constraints
Technology stack: Python-based with modern frameworks. Focus on maintainable, scalable code. Security best practices mandatory. Performance requirements: Response times under 500ms for user interactions.

## Development Workflow
Code review requirements: All changes reviewed by at least one maintainer. Testing gates: Unit tests pass, integration tests pass. Deployment approval process: Automated CI/CD with manual approval for production.

## Governance
Constitution supersedes all other practices. Amendments require documentation, approval, and backwards compatibility assessment. All PRs/reviews must verify compliance. Complexity must be justified. Use constitution.md for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2025-10-31 | **Last Amended**: 2025-10-31
