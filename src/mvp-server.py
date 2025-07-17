import os
import asyncio
from fastmcp import FastMCP
from fastapi import FastAPI
from starlette.responses import JSONResponse
import uvicorn
from utcp.client.utcp_client import UtcpClient
from utcp.client.utcp_client_config import UtcpClientConfig
from utcp.client.tool_repositories.in_mem_tool_repository import InMemToolRepository
from utcp.client.tool_search_strategies.tag_search import TagSearchStrategy

# Path to providers.json
PROVIDERS_PATH = os.path.join(os.path.dirname(__file__), "providers.json")

# Create FastAPI app for /health endpoint
app = FastAPI()

# Create MCP server
mcp = FastMCP("utcp-mcp-bridge")

utcp_client = None
utcp_tools = []
utcp_providers = []

def make_proxy(tool):
    param_map = {}
    required = set(tool.inputs.required or [])
    required_params = []
    optional_params = []
    for orig_name in tool.inputs.properties.keys():
        py_name = orig_name[:-2] if orig_name.endswith('[]') else orig_name
        param_map[py_name] = orig_name
        if py_name in required or orig_name in required:
            required_params.append(py_name)
        else:
            optional_params.append(f"{py_name}=None")
    params_str = ", ".join(required_params + optional_params)
    func_code = f"async def proxy({params_str}):\n"
    func_code += "    args = {}\n"
    for py_name, orig_name in param_map.items():
        func_code += f"    args['{orig_name}'] = {py_name}\n"
    func_code += f"    return await utcp_client.call_tool('{tool.name}', args)\n"
    ns = {}
    exec(func_code, globals(), ns)
    proxy_func = ns["proxy"]
    proxy_func.__name__ = tool.name.replace('.', '_')
    proxy_func.__doc__ = tool.description or 'UTCP tool proxy'
    return proxy_func

@app.get("/health")
async def health():
    return JSONResponse({
        "providers": len(utcp_providers),
        "tools": len(utcp_tools),
        "provider_names": [p.name for p in utcp_providers],
        "tool_names": [t.name for t in utcp_tools],
    })

async def utcp_init():
    global utcp_client, utcp_tools, utcp_providers
    config = UtcpClientConfig(providers_file_path=PROVIDERS_PATH)
    utcp_client = await UtcpClient.create(
        config=config,
        tool_repository=InMemToolRepository(),
        search_strategy=TagSearchStrategy(InMemToolRepository())
    )
    utcp_tools = await utcp_client.tool_repository.get_tools()
    utcp_providers = await utcp_client.tool_repository.get_providers()

    print(f"Successfully registered {len(utcp_providers)} providers with {len(utcp_tools)} tools")
    # Register each UTCP tool as an MCP tool
    for tool in utcp_tools:
        proxy_func = make_proxy(tool)
        mcp.tool(name=tool.name, description=tool.description or "UTCP tool")(proxy_func)

async def run_fastapi():
    """Run FastAPI server asynchronously"""
    config = uvicorn.Config(app, host="0.0.0.0", port=8788, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def run_mcp():
    """Run MCP server asynchronously"""
    await mcp.run_async(transport="http", host="0.0.0.0", port=8787, path="/mcp")

async def main():
    # Initialize UTCP first
    await utcp_init()
    
    # Run both servers concurrently
    await asyncio.gather(
        run_fastapi(),
        run_mcp()
    )

# Entrypoint
if __name__ == "__main__":
    asyncio.run(main())