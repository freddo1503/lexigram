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
