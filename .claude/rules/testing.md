# Testing

## Framework

- **pytest** with `pytest-cov` for coverage and `pytest-mock` for mocking
- Timeout: 300s per test

## Structure

- `tests/unit/` — unit tests
- `tests/integration/` — integration tests (may require AWS credentials and `.env`)

## Commands

- `just test` — run all tests (unit + integration)
- `just test-unit` — unit tests only
- `just test-integration` — integration tests only
- `just coverage` — full coverage report (HTML in `htmlcov/`)

## Configuration

- pytest config in `pyproject.toml` under `[tool.pytest.ini_options]`
- Coverage config in `.coveragerc`
