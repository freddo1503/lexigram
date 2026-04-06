# List available recipes
default:
    @just --list

# Install project dependencies
install:
    uv sync

# Install all dependencies (dev + docs)
install-all:
    uv sync --all-extras
    npm install

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

# Build docs
docs-build:
    npx antora --fetch antora-playbook.yml

# Serve docs locally
docs-serve:
    npx antora --fetch antora-playbook.yml && python3 -m http.server -d build/site 8010

# Deploy docs (CI handles GitHub Pages deployment)
docs-deploy:
    npx antora --fetch antora-playbook.yml

# Start local Langfuse infrastructure
langfuse-up:
    docker compose up -d

# Stop local Langfuse infrastructure
langfuse-down:
    docker compose down

# Run evaluation pipeline (hits real APIs, no mocks)
eval:
    uv run --group eval pytest tests/eval/ -v --timeout=600 -s

# Install git hooks via lefthook
setup-hooks:
    lefthook install
