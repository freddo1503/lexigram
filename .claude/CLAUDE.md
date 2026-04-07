# Lexigram

AI-powered multi-agent system that summarizes French legislation and publishes daily Instagram posts.

## Tech Stack

- **Python 3.12** with **uv** package manager
- **CrewAI** for multi-agent orchestration (Mistral AI for all agents — text + images)
- **AWS Lambda** (Docker-based, eu-west-3), **DynamoDB**, **EventBridge** (weekdays 11:30 UTC)
- **AWS CDK** for infrastructure (`infra/`)
- **Légifrance API** via `pylegifrance` for official French law data
- **Instagram Graph API** for publishing

## Commands

All commands go through `just`. Run `just --list` to see available recipes.

| Recipe | Purpose |
|--------|---------|
| `just install` | Install dependencies |
| `just install-all` | Install dev + docs dependencies |
| `just test` | Run all tests (unit + integration) |
| `just test-unit` | Run unit tests only |
| `just test-integration` | Run integration tests only |
| `just coverage` | Run tests with coverage report |
| `just lint` | Lint with ruff |
| `just lint-fix` | Lint and auto-fix |
| `just format` | Format with ruff |
| `just format-check` | Check formatting |
| `just type-check` | Type check with ty |
| `just deploy` | Deploy CDK stack |
| `just docs-build` | Build Antora docs |
| `just docs-serve` | Build and serve docs locally (port 8000) |
| `just docs-deploy` | Build docs (CI handles GitHub Pages deployment) |
| `just setup-hooks` | Install lefthook git hooks |

## Configuration

- **Settings**: Pydantic-based in `app/config.py` (`LexigramSettings`)
- **Secrets**: AWS Secrets Manager (secret name: `my-env-secrets`), `.env` for local dev
- **Agent prompts**: `app/config/agents.yml` (written in French)
- **Infrastructure**: `infra/lexigram_stack.py` (Lambda, DynamoDB, EventBridge)

## Key Paths

| Path | Purpose |
|------|---------|
| `app/agents/` | CrewAI agent definitions |
| `app/services/` | Business logic (law sync, processing, publishing) |
| `app/config/agents.yml` | Agent/task YAML configuration |
| `infra/` | AWS CDK infrastructure |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Integration tests |
