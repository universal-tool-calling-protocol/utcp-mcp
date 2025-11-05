#!/usr/bin/env node

// UTCP-MCP Bridge Entry Point
// This is the main entry point for the npx @utcp/mcp-bridge command

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import path from "path";
import { promises as fs } from "fs";
import { parse as parseDotEnv } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

import "@utcp/http";
import "@utcp/text";
import "@utcp/mcp";
import "@utcp/cli";
import "@utcp/dotenv-loader"
import "@utcp/file"

import {
    UtcpClient,
    CallTemplateSchema,
    InMemConcurrentToolRepository,
    TagSearchStrategy,
    DefaultVariableSubstitutor,
    ensureCorePluginsInitialized,
    UtcpClientConfigSerializer
} from "@utcp/sdk";
import type { UtcpClientConfig } from "@utcp/sdk";

// Get current file directory for Node.js ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

ensureCorePluginsInitialized();

let utcpClient: UtcpClient | null = null;

async function main() {
    setupMcpTools();
    utcpClient = await initializeUtcpClient();
    const transport = new StdioServerTransport();
    await mcp.connect(transport);
}

const mcp = new McpServer({
    name: "UTCP-Client-MCP-Bridge",
    version: "1.0.0",
});

function setupMcpTools() {
    mcp.registerTool("register_manual", {
        title: "Register a UTCP Manual",
        description: "Registers a new tool provider by providing its call template.",
        inputSchema: { manual_call_template: CallTemplateSchema.describe("The call template for the UTCP Manual endpoint.") },
    }, async (input) => {
        const client = await initializeUtcpClient();
        try {
            const result = await client.registerManual(input.manual_call_template as any);
            return { content: [{ type: "text", text: JSON.stringify(result) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });

    mcp.registerTool("deregister_manual", {
        title: "Deregister a UTCP Manual",
        description: "Deregisters a tool provider from the UTCP client.",
        inputSchema: { manual_name: z.string().describe("The name of the manual to deregister.") },
    }, async (input) => {
        const client = await initializeUtcpClient();
        try {
            const success = await client.deregisterManual(input.manual_name);
            const message = success ? `Manual '${input.manual_name}' deregistered.` : `Manual '${input.manual_name}' not found.`;
            return { content: [{ type: "text", text: JSON.stringify({ success, message }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });

    mcp.registerTool("call_tool", {
        title: "Call a UTCP Tool",
        description: "Calls a registered tool by its full namespaced name.",
        inputSchema: {
            tool_name: z.string().describe("The full name of the tool to call."),
            arguments: z.record(z.string(), z.any()).describe("A JSON object of arguments."),
        },
    }, async (input) => {
        const client = await initializeUtcpClient();
        try {
            const result = await client.callTool(input.tool_name, input.arguments);
            return { content: [{ type: "text", text: JSON.stringify({ success: true, tool_name: input.tool_name, result }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });

    mcp.registerTool("search_tools", {
        title: "Search for UTCP Tools",
        description: "Searches for relevant tools based on a task description.",
        inputSchema: {
            task_description: z.string().describe("A natural language description of the task."),
            limit: z.number().optional().default(10),
        },
    }, async (input) => {
        const client = await initializeUtcpClient();
        try {
            const tools = await client.searchTools(input.task_description, input.limit);
            const simplified = tools.map(t => ({ name: t.name, description: t.description, input_schema: t.inputs }));
            return { content: [{ type: "text", text: JSON.stringify({ tools: simplified }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });

    mcp.registerTool("list_tools", {
        title: "List All Registered UTCP Tools",
        description: "Returns a list of all tool names currently registered.",
        inputSchema: {},
    }, async () => {
        const client = await initializeUtcpClient();
        try {
            const tools = await client.config.tool_repository.getTools();
            const toolNames = tools.map(t => t.name);
            return { content: [{ type: "text", text: JSON.stringify({ tools: toolNames }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });

    mcp.registerTool("get_required_keys_for_tool", {
        title: "Get Required Variables for Tool",
        description: "Get required environment variables for a registered tool.",
        inputSchema: {
            tool_name: z.string().describe("Name of the tool to get required variables for."),
        },
    }, async (input) => {
        const client = await initializeUtcpClient();
        try {
            const variables = await client.getRequiredVariablesForRegisteredTool(input.tool_name);
            return { content: [{ type: "text", text: JSON.stringify({ success: true, tool_name: input.tool_name, required_variables: variables }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, tool_name: input.tool_name, error: e.message }) }] };
        }
    });

    mcp.registerTool("tool_info", {
        title: "Get Tool Information",
        description: "Get complete information about a specific tool including all details.",
        inputSchema: {
            tool_name: z.string().describe("Name of the tool to get complete information for."),
        },
    }, async (input) => {
        const client = await initializeUtcpClient();
        try {
            const tool = await client.config.tool_repository.getTool(input.tool_name);
            if (!tool) {
                return { content: [{ type: "text", text: JSON.stringify({ success: false, error: `Tool '${input.tool_name}' not found` }) }] };
            }
            return { content: [{ type: "text", text: JSON.stringify({ success: true, tool: tool }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });
}

async function initializeUtcpClient(): Promise<UtcpClient> {
    if (utcpClient) {
        return utcpClient as UtcpClient;
    }

    // Look for config file: 1) Environment variable, 2) Current working directory, 3) Package directory
    const cwd = process.cwd();
    const packageDir = __dirname;
    
    let configPath: string;
    let scriptDir: string;
    
    // Check if UTCP_CONFIG_FILE environment variable is set
    if (process.env.UTCP_CONFIG_FILE) {
        configPath = path.resolve(process.env.UTCP_CONFIG_FILE);
        scriptDir = path.dirname(configPath);
        
        try {
            await fs.access(configPath);
        } catch {
            console.warn(`UTCP config file specified in UTCP_CONFIG_FILE not found: ${configPath}`);
        }
    } else {
        // Fall back to current working directory first, then package directory
        configPath = path.resolve(cwd, '.utcp_config.json');
        scriptDir = cwd;
        
        try {
            await fs.access(configPath);
        } catch {
            configPath = path.resolve(packageDir, '.utcp_config.json');
            scriptDir = packageDir;
        }
    }

    let rawConfig: any = {};
    try {
        const configFileContent = await fs.readFile(configPath, 'utf-8');
        rawConfig = JSON.parse(configFileContent);
    } catch (e: any) {
        if (e.code !== 'ENOENT') {
            console.warn(`Could not read or parse .utcp_config.json. Error: ${e.message}`);
        }
    }

    const clientConfig = new UtcpClientConfigSerializer().validateDict(rawConfig);

    const newClient = await UtcpClient.create(scriptDir, clientConfig);

    utcpClient = newClient;
    return utcpClient as UtcpClient;
}

main().catch(err => {
    console.error("Failed to start UTCP-MCP Bridge:", err);
    process.exit(1);
});
