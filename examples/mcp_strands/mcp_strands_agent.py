from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient
import traceback
import os
from contextlib import ExitStack

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
os.environ['AWS_REGION'] = 'us-east-1'

# MCP server configurations
MCP_SERVERS = [
    "http://localhost:8777/utcp-proxy",
    # "http://localhost:8776/utcp-client"
]

system_prompt = """You are a helpful AI assistant that can use various tools through MCP (Model Context Protocol) 
and its dedicated Universal Tool Calling Protocol server.
You have access to tools that can help you perform different tasks. When a user asks for something, 
analyze their request and use the appropriate tools to help them accomplish their goal.

Be helpful, accurate, and explain what you're doing when you use tools."""

# This application uses Strand SDK to connect to MCP servers and provides a simple interface
# to call available MCP tools through natural language prompts.

def create_streamable_http_transport(url):
    return streamablehttp_client(url=url)

def print_help():
    """Print available commands"""
    print("\nAvailable commands:")
    print("  /help - Show this help message")
    print("  /clear - Clear the conversation history")
    print("  /quit, /bye, /exit - End the conversation")

def main():
    print("\nInitializing MCP clients...")
    try:
        # Create MCP clients for each server
        mcp_clients = []
        all_tools = []
        
        # Connect to each MCP server and collect tools
        for server_url in MCP_SERVERS:
            print(f"Connecting to {server_url}...")
            try:
                # Fix lambda closure issue by using default parameter
                mcp_client = MCPClient(lambda url=server_url: create_streamable_http_transport(url))
                mcp_clients.append(mcp_client)
            except Exception as e:
                print(f"Warning: Could not create client for {server_url}: {e}")
                continue

        if not mcp_clients:
            print("No MCP clients could be created. Please check your MCP servers.")
            return

        # Use nested context managers to keep all MCP connections active
        with ExitStack() as stack:
            # Enter context for all MCP clients
            active_clients = []
            for i, client in enumerate(mcp_clients):
                try:
                    stack.enter_context(client)
                    active_clients.append((client, MCP_SERVERS[i]))
                except Exception as e:
                    print(f"Warning: Could not enter context for client {MCP_SERVERS[i]}: {e}")
                    continue
            
            if not active_clients:
                print("No MCP clients could be activated.")
                return
            
            # Collect tools from all active clients
            for client, server_url in active_clients:
                try:
                    tools = client.list_tools_sync()
                    all_tools.extend(tools)
                    print(f"Found {len(tools)} tools from {server_url}")
                except Exception as e:
                    print(f"Warning: Could not get tools from {server_url}: {e}")
                    continue

            print(f"\nTotal available tools: {len(all_tools)}")
            for tool in all_tools:
                print(f"- Name: {tool.tool_name}; Type: {tool.tool_type}")
            
            if not all_tools:
                print("No tools available. Please check your MCP servers.")
                return
            
            # Create a single agent instance to maintain conversation context
            mcp_agent = Agent(
                model=MODEL_ID,
                system_prompt=system_prompt,
                tools=all_tools
            )
            
            print("\nMCP agent initialized. You can now start your conversation.")
            print("Type /help to see available commands.")
            
            while True:
                try:
                    user_prompt = input("\nEnter your query (I can use available MCP tools to help). /help: ")
                    
                    # Handle special commands
                    if user_prompt.lower() in ["/bye", "/quit", "/exit", "bye", "quit", "exit"]:
                        print("\nEnding current chat session. Now Go Build...")
                        break
                    elif user_prompt.lower() == "/help":
                        print_help()
                        continue
                    elif user_prompt.lower() == "/clear":
                        # Create a new agent instance to clear conversation history
                        mcp_agent = Agent(
                            model=MODEL_ID,
                            system_prompt=system_prompt,
                            tools=all_tools
                        )
                        print("\nConversation history cleared.")
                        continue
                    
                    # Use the same agent instance for all interactions to maintain context
                    print(f"\nUser query: {user_prompt}")
                    print("\nResponse:")
                    
                    response = mcp_agent(user_prompt)
                    if hasattr(response, 'message') and response.message:
                        content = response.message.get("content", [{}])
                        if content and isinstance(content, list) and len(content) > 0:
                            text = content[0].get("text", "No response")
                            print(text)
                        else:
                            print("No content in response")
                    else:
                        print("No message in response")
                    
                    print("\n")  # Add a newline after the response

                except KeyboardInterrupt:
                    print("\nChat session terminated by user.")
                    break
                except Exception as error:
                    print(f"\nError during chat session: {error}")
                    traceback.print_exc()
    
    except Exception as e:
        print("\nException Details:")
        print(f"Type: {type(e)}")
        print(f"Message: {str(e)}")
        print("\nTraceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
