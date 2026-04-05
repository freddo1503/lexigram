# Conventions

## Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- Include a `References:` section with official documentation URLs justifying implementation choices

## Secrets

- Never commit `.env`, credentials, API keys, or tokens
- Never run commands that print secrets to stdout
- Secrets are managed via AWS Secrets Manager (see `app/config.py`)

## Language

- Code and documentation in English
- Agent prompts and legal content in French (`app/config/agents.yml`)

## Justfile

- All codebase commands must be defined as justfile recipes
- Dev, CI, and AI agents all use `just <recipe>`
- No inline scripts in CI pipelines

## Dependencies

- Use latest/unpinned versions — do not pin to specific version tags unless explicitly requested
