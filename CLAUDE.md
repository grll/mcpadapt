# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands

- `make sync`: Set up dev environment with dependencies
- `make format`: Auto-format code with Ruff
- `make lint`: Run Ruff linter
- `make mypy`: Type-check code with mypy
- `make tests`: Run all tests with pytest
- `pytest tests/test_file.py`: Run a specific test file
- `pytest tests/test_file.py::test_function`: Run a specific test function
- `make coverage`: Run tests with coverage (95% required)

## Code Style Guidelines

- **Imports**: Group by stdlib → third-party → local/project; alphabetize within groups
- **Types**: Full type annotations required; use Python 3.10+ typing features
- **Naming**: PascalCase for classes, snake_case for functions/variables, UPPERCASE for constants
- **Docstrings**: Google-style with Args and Returns sections
- **Formatting**: Ruff for linting and formatting (pre-commit hooks configured)
- **Error Handling**: Use explicit error types with descriptive messages
- **Tests**: Must maintain 95% coverage with pytest

## Other

- **Github**: Use `gh` cli for all actions requiring interaction with github
- The name of the github repo is "grll/mcpadapt"
