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


utcp_proxy = UTCPProxy()
utcp_client = UTCPClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    try:
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
    if not utcp_proxy.client:
        raise HTTPException(status_code=503, detail="UTCP client not initialized")
    
    return JSONResponse({
        "providers": [
            {
                "name": provider.name,
                "description": getattr(provider, 'description', None)
            }
            for provider in utcp_proxy.providers
        ]
    })
