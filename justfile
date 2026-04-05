# List available recipes
default:
    @just --list

# Install project dependencies
install:
    uv sync

# Install all dependencies (dev + docs)
install-all:
    uv sync --all-extras

# Run all tests
test: test-unit test-integration

# Run unit tests
test-unit:
    uv run pytest tests/unit/

# Run integration tests
test-integration:
    uv run pytest tests/integration/

# Run tests with coverage report
coverage:
    uv run ./scripts/generate_coverage_report.py

# Lint code with ruff
lint:
    uv run ruff check .

# Lint and auto-fix
lint-fix:
    uv run ruff check . --fix

# Format code with ruff
format:
    uv run ruff format .

# Check formatting without modifying
format-check:
    uv run ruff format . --check

# Type check with ty
type-check:
    uv run ty check

# Deploy infrastructure via CDK
deploy:
    uv run cdk deploy --all --require-approval=never

# Serve docs locally
docs-serve:
    uv run mkdocs serve

# Deploy docs to GitHub Pages
docs-deploy:
    uv run mkdocs gh-deploy --force

# Install git hooks via lefthook
setup-hooks:
    lefthook install
