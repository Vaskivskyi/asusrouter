# AsusRouter MCP Server

A Model Context Protocol (MCP) server for [AsusRouter](https://github.com/Vaskivskyi/asusrouter) that enables AI assistants like Claude to interact with ASUS routers.

## Features

- **Router Connection**: Connect to ASUS routers with authentication
- **Device Management**: List connected devices and manage their network access
- **Parental Controls**: Block/allow internet access for specific devices
- **Network Monitoring**: Get device usage statistics and network information
- **User Group Management**: Manage devices by parental control groups

## Prerequisites

- Python 3.11+
- An ASUS router running AsusWRT or AsusWRT-Merlin firmware
- Router credentials (hostname, username, password)

## Installation

### From Source

1. Clone the AsusRouter repository:
   ```bash
   git clone https://github.com/Vaskivskyi/asusrouter.git
   cd asusrouter
   ```

2. Install dependencies using uv:
   ```bash
   uv sync --all-groups
   ```

3. Set up environment variables (see [Configuration](#configuration))

## Configuration

### Environment Variables

Create a `.env` file in the project root or set the following environment variables:

```bash
# Required: Router connection details
ASUS_ROUTER_HOST=192.168.1.1          # Your router's IP address
ASUS_ROUTER_USERNAME=admin             # Router admin username
ASUS_ROUTER_PASSWORD=your_password     # Router admin password

# Optional: Connection settings
ASUS_ROUTER_USE_SSL=false              # Use HTTPS (true/false)
```

### Router Setup

1. **Enable parental controls** on your ASUS router (required for blocking/allowing devices)
2. **Ensure admin access** - the provided credentials must have admin privileges
3. **Network access** - ensure the machine running the MCP server can reach the router

## Usage

### Starting the MCP Server

```bash
# From the project root
uv run python -m asusrouter_mcp.server
```

The server will start and listen for MCP client connections.

### Connecting with Claude Desktop

Add the following configuration to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "asusrouter": {
      "command": "uv",
      "args": ["run", "python", "-m", "asusrouter_mcp.server"],
      "cwd": "/path/to/asusrouter",
      "env": {
        "ASUS_ROUTER_HOST": "192.168.1.1",
        "ASUS_ROUTER_USERNAME": "admin",
        "ASUS_ROUTER_PASSWORD": "your_password"
      }
    }
  }
}
```

## Available Tools

### connect_router
Connect to the ASUS router using provided credentials or environment variables.

**Parameters:**
- `host` (optional): Router IP address
- `username` (optional): Admin username
- `password` (optional): Admin password
- `use_ssl` (optional): Use HTTPS connection

**Example:**
```
Connect to the router
```

### get_router_data
Retrieve various types of data from the router.

**Parameters:**
- `data_types`: Array of data types to retrieve
  - `"clients"` - Connected devices
  - `"status"` - Router status
  - `"sysinfo"` - System information
  - `"network"` - Network statistics
  - `"wan"` - WAN connection info

**Example:**
```
Get the list of connected devices
```

### block_traffic_to_device
Block internet access for a specific device using parental controls.

**Parameters (one required):**
- `device_mac`: Device MAC address
- `device_name`: Device name
- `device_ip`: Device IP address

**Example:**
```
Block internet access for device "Kitchen Speaker"
```

### allow_traffic_to_device
Restore internet access for a previously blocked device.

**Parameters (one required):**
- `device_mac`: Device MAC address
- `device_name`: Device name
- `device_ip`: Device IP address

**Example:**
```
Allow internet access for device with MAC AA:BB:CC:DD:EE:FF
```

### get_devices_for_user
Get devices associated with a specific parental control group.

**Parameters:**
- `user_group`: Name of the user/parental control group

**Example:**
```
Get devices for the "kids" user group
```

### get_device_usage
Get usage statistics for a specific device (24-hour period).

**Parameters (one required):**
- `device_mac`: Device MAC address
- `device_name`: Device name

**Example:**
```
Get usage statistics for "iPhone"
```

## Available Resources

### router_status
Current router status including connection state and basic info.

### connected_devices
List of all currently connected devices with their details.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest asusrouter_mcp/tests/

# Run with coverage
uv run pytest --cov=asusrouter_mcp asusrouter_mcp/tests/

# Run specific test file
uv run pytest asusrouter_mcp/tests/test_server.py
```

### Code Quality

This project follows the same code quality standards as the main AsusRouter project:

```bash
# Linting and formatting with ruff
uv run ruff check --fix asusrouter_mcp/
uv run ruff format asusrouter_mcp/

# Type checking with mypy
uv run mypy asusrouter_mcp/

# Pre-commit hooks (automatically run on commit)
uv run pre-commit run --all-files
```

### Project Structure

```
asusrouter_mcp/
├── __init__.py           # Package initialization
├── server.py             # Main MCP server implementation
├── tests/                # Test suite
│   ├── __init__.py
│   ├── conftest.py       # Test fixtures
│   └── test_server.py    # Server tests
└── README.md             # This file
```

## Troubleshooting

### Connection Issues

1. **"Router not connected"**: Ensure environment variables are set correctly and router is accessible
2. **Authentication failed**: Verify username/password and admin privileges
3. **Connection timeout**: Check network connectivity and router IP address

### Parental Control Issues

1. **"Failed to block device"**: Ensure parental controls are enabled on the router
2. **Device not found**: Check device name/MAC address spelling and ensure device is connected
3. **Changes not taking effect**: Some routers may take time to apply parental control changes

### Environment Setup

1. **Missing dependencies**: Run `uv sync --all-groups` to install all required packages
2. **Python version**: Ensure you're using Python 3.11 or higher
3. **uv not found**: Install uv following the [official instructions](https://github.com/astral-sh/uv)

## Security Considerations

- Store router credentials securely using environment variables
- Use HTTPS connection when possible (`ASUS_ROUTER_USE_SSL=true`)
- Limit access to the machine running the MCP server
- Consider using a dedicated router admin account with limited privileges

## Contributing

See the main [AsusRouter CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

This project follows the same license as the main AsusRouter project.

## Related Projects

- [AsusRouter](https://github.com/Vaskivskyi/asusrouter) - Python library for ASUS router API
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification and tools