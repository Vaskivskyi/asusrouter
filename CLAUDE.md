# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AsusRouter is a Python library that provides an API wrapper for communication with ASUSWRT-powered routers using HTTP(S) protocols. It supports both stock AsusWRT firmware and AsusWRT-Merlin firmware across a wide range of Asus router models.

## Development Environment

This project uses `uv` as the Python package manager and virtual environment tool. The project requires Python 3.11+ and follows strict type checking with mypy.

### Key Dependencies
- **Runtime**: `aiohttp`, `urllib3`, `xmltodict`
- **Development**: `mypy`, `ruff`, `pre-commit`
- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`

## Common Commands

### Environment Setup
```bash
# Create and activate virtual environment
uv venv
# Install all dependencies including dev and test groups
uv sync --all-groups
# Install pre-commit hooks
uv run pre-commit install
```

### Development
```bash
# Install only runtime dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Install test dependencies
uv sync --group test

# Run pre-commit checks on all files
uv run pre-commit run --all-files

# Build package
uv build
```

### Testing
```bash
# Run unit tests for Python 3.11 (excludes device tests)
uv run --python 3.11 pytest --cov=asusrouter --cov-report=term-missing -vv -k 'not test_devices'

# Run unit tests for Python 3.12
uv run --python 3.12 pytest --cov=asusrouter --cov-report=term-missing -vv -k 'not test_devices'

# Run unit tests for Python 3.13
uv run --python 3.13 pytest --cov=asusrouter --cov-report=term-missing -vv -k 'not test_devices'

# Run device-specific tests (tests on actual device data)
uv run --python 3.13 pytest tests/test_devices.py --cov=asusrouter --cov-report=term-missing -vv --log-cli-level=INFO
```

### Linting and Type Checking
```bash
# Run ruff linting and formatting (automatically done by pre-commit)
uv run ruff check --fix
uv run ruff format

# Run mypy type checking
uv run mypy asusrouter
```

## Code Architecture

### Core Components

- **`AsusRouter`** (`asusrouter.py`): Main class for router communication with async/await pattern
- **`Connection`** (`connection.py`): Handles HTTP requests and authentication with the router
- **`AsusData`** (`modules/data.py`): Enum defining all available data types that can be retrieved from routers
- **Configuration**:
  - `config.py`: Router configuration management
  - `connection_config.py`: Connection-specific configuration
- **Registry** (`registry.py`): Manages callable registrations for data processing

### Module Organization

- **`modules/`**: Core functionality modules
  - `data.py`: Data type definitions and state management
  - `client.py`, `system.py`, `traffic.py`, etc.: Specific router feature modules
  - `endpoint/`: API endpoint definitions
  - `data_finder.py`, `data_transform.py`: Data processing utilities

- **`tools/`**: Utility functions
  - `converters.py`: Data type conversion utilities
  - `cleaners.py`: Data cleaning functions
  - `security.py`: Security-related utilities
  - `dump.py`: Debug data dumping functionality

### Key Patterns

1. **Async/Await**: All router communication is asynchronous using aiohttp
2. **Data Types**: Strong typing with Pydantic models and type hints
3. **Enum-based Data Access**: `AsusData` enum provides type-safe data retrieval
4. **Modular Design**: Features are separated into individual modules
5. **Error Handling**: Custom exception hierarchy for different error types

### Data Flow

1. `AsusRouter` class manages the connection lifecycle
2. `Connection` handles HTTP requests to router endpoints
3. Data is retrieved via `AsusData` enum values
4. Raw responses are processed through data transform modules
5. Clean, typed data is returned to the caller

## Testing Strategy

- **Unit Tests**: Test individual components and functions
- **Device Tests**: Test against real router response data from various models
- **Coverage**: Maintains test coverage reporting
- **Multiple Python Versions**: Tests run against Python 3.11, 3.12, and 3.13

## Code Quality Standards

- **Ruff**: Used for both linting and code formatting (line length: 79 characters)
- **MyPy**: Strict type checking enabled
- **Pre-commit**: All commits must pass linting and formatting checks
- **Docstrings**: PEP 257 convention required for all public APIs

## VS Code Integration

The project includes pre-configured VS Code settings:
- Recommended extensions for Python development with Ruff
- Auto-formatting on save
- Integrated task runners for common operations
- MyPy integration for type checking