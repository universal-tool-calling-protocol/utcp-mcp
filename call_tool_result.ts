import { ContentBlock, ContentBlockSchema } from "@modelcontextprotocol/sdk/types.js";

const isContentBlock = (value: unknown): value is ContentBlock => ContentBlockSchema.safeParse(value).success;

/**
 * Builds the call_tool response for a UTCP tool result.
 *
 * MCP content blocks (image, resource, etc.) are passed through natively. Everything else
 * goes into the JSON text block as `result`, keeping its shape: an array result stays an
 * array, even when it is empty or holds a single item.
 */
export function toCallToolContent(toolName: string, result: unknown): ContentBlock[] {
    const items: unknown[] = Array.isArray(result) ? result : [result];
    const content: ContentBlock[] = [];
    const plain: unknown[] = [];
    for (const item of items) {
        if (isContentBlock(item)) {
            content.push(item);
        } else {
            plain.push(item);
        }
    }
    const onlyContentBlocks = items.length > 0 && plain.length === 0;
    const value = Array.isArray(result) ? (onlyContentBlocks ? undefined : plain) : plain[0];
    content.push({
        type: "text",
        text: JSON.stringify({ success: true, tool_name: toolName, result: value }),
    });
    return content;
}
