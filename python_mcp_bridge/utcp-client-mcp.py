# /// script
# dependencies = [
#   "fastmcp",
#   "utcp==1.0.1",
#   "utcp-mcp==1.0.1",
#   "utcp-text==1.0.1",
#   "utcp-cli==1.0.1",
#   "utcp-http==1.0.1",
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
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# UTCP imports
from utcp.utcp_client import UtcpClient
from utcp.data.utcp_client_config import UtcpClientConfig
from utcp.data.call_template import CallTemplate

# Global UTCP client instance
utcp_client: Optional[UtcpClient] = None

# Initialize FastMCP server
mcp = FastMCP("UTCP Client MCP Server")

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
async def register_manual(manual_call_template: CallTemplate) -> Dict[str, Any]:
    """Register a new tool provider with the UTCP client.
    
    Args:
        manual_call_template: Call template to the endpoint of a UTCP Manual
        
    Returns:
        Dictionary with success status and list of registered tools
    """
    client = await initialize_utcp_client()
    
    try:
        tools = await client.register_manual(manual_call_template)
        
        return {
            "success": True,
            "manual_name": manual_call_template.name,
            "tools_registered": len(tools),
            "tool_names": [tool.name for tool in tools]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def deregister_manual(manual_name: str) -> Dict[str, Any]:
    """Deregister a tool provider from the UTCP client.
    
    Args:
        manual_name: Name of the manual to deregister
        
    Returns:
        Dictionary with success status
    """
    client = await initialize_utcp_client()
    
    try:
        await client.deregister_manual(manual_name)
        return {
            "success": True,
            "message": f"Manual '{manual_name}' deregistered successfully"
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
async def search_tools(task_description: str, limit: int = 10) -> Dict[str, Any]:
    """Search for tools using a query string.
    
    Args:
        task_description: Description of the task to search for tools
        limit: Optional limit on the number of tools to return
        
    Returns:
        Dictionary with success status and matching tools
    """
    client = await initialize_utcp_client()
    
    try:
        tools = await client.search_tools(task_description, limit)
        return {"tools": [{"name": tool.name, "description": tool.description, "input_schema": tool.inputs.model_dump(exclude_none=True)} for tool in tools]}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_required_keys_for_tool(tool_name: str) -> Dict[str, Any]:
    """Get required environment variables for a registered tool.
    
    Args:
        tool_name: Name of the tool to get variables for
        
    Returns:
        Dictionary with success status and required variables
    """
    client = await initialize_utcp_client()
    
    try:
        variables = await client.get_required_variables_for_registered_tool(tool_name)
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


@mcp.tool()
async def tool_info(tool_name: str) -> Dict[str, Any]:
    """Get complete information about a specific tool including all details using model_dump().
    
    Args:
        tool_name: Name of the tool to get complete information for
        
    Returns:
        Dictionary with success status and complete tool information with model_dump()
    """
    client = await initialize_utcp_client()
    
    try:
        # Search for the specific tool
        tool = await client.config.tool_repository.get_tool(tool_name)
        
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }
        
        # Return complete tool information with model_dump()
        return {
            "success": True,
            "tool": tool.model_dump()
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
