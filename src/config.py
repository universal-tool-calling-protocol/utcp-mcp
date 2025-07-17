import os
from dotenv import load_dotenv


load_dotenv()  

class Config:
    PROVIDERS_PATH = os.getenv("PROVIDERS_PATH", "/app/data/providers.json")
    HOST = os.getenv("HOST", "0.0.0.0")
    FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8778"))
    MCP_PROXY_PORT = int(os.getenv("MCP_PROXY_PORT", "8777"))
    MCP_CLIENT_PORT = int(os.getenv("MCP_CLIENT_PORT", "8776"))
    MCP_PROXY_PATH = os.getenv("MCP_PROXY_PATH", "/utcp-proxy")
    MCP_CLIENT_PATH = os.getenv("MCP_CLIENT_PATH", "/utcp-client")
