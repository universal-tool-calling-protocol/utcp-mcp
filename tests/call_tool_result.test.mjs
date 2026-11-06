import { test } from "node:test";
import assert from "node:assert/strict";
import { toCallToolContent } from "../dist/call_tool_result.js";

const resultOf = (content) => JSON.parse(content.at(-1).text).result;
const image = { type: "image", data: "aGk=", mimeType: "image/png" };

test("an empty array result stays an empty array", () => {
    assert.deepEqual(resultOf(toCallToolContent("m.t", [])), []);
});

test("a single-item array result stays an array", () => {
    assert.deepEqual(resultOf(toCallToolContent("m.t", [{ id: 1 }])), [{ id: 1 }]);
});

test("a multi-item array result stays an array", () => {
    assert.deepEqual(resultOf(toCallToolContent("m.t", [1, 2])), [1, 2]);
});

test("a non-array result is returned as is", () => {
    assert.deepEqual(resultOf(toCallToolContent("m.t", { a: 1 })), { a: 1 });
    assert.equal(resultOf(toCallToolContent("m.t", "text")), "text");
});

test("content blocks pass through natively", () => {
    const content = toCallToolContent("m.t", [image, { id: 1 }]);
    assert.deepEqual(content[0], image);
    assert.deepEqual(resultOf(content), [{ id: 1 }]);
});

test("a result made only of content blocks has no JSON result", () => {
    const content = toCallToolContent("m.t", [image]);
    assert.deepEqual(content[0], image);
    assert.equal(resultOf(content), undefined);
    assert.equal(resultOf(toCallToolContent("m.t", image)), undefined);
});
