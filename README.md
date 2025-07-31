# UTCP-MCP Bridge

## Overview

**The last MCP server you'll ever need.**

UTCP-MCP Bridge is a universal, all-in-one MCP server that brings the full power of the Universal Tool Calling Protocol (UTCP) to the MCP ecosystem. With this project, you can:

- **Use UTCP as a proxy:** Instantly expose all tools registered via UTCP as MCP-compatible tools, making them available to any MCP client.
- **Use the UTCP client directly:** Register and deregister providers, search and call tools — unlocking the main functions of the UTCP client from a single place.
- **Web interface:** Easily manage your tools and providers through a user-friendly web UI. Register and deregister providers, enable and disable tools, and much more — all with just a few clicks. More features are coming soon!

With UTCP-MCP Bridge, you only need to install one MCP server to access, manage, and extend your tool ecosystem—no matter how you want to use it.

<img width="2263" height="976" alt="3mcp" src="https://github.com/user-attachments/assets/a6759512-1c0d-4265-9518-64916fbe1428" />

---

## Getting Started

You can run the UTCP-MCP Bridge in two ways: using Docker or a local bash script.

### 1.1 Run with Docker

Ensure you have Docker and Docker Compose installed.

```bash
docker-compose up --build
```

### 1.2 Run with Bash Script

Ensure you have Python 3 installed.

```bash
./run.sh
```

### 1.3 Run with PowerShell Script

Ensure you have Python 3 installed.

```bash
./run.ps1
```

This will:
- Set up a Python virtual environment with all dependencies or build the Docker image
- Start the MCP servers and WEB server
- Expose the following ports:
  - `8776` (UTCP Client MCP)
  - `8777` (UTCP Proxy MCP)
  - `8778` (FastAPI web server)

### 2 Connect with your MCP Client of choice

To connect your MCP client to the UTCP-MCP Bridge, add the following entries to your client's `mcp.json` (or equivalent configuration file):

#### Cursor example:
```json
{
  "mcpServers": {
    // any other mcp servers
    "utcp-proxy-mcp-local": {
      "url": "http://localhost:8777/utcp-proxy"
    },
    "utcp-client-mcp-local": {
      "url": "http://localhost:8776/utcp-client"
    }
  }
}
```
#### VS Code example:
```json
{
	"servers": {
    // any other mcp servers
		"utcp-proxy-mcp-local": {
			"url": "http://localhost:8777/utcp-proxy",
			"type": "http"
		},
		"utcp-client-mcp-local": {
			"url": "http://localhost:8776/utcp-client",
			"type": "http"
		}
	},
	"inputs": []
}
```

- `utcp-proxy-mcp-local` connects to the UTCP Proxy MCP server (port 8777)
- `utcp-client-mcp-local` connects to the UTCP Client MCP server (port 8776)

Adjust the URLs if you are running the server on a different host or port.

### 3 UI Interface

Web Interface to view and manage providers and tools is accessible in any browser at [http://localhost:8778/](http://localhost:8778/)

<img width="1512" height="982" alt="Screenshot 2025-07-30 at 17 53 42" src="https://github.com/user-attachments/assets/2164587b-72ec-426f-98be-3a75df761dbb" />


---

## Configuration

- Provider and tool definitions are loaded from the `data/` directory (e.g., `data/providers.json`).
- Environment variables can be set in Docker Compose or your shell to customize ports and paths.

---

## API Endpoints

- `/` – Web UI
- `/health` – Health check and status
- `/tools` – List available tools
- `/providers` – List available providers

---

## Dependencies

- `utcp`
- `fastmcp`
- `fastapi`
- `python-dotenv`

All dependencies are installed automatically by the Docker image or the bash script.
