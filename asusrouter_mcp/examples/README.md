# AsusRouter MCP Examples

This directory contains example scripts and tools for testing and demonstrating the AsusRouter MCP server.

## Files

### test_logger.py
A comprehensive logging utility used by the test scripts. Provides structured logging with timestamps and test result tracking.

### test_mcp_with_logging.py
A comprehensive test script that demonstrates all MCP server functionality with detailed logging. This script:
- Tests all available MCP tools
- Logs results to JSON files
- Provides detailed error reporting
- Can be used as a reference for implementing MCP clients

**Usage:**
```bash
# From the project root
uv run python asusrouter_mcp/examples/test_mcp_with_logging.py
```

### interactive_test.py
An interactive script for manually testing MCP server functions. Useful for:
- Debugging connection issues
- Testing specific device operations
- Manual validation of router responses

**Usage:**
```bash
# From the project root
uv run python asusrouter_mcp/examples/interactive_test.py
```

## Running Examples

Before running any examples, ensure you have:

1. Set up your environment variables:
   ```bash
   cp asusrouter_mcp/.env.example .env
   # Edit .env with your router details
   ```

2. Installed dependencies:
   ```bash
   uv sync --all-groups
   ```

3. Ensured your router is accessible and parental controls are enabled

## Log Files

Test scripts will create log files in a `test_logs/` directory. These logs contain:
- Detailed test execution information
- API call results
- Error messages and stack traces
- Performance metrics

Use the log viewer to examine results:
```bash
uv run python asusrouter_mcp/examples/test_logger.py view
```