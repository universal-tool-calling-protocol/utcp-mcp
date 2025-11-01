// utcp-client-mcp.ts (TypeScript MCP-UTCP Bridge Server)

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import path from "path";
import { promises as fs } from "fs";
import { parse as parseDotEnv } from 'dotenv';

import {
    UtcpClient,
    CallTemplateSchema,
    InMemConcurrentToolRepository,
    TagSearchStrategy,
    DefaultVariableSubstitutor,
    ensureCorePluginsInitialized
} from "@utcp/sdk";
import type { UtcpClientConfig } from "@utcp/sdk";

ensureCorePluginsInitialized();

let utcpClient: UtcpClient | null = null;

async function main() {
    console.log("Initializing UTCP-MCP Bridge...");
    setupMcpTools();
    utcpClient = await initializeUtcpClient();

    const bridgeScriptPath = path.resolve(import.meta.dir, import.meta.file);
    const connectionConfig = {
        mcpServers: {
            "typescript-utcp-bridge": {
                command: "bun",
                args: ["run", bridgeScriptPath],
            }
        }
    };

    console.log("\n✅ Bridge is ready. To connect, use this configuration in your MCP client's config file:");
    console.log("================================ MCP CONFIG ================================");
    console.log(JSON.stringify(connectionConfig, null, 2));
    console.log("==========================================================================");

    console.log("\nStarting MCP server on stdio...");
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
        description: "Returns a list of all tools currently registered.",
        inputSchema: {},
    }, async () => {
        const client = await initializeUtcpClient();
        try {
            const tools = await client.config.tool_repository.getTools();
            const toolInfo = tools.map(t => ({ name: t.name, description: t.description }));
            return { content: [{ type: "text", text: JSON.stringify({ tools: toolInfo }) }] };
        } catch (e: any) {
            return { content: [{ type: "text", text: JSON.stringify({ success: false, error: e.message }) }] };
        }
    });
}

async function initializeUtcpClient(): Promise<UtcpClient> {
    if (utcpClient) {
        return utcpClient as UtcpClient;
    }

    const scriptDir = path.resolve(import.meta.dir);
    const configPath = path.resolve(scriptDir, '.utcp_config.json');
    console.log(`Searching for UTCP config file at: ${configPath}`);

    let rawConfig: any = {};
    try {
        const configFileContent = await fs.readFile(configPath, 'utf-8');
        rawConfig = JSON.parse(configFileContent);
        console.log("Loaded UTCP client configuration from .utcp_config.json");
    } catch (e: any) {
        if (e.code !== 'ENOENT') {
            console.warn(`Could not read or parse .utcp_config.json. Error: ${e.message}`);
        }
        console.log("No valid .utcp_config.json found. Initializing with default config.");
    }

    const toolRepository = new InMemConcurrentToolRepository();
    const searchStrategy = new TagSearchStrategy({
        tool_search_strategy_type: 'tag_and_description_word_match',
        ...rawConfig.tool_search_strategy
    });
    const variableSubstitutor = new DefaultVariableSubstitutor();

    const loadedVariables: Record<string, string> = {};
    if (rawConfig.load_variables_from) {
        for (const loaderConfig of rawConfig.load_variables_from) {
            if (loaderConfig.variable_loader_type === 'dotenv' && loaderConfig.env_file_path) {
                try {
                    const envPath = path.resolve(scriptDir, loaderConfig.env_file_path);
                    const envContent = await fs.readFile(envPath, 'utf-8');
                    Object.assign(loadedVariables, parseDotEnv(envContent));
                    console.log(`Successfully loaded variables from ${envPath}`);
                } catch (e: any) {
                    console.warn(`Could not load .env file from '${loaderConfig.env_file_path}': ${e.message}`);
                }
            }
        }
    }

    const finalVariables = { ...loadedVariables, ...(rawConfig.variables || {}) };

    const clientConfig: UtcpClientConfig = {
        variables: finalVariables,
        load_variables_from: [],
        tool_repository: toolRepository,
        tool_search_strategy: searchStrategy,
        post_processing: rawConfig.post_processing || [],
        manual_call_templates: [],
    };

    const newClient = new (UtcpClient as any)(clientConfig, variableSubstitutor, scriptDir);

    if (rawConfig.manual_call_templates && Array.isArray(rawConfig.manual_call_templates)) {
        console.log(`Registering ${rawConfig.manual_call_templates.length} initial manuals from config...`);
        for (const manualTemplate of rawConfig.manual_call_templates) {
            try {
                if (!manualTemplate.name) {
                    manualTemplate.name = manualTemplate.call_template_type || 'unnamed_manual';
                }
                await newClient.registerManual(manualTemplate);
            } catch (e: any) {
                console.error(`Failed to register initial manual '${manualTemplate.name}': ${e.message}`);
            }
        }
    }

    console.log("UTCP Client manually initialized successfully.");
    utcpClient = newClient;
    return utcpClient as UtcpClient;
}

main().catch(err => {
    console.error("Failed to start UTCP-MCP Bridge:", err);
    process.exit(1);
});