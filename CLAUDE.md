# [Project Name] — Claude Code Context

## Project Overview

<!-- One paragraph: what does this project do? -->

**PRD:** `docs/prd/v1.0-prd.md`
**Build Guide:** `docs/build-guides/v1.0-build-guide.md`
**Process:** `docs/process.md` — branch/PR cadence, pre-commit + pre-PR agent gates, trivial-change fast path, phase-boundary rituals. Read this before any feature work.

<!-- If using issue tracking, add details here:
**Issue Tracking:** [Tool] — [project/board name], [team/key]
-->

---

## Architecture

<!-- High-level architecture diagram or description -->

```
[Frontend]
    → [API Layer]
    → [Compute]
    → [Data Store]
```

<!-- Key technology choices -->

- **Frontend:**
- **Auth:**
- **API:**
- **Compute:**
- **Persistence:**
- **IaC:**
- **CI/CD:**

<!-- Environment details -->

<!-- Example:
**Cloud Account:** 123456789012
**Region:** eu-west-1
**GitHub Repo:** user/repo
-->

---

## Repository Structure

```
project/
├── CLAUDE.md                        # This file
├── docs/
│   ├── prd/                         # Product requirements
│   ├── build-guides/                # Implementation guides
│   ├── process.md                   # Development process and agent cadence
│   ├── tech-debt.md                 # Known gaps and drift
│   └── decisions/                   # Architecture Decision Records
├── ...                              # Project-specific structure
```

<!-- Document your project's directory structure here.
     Keep this updated — the doc-generator agent refreshes it at phase boundaries. -->

---

## Key Patterns

<!-- Document the important architectural patterns, conventions, and contracts
     that someone working on the codebase needs to know. Examples:

- How auth tokens flow through the system
- How errors are structured and propagated
- Shared module/helper contracts
- Naming conventions for files, functions, routes
- Data model patterns (e.g. DynamoDB single-table design, SQL schema conventions)
-->

---

## Testing

| Level | Tool | Scope |
|-------|------|-------|
| Unit | | |
| Integration | | |
| E2E | | |

<!-- Add run commands:
Run tests: `npm test` / `pytest` / etc.
-->

---

## Git Workflow

**Branch strategy:** Feature branches → PR → merge to main.

```
main                    ← production; protected
└── feature/<slug>      ← feature work
└── fix/<slug>          ← bug fixes
```

<!-- Document your branch naming conventions and typical flow -->

---

## Deployment

<!-- How does code get from main to production?
- Infrastructure: terraform apply / CloudFormation / etc.
- Application: auto-deploy on merge / manual deploy / etc.
- CI/CD: which workflows run on PR vs merge
-->

---

## Common Pitfalls & Constraints

<!-- Document the things that have bitten you or will bite someone new.
     These are the hard-won lessons — keep them updated.

Examples:
- Service X has a 30s timeout that affects Y
- Config Z must be set before first deploy
- Region constraint on service W
- Item size limits on data store
-->

---

## Updating this document

This file is maintained by the **doc-generator** agent at phase boundaries and should reflect the current state of the codebase. If you notice drift between this document and reality, fix it — stale context is worse than no context.
