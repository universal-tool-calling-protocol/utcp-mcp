# /// script
# dependencies = [
#   "fastmcp",
#   "utcp",
#   "numpy",
#   "langchain_huggingface",
#   "sentence_transformers"
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
from typing import Any, Dict, List, Optional, Union, Tuple

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# UTCP imports
from utcp.client.utcp_client import TagSearchStrategy, UtcpClient
from utcp.shared.provider import Provider, HttpProvider, CliProvider, ProviderType, SSEProvider, \
    StreamableHttpProvider, WebSocketProvider, GRPCProvider, GraphQLProvider, \
    TCPProvider, UDPProvider, WebRTCProvider, MCPProvider, TextProvider
from utcp.shared.tool import ProviderUnion, Tool
from utcp.client.utcp_client_config import UtcpVariableNotFound
from utcp.client.utcp_client_config import UtcpClientConfig
from utcp.client.tool_repository import ToolRepository
from utcp.client.tool_search_strategy import ToolSearchStrategy
from langchain_huggingface import HuggingFaceEmbeddings
import numpy as np
import re

# Global UTCP client instance
utcp_client: Optional[UtcpClient] = None

# ============================================== Embeddings Model ============================================================

class EmbeddingModel:
    """
    Local embedding model using all-MiniLM-L6-v2 from HuggingFace.
    """
    
    def __init__(self,
                 api_key: str = None,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the embedding model.
        
        Args:
            api_key: Not used for local models, kept for compatibility
            model_name: The embedding model to use (default: "sentence-transformers/all-MiniLM-L6-v2")
        """
        self.model_name = model_name
        
        # Initialize the local HuggingFace embedding model
        self.model = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs={'device': 'cpu'},  # Use CPU for compatibility
            encode_kwargs={'normalize_embeddings': True}  # Normalize for better similarity
        )
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            A float array representing the embedding
        """
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.model.embed_query, text)
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using local model.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of float arrays representing the embeddings
        """
        if not texts:
            return []
        
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.model.embed_documents, texts)


# ============================================== Embedding In Memory Repo ============================================================


class EmbeddingInMemRepo(ToolRepository):
    """
    In-memory tool repository with embedding support for tool search.
    """
    
    def __init__(self, embedding_model: EmbeddingModel):
        """
        Initialize the in-memory tool repository.
        
        Args:
            embedding_model: The embedding model for generating embeddings
        """
        self.tools: List[Tool] = []
        self.tool_per_provider: Dict[str, Tuple[Provider, List[Tool]]] = {}
        self.embedding_model = embedding_model
        self._tool_embeddings: Dict[str, List[float]] = {}  # tool_name -> embedding
        self._all_tags: set = set()  # Cache of all unique tags
    
    async def save_provider_with_tools(self, provider: Provider, tools: List[Tool]) -> None:
        """
        Save a provider and its tools in the repository.
        
        Args:
            provider: The provider to save.
            tools: The tools associated with the provider.
        """
        # Remove existing tools for this provider if any
        if provider.name in self.tool_per_provider:
            await self.remove_provider(provider.name)
        
        # Add tools to main list and generate embeddings
        # Try batch embedding first for better performance
        try:
            embed_texts = [f"{tool.name} {tool.description} {' '.join(tool.tags)}" for tool in tools]
            embeddings = await self.embedding_model.embed_batch(embed_texts)
            
            # Store embeddings and update tags (skip empty embeddings from failed batch items)
            for tool, embedding in zip(tools, embeddings):
                if embedding:  # Only store non-empty embeddings
                    self._tool_embeddings[tool.name] = embedding
                self._all_tags.update(tool.tags)
                
        except Exception as e:
            print(f"Batch embedding failed, falling back to individual embeddings: {e}")
            # Fallback to individual embedding generation
            for tool in tools:
                try:
                    embed_text = f"{tool.name} {tool.description} {' '.join(tool.tags)}"
                    embedding = await self.embedding_model.embed(embed_text)
                    self._tool_embeddings[tool.name] = embedding
                    self._all_tags.update(tool.tags)
                except Exception as embed_error:
                    print(f"Failed to generate embedding for tool {tool.name}: {embed_error}")
                    # Continue with other tools even if one fails
        
        self.tools.extend(tools)
        self.tool_per_provider[provider.name] = (provider, tools)
    
    async def remove_provider(self, provider_name: str) -> None:
        """
        Remove a provider and its tools from the repository.
        
        Args:
            provider_name: The name of the provider to remove.
            
        Raises:
            ValueError: If the provider is not found.
        """
        if provider_name not in self.tool_per_provider:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        tools_to_remove = self.tool_per_provider[provider_name][1]
        
        # Remove tools from main list
        self.tools = [tool for tool in self.tools if tool not in tools_to_remove]
        
        # Remove embeddings for these tools
        for tool in tools_to_remove:
            self._tool_embeddings.pop(tool.name, None)
        
        # Remove provider
        self.tool_per_provider.pop(provider_name, None)
        
        # Rebuild tags cache
        self._all_tags = set()
        for tool in self.tools:
            self._all_tags.update(tool.tags)
    
    async def remove_tool(self, tool_name: str) -> None:
        """
        Remove a tool from the repository.
        
        Args:
            tool_name: The name of the tool to remove.
            
        Raises:
            ValueError: If the tool is not found.
        """
        provider_name = tool_name.split(".")[0]
        if provider_name not in self.tool_per_provider:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        # Find and remove tool from main list
        new_tools = [tool for tool in self.tools if tool.name != tool_name]
        if len(new_tools) == len(self.tools):
            raise ValueError(f"Tool '{tool_name}' not found")
        
        self.tools = new_tools
        
        # Remove embedding
        self._tool_embeddings.pop(tool_name, None)
        
        # Update provider's tool list
        provider, provider_tools = self.tool_per_provider[provider_name]
        new_provider_tools = [tool for tool in provider_tools if tool.name != tool_name]
        self.tool_per_provider[provider_name] = (provider, new_provider_tools)
        
        # Rebuild tags cache
        self._all_tags = set()
        for tool in self.tools:
            self._all_tags.update(tool.tags)
    
    async def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get a tool from the repository.
        
        Args:
            tool_name: The name of the tool to retrieve.
            
        Returns:
            The tool if found, otherwise None.
        """
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    async def get_tools(self) -> List[Tool]:
        """
        Get all tools from the repository.
        
        Returns:
            List of all tools
        """
        return self.tools
    
    async def get_tools_by_provider(self, provider_name: str) -> Optional[List[Tool]]:
        """
        Get tools associated with a specific provider.
        
        Args:
            provider_name: The name of the provider.
            
        Returns:
            A list of tools associated with the provider, or None if the provider is not found.
        """
        if provider_name not in self.tool_per_provider:
            return None
        return self.tool_per_provider[provider_name][1]
    
    async def get_provider(self, provider_name: str) -> Optional[Provider]:
        """
        Get a provider from the repository.
        
        Args:
            provider_name: The name of the provider to retrieve.
            
        Returns:
            The provider if found, otherwise None.
        """
        if provider_name not in self.tool_per_provider:
            return None
        return self.tool_per_provider[provider_name][0]
    
    async def get_providers(self) -> List[Provider]:
        """
        Get all providers from the repository.
        
        Returns:
            A list of providers.
        """
        return [provider for provider, _ in self.tool_per_provider.values()]
    
    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags from the repository.
        
        Returns:
            List of all unique tags
        """
        return list(self._all_tags)
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(v1)
        vec2 = np.array(v2)
        dot_product = np.dot(vec1, vec2)
        norm_v1 = np.linalg.norm(vec1)
        norm_v2 = np.linalg.norm(vec2)
        return dot_product / (norm_v1 * norm_v2)
    
    async def search_by_embedding(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Tool, float]]:
        """
        Search tools by embedding similarity.
        
        Args:
            query_embedding: The query embedding
            top_k: Maximum number of results to return
            
        Returns:
            List of (Tool, similarity_score) tuples
        """
        results = []
        
        for tool in self.tools:
            if tool.name in self._tool_embeddings:
                embedding = self._tool_embeddings[tool.name]
                similarity = self._cosine_similarity(query_embedding, embedding)
                results.append((tool, similarity))
        
        # Sort by similarity score in descending order
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    # Legacy method for backward compatibility
    def remove_tool_legacy(self, name: str) -> bool:
        """
        Remove a tool from the store (legacy method).
        
        Args:
            name: Name of the tool to remove
            
        Returns:
            True if the tool was removed, False if not found
        """
        try:
            import asyncio
            asyncio.create_task(self.remove_tool(name))
            return True
        except ValueError:
            return False
        except Exception:
            return False
    
    async def search_by_tags(self, tags: List[str], top_k: int = 5) -> List[Tuple[Tool, float]]:
        """
        Search tools by tag overlap (Jaccard similarity).
        
        Args:
            tags: List of tags to search for
            top_k: Maximum number of results to return
            
        Returns:
            List of (tool, score) tuples, where score is the Jaccard similarity
        """
        tools = await self.get_tools()
        results = []
        
        for tool in tools:
            # Calculate tag overlap score (proportion of searched tags that exist in this tool)
            tool_tags = set(tool.tags)
            tool_tags.add(tool.name)
            tool_tags.add(tool.name.split(".")[0])
            tool_tags.add(tool.name.split(".")[1])
            matching_tags = set(tags) & set(tool_tags)
            if matching_tags:
                # Score is a combination of tag match ratio and the number of matching tags
                match_ratio = len(matching_tags) / len(tags)
                tag_weight = len(matching_tags) / (len(tool_tags) + 1)  # +1 to avoid division by zero
                score = (match_ratio + tag_weight) / 2
                results.append((tool, score))
        
        # Sort by tag overlap score in descending order
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


# ============================================== Tool Selector ============================================================
class ToolSelector(ToolSearchStrategy):
    """
    Class for selecting the most appropriate tools based on user queries.
    """
    
    def __init__(self, vector_store: EmbeddingInMemRepo, embedding_model: EmbeddingModel):
        """
        Initialize the tool selector.
        
        Args:
            vector_store: The vector store for tool lookup
            embedding_model: The embedding model for generating embeddings
        """
        self.vector_store = vector_store
        self.embedding_model = embedding_model
    
    async def search_tools(self, query: str, limit: int = 10) -> List[Tool]:
        """
        Search for tools relevant to the query.

        Args:
            query: The search query.
            limit: The maximum number of tools to return. 0 for no limit.

        Returns:
            A list of tools that match the search query.
        """
        # Strategy 1: Extract relevant tags from query
        query_lower = query.lower()
        # Extract words from the query, filtering out non-word characters
        relevant_tags = set(re.findall(r'\w+', query_lower))
        
        # Strategy 2: Generate embedding for the query
        query_embedding = await self.embedding_model.embed(query)
        
        # Perform searches using both strategies
        
        # Strategy 1: Get tools by tags (limit/2 tools)
        tagSearchStrategy = TagSearchStrategy(self.vector_store)
        tag_tools = await tagSearchStrategy.search_tools(query, limit // 2 if limit > 0 else 5)
        
        # Strategy 2: Get tools by embeddings (limit tools to allow for deduplication)
        embedding_results = await self.vector_store.search_by_embedding(query_embedding, top_k=limit if limit > 0 else 10)
        
        # Track already selected tools by name
        selected_tools = []
        selected_names = set()
        
        # First, add all tag-based tools
        for tool in tag_tools:
            if tool.name not in selected_names:
                selected_tools.append(tool)
                selected_names.add(tool.name)
        
        # Then, add top embedding tools that aren't already selected
        for tool, score in embedding_results:
            if len(selected_tools) >= limit:
                break
            if tool.name not in selected_names:
                selected_tools.append(tool)
                selected_names.add(tool.name)
        
        return selected_tools
    
    async def find_tools(self, query: str, max_tools: int = 5) -> List[Tool]:
        """
        Legacy method for backward compatibility.
        Select the most appropriate tools for a user query using multiple strategies.
        
        Args:
            query: The user query
            max_tools: Maximum number of tools to return
            
        Returns:
            List of selected tools
        """
        return await self.search_tools(query, max_tools)
    
    def get_tool_summary(self, tools: List[Tool]) -> List[Dict[str, Any]]:
        """
        Generate a summary of tools for presenting to the agent.
        
        Args:
            tools: List of tools
            
        Returns:
            List of tool summary dictionaries
        """
        summaries = []
        
        for tool in tools:
            summary = {
                "name": tool.name,
                "description": tool.description,
                "tags": tool.tags,
                "provider": tool.tool_provider.name if tool.tool_provider else None,
                "provider_type": tool.tool_provider.provider_type if tool.tool_provider else None,
                # Include basic parameter information without full schema details
                "parameters": list(tool.inputs.properties.keys()) if tool.inputs and tool.inputs.properties else [],
                "returns": list(tool.outputs.properties.keys()) if tool.outputs and tool.outputs.properties else []
            }
            summaries.append(summary)
        
        return summaries

# ============================================== MCP ============================================================

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
    embedding_model = EmbeddingModel()
    vector_store = EmbeddingInMemRepo(embedding_model=embedding_model)
    utcp_client = await UtcpClient.create(
        config=config,
        tool_repository=vector_store,
        search_strategy=ToolSelector(vector_store, embedding_model)
    )
    
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
    return await search_tools_func(query, limit)

async def search_tools_func(query: str, limit: int = 10) -> Dict[str, Any]:
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
        return {"tools": [{"name": tool.name, "description": tool.description, "input_schema": tool.inputs.model_dump(exclude_none=True)} for tool in tools]}
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
        tool = await client.tool_repository.get_tool(tool_name)
        
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


# ============================================== Main ============================================================

async def main():
    global utcp_client
    utcp_client = await initialize_utcp_client()
    await mcp.run_async(transport="stdio")

if __name__ == "__main__":
    # Run the FastMCP server
    asyncio.run(main())
