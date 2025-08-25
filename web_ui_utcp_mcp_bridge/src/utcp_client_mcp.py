import os
import asyncio
from config import Config
from logger import logger
from fastmcp import FastMCP
from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig
from utcp.client.tool_repositories.in_mem_tool_repository import InMemToolRepository
from utcp.client.tool_search_strategies.tag_search import TagSearchStrategy
from utcp.shared.provider import Provider
from typing import Dict, Any, List, Optional


class UTCPClient:
    def __init__(self):
        self.client: Optional[UtcpClient] = None
        self.mcp = FastMCP("utcp-client-mcp")

    async def initialize(self) -> None:
        logger.info("UTCP-CLIENT-MCP: initializing...")
        config = UtcpClientConfig(providers_file_path=Config.PROVIDERS_PATH)
        self.client = await UtcpClient.create(
            config=config,
            tool_repository=InMemToolRepository(),
            search_strategy=TagSearchStrategy(InMemToolRepository())
        )
        await self._register_mcp_tools()
        logger.info("UTCP-CLIENT-MCP: server initialized.")

    async def _register_mcp_tools(self):
        @self.mcp.tool(name="register_tool_provider", description="Register a tool provider. Args: provider_dict (dict)")
        async def register_tool_provider(provider_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
            provider = Provider.model_validate(provider_dict)
            tools = await self.client.register_tool_provider(provider)
            return [tool.model_dump() for tool in tools]

        @self.mcp.tool(name="deregister_tool_provider", description="Deregister a tool provider. Args: provider_name (str)")
        async def deregister_tool_provider(provider_name: str) -> str:
            await self.client.deregister_tool_provider(provider_name)
            return f"Provider '{provider_name}' deregistered."

        @self.mcp.tool(name="call_tool", description="Call a tool. Args: tool_name (str), arguments (dict)")
        async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
            return await self.client.call_tool(tool_name, arguments)

        @self.mcp.tool(name="search_tools", description="Search for tools. Args: query (str), limit (int, optional)")
        async def search_tools(query: str, limit: int = 10) -> List[Dict[str, Any]]:
            tools = self.client.search_tools(query, limit)
            return [tool.model_dump() for tool in tools]

    async def add_provider(self, provider_obj) -> None:
        logger.info(f"UTCP-CLIENT-MCP: registering provider {provider_obj.name}")
        await self.client.register_tool_provider(provider_obj)

    async def remove_provider(self, provider_name: str) -> None:
        logger.info(f"UTCP-CLIENT-MCP: deregistering provider {provider_name}")
        await self.client.deregister_tool_provider(provider_name)

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.client:
            logger.info("UTCP-CLIENT-MCP: cleaning...")
            # Add any cleanup logic here if needed
            self.client = None

    async def run(self):
        await self.mcp.run_async(
            transport="http",
            host=Config.HOST,
            port=Config.MCP_CLIENT_PORT,
            path=Config.MCP_CLIENT_PATH
        )
