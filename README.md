# UTCP-MCP Bridge

## Overview

**The last MCP server you'll ever need.**

UTCP-MCP Bridge is a universal, all-in-one MCP server that brings the full power of the Universal Tool Calling Protocol (UTCP) to the MCP ecosystem. With this project, you can:

- **Use the UTCP client directly:** Register and deregister UTCP manuals, search and call tools — unlocking the main functions of the UTCP client from a single place.
- **Use UTCP as a proxy:** Instantly expose all tools registered via UTCP as MCP-compatible tools, making them available to any MCP client. Available in the web interface
- **Web interface:** Easily manage your tools and manuals through a user-friendly web UI. Register and deregister manuals, enable and disable tools, and much more — all with just a few clicks. More features are coming soon! The web-ui is a bit more complex, check out its readme and setup instructions here: [web_ui_utcp_mcp_bridge/README.md](web_ui_utcp_mcp_bridge/README.md)

With UTCP-MCP Bridge, you only need to install one MCP server to access, manage, and extend your tool ecosystem—no matter how you want to use it.

<img width="2263" height="976" alt="3mcp" src="https://github.com/user-attachments/assets/a6759512-1c0d-4265-9518-64916fbe1428" />

---

## Quick Setup (Standalone)

For a quick standalone setup using just the UTCP client MCP:

### 1. Install uv
Ensure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed on your system. You can install it via:

```bash
# Using pipx (recommended)
pipx install uv

# Using pip
pip install uv

# Or follow the official installation guide above
```

### 2. Download the client script
Download the `simple-utcp-client-mcp.py` file to your desired location.

### 3. Configure your MCP client
Add the following configuration to your MCP client:

```json
{
  "mcpServers": {
    "simple-utcp-client-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--script",
        "path\\to\\simple-utcp-client-mcp.py"
      ]
    }
  }
}
```

### 4. Optional configuration
Create a `.utcp_config.json` file in the same directory as the python script to:
- Set environment variables (optional)
- Register manuals on startup (optional)
- Load variables from .env files (optional)
- Add custom post processing steps (optional)
- Use custom tool repositories (optional)
- Use custom tool search strategies (optional)

Example `.utcp_config.json`:
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
          "only_include_keys": ["name", "key"],
          "only_include_tools": ["openlibrary.read_search_authors_json_search_authors_json_get"]
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