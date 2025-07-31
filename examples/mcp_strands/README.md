# MCP Strands Agent Example

## Overview

This example demonstrates how to build an AI agent using the **Strands SDK** that connects to **UTCP-MCP Bridge** servers to access and utilize tools through the Model Context Protocol (MCP). The agent provides a conversational interface where users can interact with various tools exposed by the UTCP ecosystem.

## What This Example Does

The MCP Strands Agent (`mcp_strands_agent.py`) creates an intelligent assistant that:

- **Connects to UTCP-MCP Bridge servers** to discover available tools
- **Uses Strands SDK** to create a conversational AI agent powered by Amazon Bedrock's Claude 3 Sonnet
- **Maintains conversation context** across multiple interactions
- **Provides a command-line interface** for natural language tool interaction
- **Handles multiple MCP servers** simultaneously for maximum tool availability

## Key Features

### UTCP-MCP Integration
- Connects to the UTCP Proxy MCP server (port 8777) by default
- Automatically discovers and loads all available tools from connected servers
- Seamlessly bridges UTCP tools to the Strands agent framework

### Conversational Interface
- Natural language interaction with AI-powered tool selection
- Persistent conversation history within a session
- Built-in commands for session management (`/help`, `/clear`, `/quit`)

### Error Handling & Resilience
- Graceful handling of server connection failures
- Continues operation even if some MCP servers are unavailable
- Detailed error reporting and debugging information

## Prerequisites

Before running this example, ensure you have:

1. **UTCP-MCP Bridge running** (see main project README)
2. **AWS credentials configured** with Amazon Bedrock access for Claude 3 Sonnet
3. **Python 3.8+** installed
4. **Required Python packages** (see requirements.txt)

## Quick Start

### 1. Start UTCP-MCP Bridge

From the main project directory:
```bash
# Using Docker
docker-compose up --build

# OR using local script
./run.sh
```

This will start the UTCP-MCP Bridge servers on:
- Port 8777 (UTCP Proxy MCP)
- Port 8776 (UTCP Client MCP) 
- Port 8778 (Web UI)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

Ensure your AWS credentials are configured with Amazon Bedrock access for Claude models:
```bash
aws configure
# OR set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
```

**Note:** Your AWS account must have access to Amazon Bedrock and the Claude 3 Sonnet model in the specified region.

### 4. Run the Agent

```bash
python mcp_strands_agent.py
```

## Usage

Once the agent starts, you'll see:
```
Initializing MCP clients...
Connecting to http://localhost:8777/utcp-proxy...
Found X tools from http://localhost:8777/utcp-proxy

Total available tools: X
- Name: tool1; Type: function
- Name: tool2; Type: function
...

MCP agent initialized. You can now start your conversation.
Type /help to see available commands.

Enter your query (I can use available MCP tools to help). /help:
```

### Available Commands

- `/help` - Show available commands
- `/clear` - Clear conversation history and start fresh
- `/quit`, `/bye`, `/exit` - End the session

### Example Interactions

```
Enter your query: What tools do you have available?

Response: I have access to several tools through the UTCP-MCP Bridge...

Enter your query: Can you help me search for files in my project?

Response: I can help you search for files. Let me use the file search tool...
```

## Configuration

### MCP Server URLs

Modify the `MCP_SERVERS` list in the script to connect to different servers:

```python
MCP_SERVERS = [
    "http://localhost:8777/utcp-proxy",    # UTCP Proxy MCP
    "http://localhost:8776/utcp-client",   # UTCP Client MCP (optional)
    # Add more MCP servers as needed
]
```

### AI Model

Change the Amazon Bedrock model by modifying the `MODEL_ID` variable:

```python
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"  # Default - Claude 3 Sonnet
# MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"  # Claude 3 Haiku - Faster, less capable
```

**Note:** Ensure the selected model is available in your AWS region and that your account has access to it through Amazon Bedrock.

### System Prompt

Customize the agent's behavior by modifying the `system_prompt` variable to change how the AI assistant behaves and responds to user queries.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   User Input    │───▶│  Strands Agent   │───▶│  Amazon Bedrock     │
└─────────────────┘    └──────────────────┘    │  (Claude Models)    │
                                │               └─────────────────────┘
                                ▼
                       ┌──────────────────┐
                       │   MCP Clients    │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ UTCP-MCP Bridge  │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   UTCP Tools     │
                       └──────────────────┘
```

## Troubleshooting

### Common Issues

1. **"No MCP clients could be created"**
   - Ensure UTCP-MCP Bridge is running
   - Check that ports 8777/8776 are accessible
   - Verify server URLs in `MCP_SERVERS`

2. **AWS/Amazon Bedrock errors**
   - Verify AWS credentials are configured
   - Check AWS region is set to `us-east-1` (or your preferred Bedrock region)
   - Ensure you have access to Amazon Bedrock and Claude models
   - Verify the model ID exists and is available in your region

3. **"No tools available"**
   - Check UTCP-MCP Bridge web UI at http://localhost:8778
   - Verify UTCP providers are registered and tools are enabled
   - Check server logs for connection issues

### Debug Mode

For detailed debugging, the script includes comprehensive error handling and traceback printing. Monitor the console output for specific error messages.

## Integration with UTCP Ecosystem

This example showcases the power of the UTCP-MCP Bridge by:

- **Leveraging UTCP's universal tool protocol** through MCP compatibility
- **Accessing any UTCP-registered tools** without direct UTCP client integration
- **Demonstrating seamless tool discovery** and usage in AI applications
- **Providing a template** for building more complex UTCP-powered agents

## Next Steps

- Explore the UTCP-MCP Bridge web UI at http://localhost:8778
- Register additional UTCP providers to expand tool availability
- Customize the agent's system prompt for specific use cases
- Build more sophisticated workflows using the discovered tools

## Related

- [UTCP-MCP Bridge Main README](../../README.md)
- [Strands SDK Documentation](https://github.com/strands-ai/strands)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
