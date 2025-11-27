![MCP vs. UTCP](https://github.com/universal-tool-calling-protocol/.github/raw/main/assets/banner.png)

# UTCP MCP Bridge (Rust)

This **Rust UTCP bridge** enables seamless integration between UTCP tools and any MCP-based ecosystem, providing standard tool invocation, search, streaming, and provider registration functionalities.

A lightweight Rust-based bridge that exposes **UTCP tools** as **MCP tools** — enabling any MCP-compatible client (Claude Desktop, Claude CLI, LLM runtimes implementing MCP) to call UTCP tools seamlessly.

## Features

This bridge lets you:

- 🔌 Load UTCP providers dynamically from JSON configuration
- 🛠 Call UTCP tools via MCP
- 🔍 Search the UTCP tool registry
- 🔄 Stream UTCP tool results over MCP
- 🤝 Register new providers dynamically at runtime (planned)

Designed with flexibility in mind, the bridge can power anything from local tool-automation setups to distributed LLM agent workflows.

---

## UTCP → MCP Tool Mapping

| MCP Tool Name             | Description |
|---------------------------|-------------|
| `utcp_call_tool`          | Call any UTCP tool with arguments |
| `utcp_search_tools`       | Fuzzy-search tools in UTCP registry |
| `utcp_call_tool_stream`   | Stream responses from UTCP tools |
| `utcp_register_provider`  | Register new UTCP provider at runtime (planned) |

---

## Installation

### From Source

```bash
git clone https://github.com/universal-tool-calling-protocol/mcp-bridge-rs-utcp.git
cd mcp-bridge-rs-utcp
cargo build --release
```

### Install Globally

To install the bridge globally so it can be used from anywhere:

```bash
# Copy to your local bin directory (recommended)
cp target/release/mcp-bridge-rs-utcp ~/.local/bin/

# OR copy to system bin (requires sudo)
sudo cp target/release/mcp-bridge-rs-utcp /usr/local/bin/
```

Ensure `~/.local/bin` or `/usr/local/bin` is in your `PATH`.

---

## Usage

### Quick Start

```bash
# Set the path to your UTCP providers file (optional)
export UTCP_PROVIDERS_FILE=/path/to/providers.json

# Run the bridge
mcp-bridge-rs-utcp
```

### With Claude Desktop

Add the following to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "utcp-bridge": {
      "command": "mcp-bridge-rs-utcp",
      "env": {
        "UTCP_PROVIDERS_FILE": "/absolute/path/to/providers.json"
      }
    }
  }
}
```

---

## Features

### CodeMode

The bridge includes **CodeMode** support, allowing you to execute inline Rhai scripts that can call UTCP tools. This enables complex logic and data processing directly within the MCP tool call.

#### Example: Run Code

```json
{
  "name": "utcp_run_code",
  "arguments": {
    "code": "let x = 10; x * 2",
    "timeout": 1000
  }
}
```

#### Example: Call Tool from Code

```json
{
  "name": "utcp_run_code",
  "arguments": {
    "code": "let weather = call_tool(\"get_weather\", #{\"city\": \"London\"}); weather"
  }
}
```

---

## Configuration

The bridge uses the `rs-utcp` configuration format. Create a `providers.json` file:

```json
{
  "manual_call_templates": [
    {
      "call_template_type": "http",
      "name": "weather_api",
      "url": "https://api.weather.example.com/tools",
      "http_method": "GET"
    },
    {
      "call_template_type": "mcp",
      "name": "file_tools",
      "command": "python3",
      "args": ["mcp_server.py"]
    }
  ],
  "load_variables_from": [
    {
      "variable_loader_type": "dotenv",
      "env_file_path": ".env"
    }
  ]
}
```

---

## Architecture

```
┌─────────────────┐
│   MCP Client    │  (Claude Desktop, etc.)
│  (JSON-RPC)     │
└────────┬────────┘
         │
         │ stdio/SSE
         ▼
┌─────────────────┐
│  MCP Bridge     │  (this project)
│  (Rust)         │
└────────┬────────┘
         │
         │ UTCP Protocol
         ▼
┌─────────────────┐
│  UTCP Client    │  (rs-utcp)
│                 │
└────────┬────────┘
         │
         │ Various Transports
         ▼
┌─────────────────┐
│  Tool Providers │
│  (HTTP, gRPC,   │
│   WebSocket,    │
│   MCP, etc.)    │
└─────────────────┘
```

---

## Tool Examples

### Call a UTCP Tool

```json
{
  "name": "utcp_call_tool",
  "arguments": {
    "tool_name": "get_weather",
    "arguments": {
      "city": "San Francisco"
    }
  }
}
```

### Search for Tools

```json
{
  "name": "utcp_search_tools",
  "arguments": {
    "query": "weather",
    "limit": 5
  }
}
```

### Stream Tool Results

```json
{
  "name": "utcp_call_tool_stream",
  "arguments": {
    "tool_name": "generate_report",
    "arguments": {
      "topic": "AI trends"
    }
  }
}
```

---

## Development

### Building

```bash
cargo build
```

### Running Tests

```bash
cargo test
```

### Running Locally

```bash
RUST_LOG=info cargo run
```

---

## Comparison with Go Implementation

This Rust implementation provides the same core functionality as the [Go UTCP MCP Bridge](https://github.com/universal-tool-calling-protocol/go-utcp-mcp-bridge), with the following differences:

- ✅ **Performance**: Rust implementation offers better memory safety and performance
- ✅ **Type Safety**: Leverages Rust's type system for more robust error handling
- ✅ **CodeMode**: Inline code execution supported via Rhai engine
- 🚧 **Chain Execution**: UTCP Chain support planned for future release

---

## Status

This bridge is currently in **beta** status. The following features are implemented:

- ✅ Tool calling
- ✅ Tool search
- ✅ Streaming support
- ✅ CodeMode support
- 🚧 Dynamic provider registration (in progress)
- 🚧 Chain execution (planned)

---

## Related Projects

- [rs-utcp](https://github.com/universal-tool-calling-protocol/rs-utcp) - Rust UTCP client library
- [go-utcp](https://github.com/universal-tool-calling-protocol/go-utcp) - Go UTCP implementation
- [go-utcp-mcp-bridge](https://github.com/universal-tool-calling-protocol/go-utcp-mcp-bridge) - Go MCP bridge

---

## License

MIT OR Apache-2.0

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
