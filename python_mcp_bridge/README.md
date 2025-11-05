# UTCP-MCP Bridge (Python)

Python implementation of the UTCP-MCP Bridge for users who prefer Python or need specific Python environment features.

## 🚀 Quick Start

### 1. Install Dependencies

Ensure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed on your system:

```bash
# Using pipx (recommended)
pipx install uv

# Using pip
pip install uv

# Or using curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Download the Script

Download the [`utcp-client-mcp.py`](utcp-client-mcp.py) file to your desired location.

### 3. Configure Your MCP Client

Add this configuration to your MCP client (Claude Desktop, etc.):

```json
{
  "mcpServers": {
    "utcp-python": {
      "command": "uv",
      "args": [
        "run",
        "/path/to/utcp-client-mcp.py"
      ],
      "env": {
        "UTCP_CONFIG_FILE": "/path/to/your/.utcp_config.json"
      }
    }
  }
}
```

## 🔧 Configuration

Create a `.utcp_config.json` file in the same directory as the Python script:

```json
{
    "load_variables_from": [
      {
        "variable_loader_type": "dotenv",
        "env_file_path": ".env"
      }
    ],
    "manual_call_templates": [
      {
          "name": "openlibrary",
          "call_template_type": "http",
          "http_method": "GET",
          "url": "https://openlibrary.org/static/openapi.json",
          "content_type": "application/json"
      }
    ],
    "post_processing": [
      {
          "tool_post_processor_type": "filter_dict",
          "only_include_keys": ["name", "description"],
          "only_include_tools": ["openlibrary.*"]
      }
    ],
    "tool_repository": {
      "tool_repository_type": "in_memory"
    },
    "tool_search_strategy": {
      "tool_search_strategy_type": "tag_and_description_word_match"
    }
}
```

## 🛠️ Available MCP Tools

The Python bridge exposes the same MCP tools as the Node.js version:

- **`register_manual`** - Register new UTCP manuals/APIs
- **`deregister_manual`** - Remove registered manuals
- **`call_tool`** - Execute any registered UTCP tool
- **`search_tools`** - Find tools by description
- **`list_tools`** - List all registered tool names
- **`get_required_keys_for_tool`** - Get required environment variables
- **`tool_info`** - Get complete tool information and schema

## 📋 Dependencies

The Python script uses these dependencies (automatically handled by `uv`):

- `fastmcp` - Fast MCP server implementation
- `utcp` - Core UTCP client
- `utcp-mcp` - MCP integration
- `utcp-text` - Text processing tools
- `utcp-cli` - Command-line tools
- `utcp-http` - HTTP tools

## 🌟 Features

- ✅ **Zero global installation** - Uses `uv run` for dependency isolation
- ✅ **Python ecosystem** - Perfect for Python-heavy workflows
- ✅ **Same functionality** - All features from the Node.js version
- ✅ **Environment isolation** - Each project can have its own config
- ✅ **Fast startup** - Optimized for quick tool loading

## 🔄 Alternative: Using pip/pipx

If you prefer not to use `uv`, you can also install dependencies globally:

```bash
pip install fastmcp utcp utcp-mcp utcp-text utcp-cli utcp-http
```

Then use this MCP configuration:

```json
{
  "mcpServers": {
    "utcp-python": {
      "command": "python",
      "args": ["/path/to/utcp-client-mcp.py"]
    }
  }
}
```

## 🆚 Why Choose Python Version?

- **Python expertise** - If your team is more comfortable with Python
- **Custom Python tools** - Easy to extend with Python-specific functionality
- **Environment control** - More granular control over Python dependencies
- **Debugging** - Easier to debug and modify if you know Python

For most users, we recommend the **Node.js version** via `npx @utcp/mcp-bridge` as it requires zero installation and works out of the box.
