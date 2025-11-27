use anyhow::{Context, Result};
use rs_utcp::config::UtcpClientConfig;
use rs_utcp::plugins::codemode::{CodeModeArgs, CodeModeUtcp};
use rs_utcp::repository::in_memory::InMemoryToolRepository;
use rs_utcp::tag::tag_search::TagSearchStrategy;
use rs_utcp::{UtcpClient, UtcpClientInterface};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tracing::{error, info};
use std::path::PathBuf;

/// JSON-RPC 2.0 Request
#[derive(Debug, Clone, Serialize, Deserialize)]
struct JsonRpcRequest {
    jsonrpc: String,
    id: Option<Value>,
    method: String,
    params: Option<Value>,
}

/// JSON-RPC 2.0 Response
#[derive(Debug, Clone, Serialize, Deserialize)]
struct JsonRpcResponse {
    jsonrpc: String,
    id: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<JsonRpcError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct JsonRpcError {
    code: i32,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<Value>,
}

/// MCP Server Info
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ServerInfo {
    name: String,
    version: String,
}

/// MCP Server Capabilities
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ServerCapabilities {
    #[serde(skip_serializing_if = "Option::is_none")]
    tools: Option<Value>,
}

/// MCP Tool Schema
#[derive(Debug, Clone, Serialize, Deserialize)]
struct McpTool {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    description: Option<String>,
    #[serde(rename = "inputSchema")]
    input_schema: Value,
}

/// The main bridge struct
pub struct UtcpMcpBridge {
    utcp_client: Arc<UtcpClient>,
    utcp_code: Arc<CodeModeUtcp>,
}

impl UtcpMcpBridge {
    /// Create a new bridge
    pub async fn new(config: UtcpClientConfig) -> Result<Self> {
        let repo = Arc::new(InMemoryToolRepository::new());
        let strat = Arc::new(TagSearchStrategy::new(repo.clone(), 0.5));
        
        let utcp_client = Arc::new(
            UtcpClient::new(config, repo, strat).await.context("Failed to create UTCP client")?
        );

        let utcp_code = Arc::new(CodeModeUtcp::new(utcp_client.clone()));

        Ok(Self {
            utcp_client,
            utcp_code,
        })
    }

    /// Get MCP tool definitions
    fn get_tools() -> Vec<McpTool> {
        vec![
            McpTool {
                name: "utcp_call_tool".to_string(),
                description: Some("Call a UTCP tool by name with arguments".to_string()),
                input_schema: json!({
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the UTCP tool to call"
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Arguments to pass to the tool"
                        }
                    },
                    "required": ["tool_name"]
                }),
            },
            McpTool {
                name: "utcp_search_tools".to_string(),
                description: Some("Search for available UTCP tools".to_string()),
                input_schema: json!({
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }),
            },
            McpTool {
                name: "utcp_call_tool_stream".to_string(),
                description: Some("Call a UTCP tool with streaming response".to_string()),
                input_schema: json!({
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the UTCP tool to call"
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Arguments to pass to the tool"
                        }
                    },
                    "required": ["tool_name"]
                }),
            },
            McpTool {
                name: "utcp_run_code".to_string(),
                description: Some("Execute inline code via UTCP CodeMode engine".to_string()),
                input_schema: json!({
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Rhai script to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds",
                            "default": 3000
                        }
                    },
                    "required": ["code"]
                }),
            },
        ]
    }

    /// Handle a JSON-RPC request
    async fn handle_request(&self, request: JsonRpcRequest) -> JsonRpcResponse {
        let id = request.id.clone();

        match request.method.as_str() {
            "initialize" => {
                let result = json!({
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "utcp-bridge",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                });

                JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: Some(result),
                    error: None,
                }
            }
            "tools/list" => {
                let tools = Self::get_tools();
                JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: Some(json!({ "tools": tools })),
                    error: None,
                }
            }
            "tools/call" => self.handle_tool_call(id, request.params).await,
            _ => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32601,
                    message: format!("Method not found: {}", request.method),
                    data: None,
                }),
            },
        }
    }

    async fn handle_tool_call(&self, id: Option<Value>, params: Option<Value>) -> JsonRpcResponse {
        let params = match params {
            Some(p) => p,
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: "Invalid params".to_string(),
                        data: None,
                    }),
                }
            }
        };

        let tool_name = match params.get("name").and_then(|v| v.as_str()) {
            Some(name) => name,
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: "Missing tool name".to_string(),
                        data: None,
                    }),
                }
            }
        };

        let arguments = params
            .get("arguments")
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default();

        match tool_name {
            "utcp_call_tool" => self.handle_utcp_call_tool(id, arguments).await,
            "utcp_search_tools" => self.handle_utcp_search_tools(id, arguments).await,
            "utcp_call_tool_stream" => self.handle_utcp_call_tool_stream(id, arguments).await,
            "utcp_run_code" => self.handle_utcp_run_code(id, arguments).await,
            _ => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32602,
                    message: format!("Unknown tool: {}", tool_name),
                    data: None,
                }),
            },
        }
    }

    async fn handle_utcp_run_code(
        &self,
        id: Option<Value>,
        arguments: serde_json::Map<String, Value>,
    ) -> JsonRpcResponse {
        let code = match arguments.get("code").and_then(|v| v.as_str()) {
            Some(c) => c.to_string(),
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: "code is required".to_string(),
                        data: None,
                    }),
                }
            }
        };

        let timeout = arguments
            .get("timeout")
            .and_then(|v| v.as_u64())
            .map(|t| t);

        let args = CodeModeArgs {
            code,
            timeout,
        };

        match self.utcp_code.execute(args).await {
            Ok(result) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: Some(json!({
                    "content": [{
                        "type": "text",
                        "text": serde_json::to_string_pretty(&result.value).unwrap_or_else(|_| "{}".to_string())
                    }]
                })),
                error: None,
            },
            Err(e) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: format!("Error executing code: {}", e),
                    data: None,
                }),
            },
        }
    }

    async fn handle_utcp_call_tool(
        &self,
        id: Option<Value>,
        arguments: serde_json::Map<String, Value>,
    ) -> JsonRpcResponse {
        let tool_name = match arguments.get("tool_name").and_then(|v| v.as_str()) {
            Some(name) => name,
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: "tool_name is required".to_string(),
                        data: None,
                    }),
                }
            }
        };

        let tool_args = arguments
            .get("arguments")
            .and_then(|v| v.as_object())
            .map(|obj| {
                obj.iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect::<HashMap<String, Value>>()
            })
            .unwrap_or_default();

        match self.utcp_client.call_tool(tool_name, tool_args).await {
            Ok(result) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: Some(json!({
                    "content": [{
                        "type": "text",
                        "text": serde_json::to_string_pretty(&result).unwrap_or_else(|_| "{}".to_string())
                    }]
                })),
                error: None,
            },
            Err(e) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: format!("Error calling tool: {}", e),
                    data: None,
                }),
            },
        }
    }

    async fn handle_utcp_search_tools(
        &self,
        id: Option<Value>,
        arguments: serde_json::Map<String, Value>,
    ) -> JsonRpcResponse {
        let query = match arguments.get("query").and_then(|v| v.as_str()) {
            Some(q) => q,
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: "query is required".to_string(),
                        data: None,
                    }),
                }
            }
        };

        let limit = arguments
            .get("limit")
            .and_then(|v| v.as_u64())
            .unwrap_or(10) as usize;

        match self.utcp_client.search_tools(query, limit).await {
            Ok(tools) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: Some(json!({
                    "content": [{
                        "type": "text",
                        "text": serde_json::to_string_pretty(&tools).unwrap_or_else(|_| "[]".to_string())
                    }]
                })),
                error: None,
            },
            Err(e) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: format!("Error searching tools: {}", e),
                    data: None,
                }),
            },
        }
    }

    async fn handle_utcp_call_tool_stream(
        &self,
        id: Option<Value>,
        arguments: serde_json::Map<String, Value>,
    ) -> JsonRpcResponse {
        let tool_name = match arguments.get("tool_name").and_then(|v| v.as_str()) {
            Some(name) => name,
            None => {
                return JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: None,
                    error: Some(JsonRpcError {
                        code: -32602,
                        message: "tool_name is required".to_string(),
                        data: None,
                    }),
                }
            }
        };

        let tool_args = arguments
            .get("arguments")
            .and_then(|v| v.as_object())
            .map(|obj| {
                obj.iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect::<HashMap<String, Value>>()
            })
            .unwrap_or_default();

        match self.utcp_client.call_tool_stream(tool_name, tool_args).await {
            Ok(mut stream) => {
                let mut chunks = Vec::new();

                loop {
                    match stream.next().await {
                        Ok(Some(chunk)) => {
                            chunks.push(chunk);
                        }
                        Ok(None) => break,
                        Err(e) => {
                            return JsonRpcResponse {
                                jsonrpc: "2.0".to_string(),
                                id,
                                result: None,
                                error: Some(JsonRpcError {
                                    code: -32603,
                                    message: format!("Stream error: {}", e),
                                    data: None,
                                }),
                            };
                        }
                    }
                }

                JsonRpcResponse {
                    jsonrpc: "2.0".to_string(),
                    id,
                    result: Some(json!({
                        "content": [{
                            "type": "text",
                            "text": serde_json::to_string_pretty(&json!({ "chunks": chunks })).unwrap_or_else(|_| "{}".to_string())
                        }]
                    })),
                    error: None,
                }
            }
            Err(e) => JsonRpcResponse {
                jsonrpc: "2.0".to_string(),
                id,
                result: None,
                error: Some(JsonRpcError {
                    code: -32603,
                    message: format!("Error calling tool stream: {}", e),
                    data: None,
                }),
            },
        }
    }

    /// Run the MCP server over stdio
    pub async fn run(&self) -> Result<()> {
        let stdin = tokio::io::stdin();
        let mut stdout = tokio::io::stdout();
        let reader = BufReader::new(stdin);
        let mut lines = reader.lines();

        info!("UTCP MCP Bridge is ready on stdio");

        while let Some(line) = lines.next_line().await? {
            if line.trim().is_empty() {
                continue;
            }

            // Parse the JSON-RPC request
            let request: JsonRpcRequest = match serde_json::from_str(&line) {
                Ok(req) => req,
                Err(e) => {
                    error!("Failed to parse request: {}", e);
                    let error_response = JsonRpcResponse {
                        jsonrpc: "2.0".to_string(),
                        id: None,
                        result: None,
                        error: Some(JsonRpcError {
                            code: -32700,
                            message: format!("Parse error: {}", e),
                            data: None,
                        }),
                    };
                    let response_str = serde_json::to_string(&error_response)?;
                    stdout.write_all(response_str.as_bytes()).await?;
                    stdout.write_all(b"\n").await?;
                    stdout.flush().await?;
                    continue;
                }
            };

            // Handle the request
            let response = self.handle_request(request).await;

            // Send the response
            let response_str = serde_json::to_string(&response)?;
            stdout.write_all(response_str.as_bytes()).await?;
            stdout.write_all(b"\n").await?;
            stdout.flush().await?;
        }

        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with_writer(std::io::stderr) // Write logs to stderr to avoid interfering with stdio protocol
        .init();

    info!("Starting UTCP MCP Bridge...");

    // Create UTCP client config
    let providers_file = std::env::var("UTCP_PROVIDERS_FILE").ok();
    let mut config = UtcpClientConfig::default();
    if let Some(path) = providers_file {
        config.providers_file_path = Some(path.into());
    }

    // Create and run the bridge
    let bridge = UtcpMcpBridge::new(config).await?;
    bridge.run().await?;

    info!("Bridge shutting down");
    Ok(())
}
