# Code Style

## Principles

- **KISS**: Keep It Simple — simplicity over complexity
- **DRY**: Don't Repeat Yourself — code reuse first
- **YAGNI**: You Aren't Gonna Need It — only build what is needed now
- **Maintainability**: write code that is easy to read, understand, and modify

## Linting & Formatting

- **Ruff** for linting and formatting (line-length 88, double quotes, space indent)
- **ty** for type checking (Python 3.12 target)
- No Black, no mypy — ruff and ty cover everything
- Run `just lint-fix && just format` before committing

## Git Hooks

- **Lefthook** manages pre-commit hooks (replaces pre-commit)
- Hooks run `just lint-fix` and `just format` on staged `.py` files
- Install hooks with `just setup-hooks`
