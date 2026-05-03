#!/usr/bin/env node
// Tear down what dev-register.mjs set up: deregister the Claude Code MCP server
// and restore the registry versions of any typescript-utcp packages whose dist
// dirs were overlaid in node_modules.
//
// Usage:
//   node scripts/dev-unregister.mjs [--name <mcp-name>]

import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const bridgeDir = path.resolve(__dirname, "..");

const args = process.argv.slice(2);
const getArg = (flag, fallback) => {
  const i = args.indexOf(flag);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};

const name = getArg("--name", "utcp-dev");

function run(cmd, cmdArgs, opts = {}) {
  console.log(`> ${cmd} ${cmdArgs.join(" ")}  (in ${opts.cwd ?? process.cwd()})`);
  spawnSync(cmd, cmdArgs, { stdio: "inherit", shell: true, ...opts });
}

run("claude", ["mcp", "remove", name, "--scope", "user"]);

// Prefer bun to match this repo's native package manager (bun.lock is checked
// in); fall back to npm. Reinstall from the registry to undo any dist-overlay.
const bunAvailable = spawnSync("bun", ["--version"], { stdio: "ignore", shell: true }).status === 0;
if (bunAvailable) {
  run("bun", ["install"], { cwd: bridgeDir });
} else {
  // npm install --no-save keeps package.json untouched.
  run("npm", ["install", "--no-save"], { cwd: bridgeDir });
}

console.log(`\n✓ Unregistered '${name}' and restored registry node_modules.`);
console.log(`  Restart Claude Code so it stops trying to spawn the dev bridge.`);
