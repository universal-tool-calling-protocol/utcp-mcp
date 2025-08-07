# /// script
# dependencies = [
#   "fastmcp",
#   "utcp==0.2.1",
# ]
# ///
"""FastMCP stdio server that proxies UTCP client functionalities as tools.

This server provides MCP tools that expose the core UTCP client operations:
- Registering and deregistering tool providers
- Calling tools through providers
- Searching for available tools
- Loading providers from a JSON configuration file
- Getting required variables for tools

The server automatically loads providers from a 'providers.json' file in the same directory.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# UTCP imports
from utcp.client.utcp_client import UtcpClient
from utcp.shared.provider import Provider, HttpProvider, CliProvider, ProviderType, SSEProvider, \
    StreamableHttpProvider, WebSocketProvider, GRPCProvider, GraphQLProvider, \
    TCPProvider, UDPProvider, WebRTCProvider, MCPProvider, TextProvider
from utcp.shared.tool import ProviderUnion, Tool
from utcp.client.utcp_client_config import UtcpVariableNotFound
from utcp.client.utcp_client_config import UtcpClientConfig

# Global UTCP client instance
utcp_client: Optional[UtcpClient] = None

# Initialize FastMCP server
mcp = FastMCP("UTCP Client MCP Server")


class ToolCallInput(BaseModel):
    """Input model for tool calls."""
    tool_name: str = Field(description="Name of the tool to call (format: provider.tool_name)")
    arguments: Dict[str, Any] = Field(description="Arguments to pass to the tool")


class SearchToolsInput(BaseModel):
    """Input model for tool search."""
    query: str = Field(description="Search query for finding tools")
    limit: int = Field(default=10, description="Maximum number of tools to return (0 for no limit)")


class LoadProvidersInput(BaseModel):
    """Input model for loading providers from file."""
    providers_file_path: str = Field(description="Path to the providers JSON file")


class GetVariablesInput(BaseModel):
    """Input model for getting required variables."""
    tool_name: str = Field(description="Name of the tool to get variables for")


async def initialize_utcp_client():
    """Initialize the UTCP client and try to load providers.json from the same directory."""
    global utcp_client
    
    if utcp_client is not None:
        return utcp_client
    
    script_dir = Path(__file__).parent
    config_file = script_dir / ".utcp_config.json"
    
    if config_file.exists():
        config = json.loads(config_file.read_text())
        config = UtcpClientConfig.model_validate(config)
    else:
        config = UtcpClientConfig()

    # Create UTCP client
    utcp_client = await UtcpClient.create(config=config)
    
    return utcp_client


@mcp.tool()
async def register_tool_provider(provider: ProviderUnion) -> Dict[str, Any]:
    """Register a new tool provider with the UTCP client.
    
    Args:
        provider_input: Provider configuration including type, name, and data
        
    Returns:
        Dictionary with success status and list of registered tools
    """
    client = await initialize_utcp_client()
    
    try:
        tools = await client.register_tool_provider(provider)
        
        return {
            "success": True,
            "provider_name": provider.name,
            "tools_registered": len(tools),
            "tool_names": [tool.name for tool in tools]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def deregister_tool_provider(provider_name: str) -> Dict[str, Any]:
    """Deregister a tool provider from the UTCP client.
    
    Args:
        provider_name: Name of the provider to deregister
        
    Returns:
        Dictionary with success status
    """
    client = await initialize_utcp_client()
    
    try:
        await client.deregister_tool_provider(provider_name)
        return {
            "success": True,
            "message": f"Provider '{provider_name}' deregistered successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call a tool through the UTCP client.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Arguments for the tool call
        
    Returns:
        Dictionary with success status and tool result
    """
    client = await initialize_utcp_client()
    
    try:
        result = await client.call_tool(tool_name, arguments)
        return {
            "success": True,
            "tool_name": tool_name,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "tool_name": tool_name,
            "error": str(e)
        }


@mcp.tool()
async def search_tools(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search for tools using a query string.
    
    Args:
        query: Search query
        limit: Optional limit on the number of tools to return
        
    Returns:
        Dictionary with success status and matching tools
    """
    client = await initialize_utcp_client()
    
    try:
        tools = await client.search_tools(query, limit)
        return {"tools": [tool.model_dump() for tool in tools]}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def load_providers_from_file(providers_file_path: str) -> Dict[str, Any]:
    """Load providers from a JSON file.
    
    Args:
        providers_file_path: Path to the providers JSON file
        
    Returns:
        Dictionary with success status and loaded providers
    """
    client = await initialize_utcp_client()
    
    try:
        providers = await client.load_providers(providers_file_path)
        return {
            "success": True,
            "providers_file": providers_file_path,
            "providers_loaded": len(providers),
            "provider_names": [provider.name for provider in providers]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def get_required_variables_for_tool(tool_name: str) -> Dict[str, Any]:
    """Get required environment variables for a registered tool.
    
    Args:
        tool_name: Name of the tool to get variables for
        
    Returns:
        Dictionary with success status and required variables
    """
    client = await initialize_utcp_client()
    
    try:
        variables = await client.get_required_variables_for_tool(tool_name)
        return {
            "success": True,
            "tool_name": tool_name,
            "required_variables": variables
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def main():
    global utcp_client
    utcp_client = await initialize_utcp_client()
    await mcp.run_async(transport="stdio")

if __name__ == "__main__":
    # Run the FastMCP server
    asyncio.run(main())
