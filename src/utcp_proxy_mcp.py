import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse
import uvicorn
from config import Config
from logger import logger
from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig
from utcp.client.tool_repositories.in_mem_tool_repository import InMemToolRepository
from utcp.client.tool_search_strategies.tag_search import TagSearchStrategy
import keyword


class UTCPProxy:
    def __init__(self):
        self.client: Optional[UtcpClient] = None
        self.tools: List[Any] = []
        self.providers: List[Any] = []
        self.mcp = FastMCP("utcp-proxy-mcp")
        
    async def initialize(self) -> None:
        """Initialize UTCP client and register tools"""
        try:
            logger.info("UTCP-PROXY-MCP: initializing...")
            config = UtcpClientConfig(providers_file_path=Config.PROVIDERS_PATH)
            self.client = await UtcpClient.create(
                config=config,
                tool_repository=InMemToolRepository(),
                search_strategy=TagSearchStrategy(InMemToolRepository())
            )
            
            self.tools = await self.client.tool_repository.get_tools()
            self.providers = await self.client.tool_repository.get_providers()

            for tool in self.tools:
                proxy_func = self._create_tool_proxy(tool)
                self.mcp.tool(name=tool.name, description=tool.description or "UTCP tool")(proxy_func)

            logger.info(f"UTCP-PROXY-MCP: registered {len(self.providers)} providers with {len(self.tools)} tools")
                            
        except Exception as e:
            logger.error(f"UTCP-PROXY-MCP: failed to initialize - {e}")
            raise
    
    def _create_tool_proxy(self, tool):
        """Create a proxy function for a UTCP tool"""
        # Helper to get attribute or dict value
        def get(obj, attr, default=None):
            if isinstance(obj, dict):
                return obj.get(attr, default)
            return getattr(obj, attr, default)

        # Get the input schema (object or dict)
        inputs = get(tool, 'inputs', {})
        properties = get(inputs, 'properties', {})
        required = set(get(inputs, 'required', []) or [])
        param_map = {}
        required_params = []
        optional_params = []

        for orig_name in properties.keys():
            py_name = orig_name[:-2] if orig_name.endswith('[]') else orig_name
            # If py_name is a Python keyword, append an underscore
            if keyword.iskeyword(py_name):
                py_name_safe = py_name + '_'
            else:
                py_name_safe = py_name
            param_map[py_name_safe] = orig_name
            if py_name in required or orig_name in required:
                required_params.append(py_name_safe)
            else:
                optional_params.append(f"{py_name_safe}=None")

        params_str = ", ".join(required_params + optional_params)

        # Build function code
        func_code = f"async def proxy({params_str}):\n"
        func_code += "    args = {}\n"
        for py_name_safe, orig_name in param_map.items():
            func_code += f"    if {py_name_safe} is not None:\n"
            func_code += f"        args['{orig_name}'] = {py_name_safe}\n"
        func_code += f"    return await bridge.client.call_tool('{get(tool, 'name')}', args)\n"

        # Create function
        namespace = {"bridge": self}
        exec(func_code, globals(), namespace)
        proxy_func = namespace["proxy"]
        proxy_func.__name__ = get(tool, 'name', 'utcp_tool').replace('.', '_')
        proxy_func.__doc__ = get(tool, 'description', 'UTCP tool proxy')

        return proxy_func
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.client:
            logger.info("UTCP-PROXY-MCP: cleaning...")
            # Add any cleanup logic here if needed
            self.client = None

    async def run(self):
        await self.mcp.run_async(
            transport="http", 
            host=Config.HOST, 
            port=Config.MCP_PROXY_PORT, 
            path=Config.MCP_PROXY_PATH
        )
