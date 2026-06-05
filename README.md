# UTCP-MCP Bridge

**The last MCP server you'll ever need.**

A universal, all-in-one MCP server that brings the full power of the Universal Tool Calling Protocol (UTCP) to the MCP ecosystem.

## 🚀 Quick Start

Add this configuration to your MCP client (Claude Desktop, etc.):

```json
{
  "mcpServers": {
    "utcp": {
      "command": "npx",
      "args": ["@utcp/mcp-bridge"],
      "env": {
        "UTCP_CONFIG_FILE": "/path/to/your/.utcp_config.json"
      }
    }
  }
}
```

**That's it!** No installation required. The bridge will automatically:
- Download and run the latest version via npx
- Load your UTCP configuration from the specified path
- Register all your UTCP manuals as MCP tools
- Provide a unified interface to manage your tool ecosystem

## 🔧 Configuration

Create a `.utcp_config.json` file to configure your tools and services:

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

### Claude Code (CLI)

For [Claude Code](https://claude.com/claude-code) (the CLI / IDE extension), register the bridge as a user-scoped MCP server:

```bash
claude mcp add-json --scope user utcp '{"type":"stdio","command":"npx","args":["@utcp/mcp-bridge"],"env":{"UTCP_CONFIG_FILE":"/absolute/path/to/.utcp_config.json"}}'
```

Then restart Claude Code. Verify with `claude mcp list`. Remove with `claude mcp remove utcp --scope user`.

## 🧪 Local development against the bridge

If you're hacking on `@utcp/sdk` or any other [typescript-utcp](https://github.com/universal-tool-calling-protocol/typescript-utcp) package and want to exercise it through Claude Code, use the dev scripts:

```bash
cd utcp-mcp
npm install
npm run dev:register     # builds typescript-utcp packages, overlays each into the bridge's node_modules, builds the bridge, and registers it as 'utcp-dev' in Claude Code
# restart Claude Code

# After every edit:
npm run dev:register     # rebuilds, re-registers; restart Claude Code

# When done:
npm run dev:unregister   # removes the MCP entry and restores registry node_modules
```

Both scripts are idempotent and never mutate `package.json`. The overlay strategy avoids `npm link`, which under modern npm aliases `unlink` to `uninstall --save` and would silently strip the dependency.

The script expects the typescript-utcp checkout to live next to this repo (`../typescript-utcp`). Override with flags if not:

- `--lib-dir <path>` — point at a different typescript-utcp checkout, or pass `none` to skip the overlay step entirely (useful when only editing the bridge)
- `--name <mcp-name>` (default `utcp-dev`) — useful if you want the dev bridge alongside a published one
- `--config <path>` (default `./.utcp_config.json`) — point at a different UTCP config

## 🛠️ Available MCP Tools

The bridge exposes these MCP tools for managing your UTCP ecosystem:

- **`register_manual`** - Register new UTCP manuals/APIs
- **`deregister_manual`** - Remove registered manuals
- **`call_tool`** - Execute any registered UTCP tool
- **`search_tools`** - Find tools by description
- **`list_tools`** - List all registered tool names
- **`get_required_keys_for_tool`** - Get required environment variables
- **`tool_info`** - Get complete tool information and schema

## 📁 What is UTCP?

The Universal Tool Calling Protocol (UTCP) allows you to:
- **Connect to any API** via HTTP, OpenAPI specs, or custom formats
- **Use command-line tools** with automatic argument parsing
- **Process text and files** with built-in utilities
- **Chain and combine** multiple tools seamlessly

With this MCP bridge, all your UTCP tools become available in Claude Desktop and other MCP clients.

## 🌟 Features

- ✅ **Zero installation** - Works via npx
- ✅ **Universal compatibility** - Works with any MCP client
- ✅ **Dynamic configuration** - Update tools without restarting
- ✅ **Environment isolation** - Each project can have its own config
- ✅ **Comprehensive tool management** - Register, search, call, and inspect tools
- ✅ **Web interface available** - See [web_ui_utcp_mcp_bridge/](web_ui_utcp_mcp_bridge/)

## 🐍 Python Version

For Python users, see the standalone Python implementation in [`python_mcp_bridge/`](python_mcp_bridge/)

## ❓ FAQ

### What is UTCP-MCP Bridge?
The **last MCP server you'll ever need** — a universal, all-in-one MCP server that brings the full power of UTCP (Universal Tool Calling Protocol) to the MCP ecosystem. Works with Claude Desktop and any MCP client.

### Available MCP Tools
| Tool | Description |
|------|-------------|
| register_manual | Register new UTCP manuals/APIs |
| deregister_manual | Remove registered manuals |
| call_tool | Execute any registered UTCP tool |
| search_tools | Find tools by description |
| list_tools | List all registered tool names |
| get_required_keys_for_tool | Get required environment variables |
| tool_info | Get complete tool info and schema |

### What is UTCP?
Universal Tool Calling Protocol allows you to:
- Connect to any API via HTTP, OpenAPI specs, or custom formats
- Use command-line tools with automatic argument parsing
- Process text and files with built-in utilities
- Chain and combine multiple tools seamlessly

### Quick Start
Add to MCP client config:
```json
{
  "mcpServers": {
    "utcp": {
      "command": "npx",
      "args": ["@utcp/mcp-bridge"],
      "env": {"UTCP_CONFIG_FILE": "/path/to/.utcp_config.json"}
    }
  }
}
```

### Key Features
- ✅ Zero installation — works via npx
- ✅ Universal compatibility — any MCP client
- ✅ Dynamic configuration
- ✅ Environment isolation
- ✅ Comprehensive tool management
- ✅ Web interface available

### Is UTCP-MCP Free?
Yes, open-source. See repository for license details.

### Help Resources
| Channel | Link |
|---------|------|
| GitHub | https://github.com/universal-tool-calling-protocol/utcp-mcp |
| Web UI | web_ui_utcp_mcp_bridge/ |

---

## 🌐 Web Interface

For advanced management with a web UI, check out [`web_ui_utcp_mcp_bridge/`](web_ui_utcp_mcp_bridge/)

---

<img width="2263" height="976" alt="UTCP MCP Bridge Interface" src="https://github.com/user-attachments/assets/a6759512-1c0d-4265-9518-64916fbe1428" />