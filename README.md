# template-repo

A GitHub template repository pre-configured with Claude Code tooling, git hooks, development process, and sensible defaults for starting new projects quickly.

Use this template when creating new repositories to get a working Claude Code setup out of the box, with a suite of specialised AI subagents, a codified development process, and automated quality checks ready to go.

## What's included

### Subagents (`.claude/agents/`)

Nine custom subagents that Claude Code automatically delegates to based on context. They can also be invoked explicitly with `@agent-name` or by asking Claude to use them.

| Agent | Model | Purpose |
|---|---|---|
| `code-reviewer` | Sonnet | Reviews code for style, complexity, anti-patterns, naming, and architectural smells. Read-only. |
| `code-optimiser` | Sonnet | Identifies performance bottlenecks, N+1 queries, unnecessary allocations, and algorithmic inefficiencies. Read-only. |
| `codebase-review` | Sonnet | Scans a repo and produces a structured briefing covering tech stack, architecture, posture assessment, and recommendations. Read-only. |
| `test-generator` | Sonnet | Generates unit tests, suggests edge cases, and reviews existing tests for quality and coverage gaps. |
| `doc-generator` | Sonnet | Creates and updates READMEs, docstrings, API docs, changelogs, and Architecture Decision Records. |
| `devops-reviewer` | Sonnet | Reviews GitHub Actions workflows, Dockerfiles, Kubernetes manifests, and Terraform/CloudFormation templates. |
| `refactorer` | Sonnet | Handles framework upgrades, dependency migrations, and pattern modernisation with incremental, test-verified changes. |
| `linter` | Haiku | Detects and auto-fixes formatting issues, unused imports, and style violations. Uses project linter config when present. |
| `phase-acceptance` | Opus | Validates that a build-guide phase is complete before the PR opens. Checks code against every PRD requirement and verification checkpoint. |

All agents have persistent user-level memory enabled, so they accumulate knowledge about your codebase patterns across sessions.

### Development process (`docs/process.md`)

A codified development process that defines when each agent runs automatically during the PR lifecycle:

- **Pre-commit** — linter runs on every commit
- **Pre-PR gates** — code-reviewer, devops-reviewer, test-generator, and doc-generator run conditionally based on what changed, with findings folded into the branch before the PR opens
- **Phase boundaries** — codebase-review and doc-generator refresh tech-debt tracking and CLAUDE.md at the end of each build-guide phase
- **Phase acceptance** — phase-acceptance validates PRD requirements when a phase closes out
- **Trivial-change fast path** — small changes (≤ 50 lines, ≤ 2 files, no critical paths) skip all gates except the linter

The process doc also covers branch/PR cadence, issue tracking conventions, fold timing for gate findings, and how to handle agent feedback.

### Project context (`CLAUDE.md`)

A skeleton `CLAUDE.md` template with sections for architecture, repository structure, key patterns, testing, git workflow, deployment, and common pitfalls. Fill it in when you start a new project — this is what Claude Code reads to understand your codebase.

Referenced by `docs/process.md`, which instructs the doc-generator agent to keep it updated at phase boundaries.

### Slash commands (`.claude/commands/`)

| Command | Description |
|---|---|
| `/create_worktree <n>` | Creates a new git worktree in `.trees/<n>`, symlinks `.venv`, and opens it in VS Code. |
| `/merge_worktree <n>` | Merges a worktree branch back into the current branch, with automatic conflict resolution. |

### Git hooks (`.githooks/`)

Local git hooks that run automatically to enforce quality standards. No external dependencies required.

| Hook | Trigger | What it does |
|---|---|---|
| `pre-commit` | Before each commit | Scans staged files for secrets (AWS keys, API tokens, private keys, passwords, connection strings) and blocks files over 5MB |
| `commit-msg` | After writing commit message | Validates Conventional Commits format (`type(scope): description`) |
| `pre-push` | Before each push | Validates branch naming follows `type/description` pattern |

All hooks can be bypassed with `--no-verify` when needed.

### GitHub templates (`.github/`)

| File | Purpose |
|---|---|
| `CODEOWNERS` | Default code ownership (`@jacarty` for everything) |
| `SECURITY.md` | Security policy with vulnerability reporting instructions |
| `pull_request_template.md` | Default PR description with What/Why/How sections and a checklist |
| `ISSUE_TEMPLATE/bug_report.yml` | Structured bug report form |
| `ISSUE_TEMPLATE/feature_request.yml` | Structured feature request form |
| `workflows/ci.yml` | Starter CI workflow with commented-out blocks for Python, Node.js, and Go — uncomment what you need |

### Claude Code permissions (`.claude/settings.json`)

Pre-configured tool permissions so Claude Code doesn't prompt for approval on common operations. Covers git, GitHub CLI, Node.js/npm, Python/pytest, and shell utilities.

**Review before using** — the following permissions are included but may be more permissive than you need for every project:

- `Bash(aws:*)` — allows any AWS CLI command without prompting. Remove if the project doesn't use AWS.
- `Bash(terraform:*)` — allows any Terraform command without prompting. Remove if not using Terraform.
- `mcp__claude_ai_Linear__*` — full Linear MCP access (read + write). Remove the entire block if you don't use Linear, or trim to read-only by removing the `save_*`, `create_*`, and `update_*` entries.

### Configuration files

| File | Purpose |
|---|---|
| `.claude/settings.json` | Claude Code tool permissions — pre-approves common dev commands |
| `.claudeignore` | Prevents Claude from reading sensitive files — env files, secrets, keys, credentials, Terraform state, and large generated files |
| `.editorconfig` | Enforces consistent formatting across editors — indent style, line endings, trailing whitespace |
| `.gitignore` | Comprehensive ignore rules covering Python, Node.js, IDE files, secrets, build outputs, and OS-generated files |
| `LICENSE` | MIT licence |

## Getting started

1. Click **Use this template** on GitHub to create a new repository
2. Clone your new repo
3. Enable git hooks:
   ```bash
   git config core.hooksPath .githooks
   chmod +x .githooks/*
   ```
4. Fill in `CLAUDE.md` with your project's architecture and conventions
5. Customise `docs/process.md` — update the agent trigger rules and issue tracking section for your setup
6. Review `.claude/settings.json` — remove AWS, Terraform, or Linear permissions if not needed for this project
7. Start Claude Code — all agents and commands are available immediately

### Using agents

Claude will automatically delegate to the right agent based on what you ask. You can also be explicit:

```
# Automatic delegation
Review the code I just changed
Lint this project
Write tests for the auth module

# Explicit invocation
@code-reviewer look at the last 3 commits
@devops-reviewer check my GitHub Actions workflow
@codebase-review give me an overview of this repo
@phase-acceptance validate phase 3
```

### Using slash commands

```
/create_worktree feat/new-auth
/merge_worktree feat/new-auth
```

### Configuring the CI workflow

The CI workflow at `.github/workflows/ci.yml` ships with language-specific blocks commented out. Uncomment the section for your language and remove the rest:

- **Python** — uses Ruff for linting and pytest for tests
- **Node.js** — uses npm with caching
- **Go** — uses golangci-lint

The commit message validation step runs by default regardless of language.

## Customisation

### Adding project-specific agents

Drop additional `.md` files into `.claude/agents/` with YAML frontmatter:

```markdown
---
name: my-agent
description: When Claude should use this agent
tools: Read, Grep, Glob
model: sonnet
---

Your system prompt here.
```

### Modifying existing agents

Edit any agent file directly. Changes take effect on the next Claude Code session (or run `/agents` to reload immediately).

### Agent tool permissions

Agents are configured with appropriate tool access:

- **Read-only** (`Read, Grep, Glob, Bash`): code-reviewer, code-optimiser, codebase-review, phase-acceptance
- **Read + write** (`Read, Write, Edit, Grep, Glob, Bash`): test-generator, doc-generator, devops-reviewer, refactorer
- **Read + edit** (`Read, Edit, Grep, Glob, Bash`): linter

### Git hook configuration

- **Max file size**: `git config hooks.maxfilesize <bytes>` (default: 5MB)
- **Skip hooks**: append `--no-verify` to `git commit` or `git push`

### Recommended project structure

Once you start building, consider adding:

```
docs/
├── prd/                    # Product requirements documents
├── build-guides/           # Phase-by-phase implementation guides
├── decisions/              # Architecture Decision Records (ADRs)
├── process.md              # Development process (included in template)
└── tech-debt.md            # Known gaps and drift
```

The process doc and agents reference this structure. The doc-generator and codebase-review agents maintain `tech-debt.md` and `CLAUDE.md` at phase boundaries.

## Licence

MIT
