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

if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
  console.error(`✗ Invalid --name '${name}'. Must match [a-zA-Z0-9_-]+.`);
  process.exit(1);
}

let hadFailure = false;

// `claude mcp remove` is allowed to fail (entry may already be gone) — log
// but don't abort the rest of the cleanup. Other steps must succeed for the
// success message to be honest.
function tryRun(cmd, cmdArgs, opts = {}) {
  console.log(`> ${cmd} ${cmdArgs.join(" ")}  (in ${opts.cwd ?? process.cwd()})`);
  const r = spawnSync(cmd, cmdArgs, { stdio: "inherit", shell: true, ...opts });
  if (r.status !== 0) {
    console.warn(`⚠ ${cmd} ${cmdArgs[0] ?? ""} exited ${r.status}; continuing.`);
  }
}

function mustRun(cmd, cmdArgs, opts = {}) {
  console.log(`> ${cmd} ${cmdArgs.join(" ")}  (in ${opts.cwd ?? process.cwd()})`);
  const r = spawnSync(cmd, cmdArgs, { stdio: "inherit", shell: true, ...opts });
  if (r.status !== 0) {
    console.error(`✗ ${cmd} ${cmdArgs[0] ?? ""} failed (exit ${r.status}).`);
    hadFailure = true;
  }
}

tryRun("claude", ["mcp", "remove", name, "--scope", "user"]);

// Prefer bun to match this repo's native package manager (bun.lock is checked
// in); fall back to npm. Reinstall from the registry to undo any dist-overlay.
const bunAvailable = spawnSync("bun", ["--version"], { stdio: "ignore", shell: true }).status === 0;
if (bunAvailable) {
  mustRun("bun", ["install"], { cwd: bridgeDir });
} else {
  // npm install --no-save keeps package.json untouched.
  mustRun("npm", ["install", "--no-save"], { cwd: bridgeDir });
}

if (hadFailure) {
  console.error(`\n✗ Unregister completed with errors. Registry node_modules may not have been restored — re-run the package manager install manually before publishing.`);
  process.exit(1);
}

console.log(`\n✓ Unregistered '${name}' and restored registry node_modules.`);
console.log(`  Restart Claude Code so it stops trying to spawn the dev bridge.`);
