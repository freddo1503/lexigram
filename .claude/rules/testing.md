# Testing

## Framework

- **pytest** with `pytest-cov` for coverage and `pytest-mock` for mocking
- Timeout: 300s per test

## Structure

- `tests/unit/` — unit tests
- `tests/integration/` — integration tests (may require AWS credentials and `.env`)
