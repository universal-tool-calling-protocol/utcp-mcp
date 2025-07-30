import os
import json
import asyncio
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP
from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse
from config import Config
from logger import logger
from utcp_proxy_mcp import UTCPProxy
from utcp_client_mcp import UTCPClient
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Body
from utcp.shared.provider import Provider, HttpProvider, CliProvider, SSEProvider, StreamableHttpProvider, WebSocketProvider, GRPCProvider, GraphQLProvider, TCPProvider, UDPProvider, WebRTCProvider, MCPProvider, TextProvider


utcp_proxy = UTCPProxy()
utcp_client = UTCPClient()

PROVIDERS_PATH = os.path.join(os.path.dirname(__file__), '../data/providers.json')
# Ensure we have the absolute path
PROVIDERS_PATH = os.path.abspath(PROVIDERS_PATH)

def read_providers_file():
    try:
        if not os.path.exists(PROVIDERS_PATH):
            # Create empty providers file if it doesn't exist
            os.makedirs(os.path.dirname(PROVIDERS_PATH), exist_ok=True)
            with open(PROVIDERS_PATH, 'w') as f:
                json.dump([], f)
            return []
        
        with open(PROVIDERS_PATH, 'r') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception as e:
        logger.error(f"Error reading providers file: {e}")
        return []

def write_providers_file(providers):
    try:
        os.makedirs(os.path.dirname(PROVIDERS_PATH), exist_ok=True)
        with open(PROVIDERS_PATH, 'w') as f:
            json.dump(providers, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing providers file: {e}")
        raise

async def reload_providers():
    logger.info("Reloading providers...")
    await utcp_client.initialize()
    await utcp_proxy.initialize()
    logger.info("Providers reloaded successfully")


# Provider type mapping (reuse from UtcpClient)
provider_classes = {
    'http': HttpProvider,
    'cli': CliProvider,
    'sse': SSEProvider,
    'http_stream': StreamableHttpProvider,
    'websocket': WebSocketProvider,
    'grpc': GRPCProvider,
    'graphql': GraphQLProvider,
    'tcp': TCPProvider,
    'udp': UDPProvider,
    'webrtc': WebRTCProvider,
    'mcp': MCPProvider,
    'text': TextProvider
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    try:
        logger.info(f"Starting application with providers path: {PROVIDERS_PATH}")
        await utcp_client.initialize()
        await utcp_proxy.initialize()
        logger.info("Application started successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        logger.info("Application shutdown complete")

app = FastAPI(
    title="UTCP-MCP Bridge",
    version="1.0.0",
    lifespan=lifespan
)

app.mount("/web", StaticFiles(directory="web"), name="web")

@app.get("/")
async def root():
    return FileResponse("web/index.html")

@app.get("/health")
async def health():
    """Health check endpoint"""
    if not utcp_proxy.client:
        raise HTTPException(status_code=503, detail="UTCP client not initialized")
    
    return JSONResponse({
        "status": "healthy",
        "providers": len(utcp_proxy.providers),
        "tools": len(utcp_proxy.tools),
        "provider_names": [p.name for p in utcp_proxy.providers],
        "tool_names": [t.name for t in utcp_proxy.tools],
    })

@app.post("/validate-providers")
async def validate_providers(providers_data: list = Body(...)):
    """Validate provider data without saving"""
    if not isinstance(providers_data, list):
        raise HTTPException(status_code=400, detail="Payload must be a JSON array")
    
    validated = []
    errors = []
    
    for i, provider in enumerate(providers_data):
        try:
            provider_type = provider.get('provider_type')
            if not provider_type:
                errors.append(f"Provider {i}: missing 'provider_type'")
                continue
                
            provider_class = provider_classes.get(provider_type)
            if not provider_class:
                errors.append(f"Provider {i}: unsupported provider_type '{provider_type}'")
                continue
                
            provider_obj = provider_class.model_validate(provider)
            validated.append({
                "index": i,
                "name": provider_obj.name,
                "type": provider_type,
                "valid": True
            })
        except Exception as e:
            errors.append(f"Provider {i} ('{provider.get('name', 'unknown')}'): {str(e)}")
    
    return JSONResponse({
        "valid": len(errors) == 0,
        "validated": validated,
        "errors": errors
    })

@app.get("/tools")
async def list_tools():
    """List available tools"""
    if not utcp_proxy.client:
        raise HTTPException(status_code=503, detail="UTCP client not initialized")

    def get(obj, attr, default=None):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    return JSONResponse({
        "tools": [
            {
                "name": get(tool, 'name', ''),
                "description": get(tool, 'description', ''),
                "inputs": get(get(tool, 'inputs', {}), 'properties', {})
            }
            for tool in utcp_proxy.tools
        ]
    })

@app.get("/providers")
async def list_providers():
    """List available providers"""
    try:
        # Return the raw providers.json data for the web UI
        providers = read_providers_file()
        return JSONResponse({"providers": providers})
    except Exception as e:
        logger.error(f"Error reading providers file: {e}")
        return JSONResponse({"providers": []})

@app.post("/providers")
async def add_provider(provider: dict = Body(...)):
    """Add a new provider and register it with UTCP clients, and register its tools as MCP tools."""
    providers = read_providers_file()
    # Prevent duplicate names
    if any(p.get('name') == provider.get('name') for p in providers):
        raise HTTPException(status_code=400, detail="Provider with this name already exists")
    # Use correct provider class
    provider_type = provider.get('provider_type')
    provider_class = provider_classes.get(provider_type)
    if not provider_class:
        raise HTTPException(status_code=400, detail=f"Unsupported provider_type: {provider_type}")
    
    try:
        provider_obj = provider_class.model_validate(provider)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid provider data: {str(e)}")
    
    # Register with both proxy and client
    if utcp_proxy.client:
        await utcp_proxy.add_provider(provider_obj)
    if utcp_client.client:
        await utcp_client.add_provider(provider_obj)
    providers.append(provider)
    write_providers_file(providers)
    return {"status": "ok", "providers": providers}

@app.delete("/providers/{provider_name}")
async def remove_provider(provider_name: str):
    """Remove a provider by name and deregister it from UTCP clients, and remove its tools from MCP."""
    providers = read_providers_file()
    new_providers = [p for p in providers if p.get('name') != provider_name]
    if len(new_providers) == len(providers):
        raise HTTPException(status_code=404, detail="Provider not found")
    # Deregister from both proxy and client
    if utcp_proxy.client:
        await utcp_proxy.remove_provider(provider_name)
    if utcp_client.client:
        await utcp_client.remove_provider(provider_name)
  
    write_providers_file(new_providers)
    return {"status": "ok", "providers": new_providers}

@app.put("/providers")
async def replace_providers(new_providers: list = Body(...)):
    """Replace the entire providers.json file and reload all providers/tools."""
    if not isinstance(new_providers, list):
        raise HTTPException(status_code=400, detail="Payload must be a JSON array")
    
    # Check if providers have actually changed
    current_providers = read_providers_file()
    if current_providers == new_providers:
        logger.info("Providers unchanged, skipping reload")
        return {"status": "ok", "providers": new_providers, "changed": False}
    
    # Validate all providers first before making any changes
    validated_providers = []
    for provider in new_providers:
        provider_type = provider.get('provider_type')
        provider_class = provider_classes.get(provider_type)
        if not provider_class:
            raise HTTPException(status_code=400, detail=f"Unsupported provider_type: {provider_type}")
        try:
            provider_obj = provider_class.model_validate(provider)
            validated_providers.append(provider_obj)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid provider data for '{provider.get('name', 'unknown')}': {str(e)}")
    
    logger.info("Providers changed, reloading...")
    
    # Remove all current providers
    if utcp_proxy.client:
        for provider in list(await utcp_proxy.client.tool_repository.get_providers()):
            await utcp_proxy.remove_provider(getattr(provider, 'name', None))
    if utcp_client.client:
        for provider in list(await utcp_client.client.tool_repository.get_providers()):
            await utcp_client.remove_provider(getattr(provider, 'name', None))
    
    # Add all new providers
    for provider_obj in validated_providers:
        if utcp_proxy.client:
            await utcp_proxy.add_provider(provider_obj)
        if utcp_client.client:
            await utcp_client.add_provider(provider_obj)
    
    write_providers_file(new_providers)
    return {"status": "ok", "providers": new_providers, "changed": True}
