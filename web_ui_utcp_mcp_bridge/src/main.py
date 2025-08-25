import asyncio
import uvicorn
from logger import logger
from config import Config
from server import utcp_client, utcp_proxy, app

async def run_client_mcp():
    """Run UTCP Client MCP server asynchronously"""
    await utcp_client.run()

async def run_proxy_mcp():
    """Run UTCP Proxy MCP server asynchronously"""
    await utcp_proxy.run()

async def run_fastapi():
    """Run FastAPI server asynchronously"""
    config = uvicorn.Config(
        app, 
        host=Config.HOST, 
        port=Config.FASTAPI_PORT, 
        log_level="info",
        reload=True
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Main entry point"""
    await asyncio.gather(
        run_fastapi(),
        run_proxy_mcp(),
        run_client_mcp(),
        return_exceptions=True
    )

if __name__ == "__main__":
    try:
        logger.info("Starting UTCP-MCP Bridge...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        logger.info("Application shutting down...")
