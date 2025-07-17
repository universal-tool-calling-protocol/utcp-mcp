# UTCP-MCP Bridge

## Overview

**The last MCP server you'll ever need.**

UTCP-MCP Bridge is a universal, all-in-one MCP server that brings the full power of the Universal Tool Calling Protocol (UTCP) to the MCP ecosystem. With this project, you can:

- **Use UTCP as a proxy:** Instantly expose all tools registered via UTCP as MCP-compatible tools, making them available to any MCP client.
- **Use the UTCP client directly:** Register and deregister providers, search and call tools — unlocking the main functions of the UTCP client from a single place.
- **Web interface:** Easily manage your tools and providers through a user-friendly web UI. Register and deregister providers, enable and disable tools, and much more — all with just a few clicks. More features are coming soon!

With UTCP-MCP Bridge, you only need to install one MCP server to access, manage, and extend your tool ecosystem—no matter how you want to use it.

---

## Getting Started

You can run the UTCP-MCP Bridge in two ways: using Docker or a local bash script.

### 1. Run with Docker

Ensure you have Docker and Docker Compose installed.

```bash
docker-compose up --build
```

### 2. Run with Bash Script (Locally)

Ensure you have Python 3 installed.

```bash
./run.sh
```

This will:
- Set up a Python virtual environment with all dependencies or build the Docker image
- Start the MCP servers and WEB server
- Expose the following ports:
  - `8776` (UTCP Client MCP)
  - `8777` (UTCP Proxy MCP)
  - `8778` (FastAPI web server)

You can access the web interface at: [http://localhost:8778/](http://localhost:8778/)

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
