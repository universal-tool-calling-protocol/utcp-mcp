#!/usr/bin/env node
// Wire up the local utcp-mcp bridge as an MCP server in Claude Code.
//
// Optionally overlays locally-built typescript-utcp packages (sibling repo)
// onto the bridge's node_modules so edits to @utcp/sdk, @utcp/http, etc. flow
// through after a rebuild + Claude Code restart.
//
// Strategy: dist-overlay, not `npm link`. Modern npm aliases `unlink <pkg>` to
// `uninstall --save`, which would silently strip dependencies from package.json.
//
// Usage:
//   node scripts/dev-register.mjs [--name <mcp-name>] [--config <path>] [--lib-dir <path>]
//
// Defaults:
//   --name     utcp-dev
//   --config   ./.utcp_config.json (relative to bridge package)
//   --lib-dir  ../typescript-utcp (sibling repo; pass "none" to skip overlay)

import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
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
const configPath = path.resolve(bridgeDir, getArg("--config", ".utcp_config.json"));
const libDirArg = getArg("--lib-dir", "../typescript-utcp");
const libDir = libDirArg === "none" ? null : path.resolve(bridgeDir, libDirArg);

if (!existsSync(configPath)) {
  console.error(`✗ Config file not found: ${configPath}`);
  console.error(`  Pass --config <path> or create one at ${configPath}.`);
  process.exit(1);
}

function run(cmd, cmdArgs, opts = {}) {
  console.log(`> ${cmd} ${cmdArgs.join(" ")}  (in ${opts.cwd ?? process.cwd()})`);
  const r = spawnSync(cmd, cmdArgs, { stdio: "inherit", shell: true, ...opts });
  if (r.status !== 0) {
    console.error(`✗ Command failed (exit ${r.status}).`);
    process.exit(r.status ?? 1);
  }
}

// Prefer bun (this repo's native package manager — bun.lock is checked in).
// Fall back to npm so contributors without bun installed still get a working
// devloop.
const bunAvailable = spawnSync("bun", ["--version"], { stdio: "ignore", shell: true }).status === 0;
const pm = bunAvailable ? "bun" : "npm";

// 1. Make sure the bridge has its registry deps installed.
if (!existsSync(path.join(bridgeDir, "node_modules"))) {
  run(pm, ["install"], { cwd: bridgeDir });
}

// 2. Optionally build typescript-utcp and overlay each package's dist into the
//    bridge's node_modules. typescript-utcp is a bun-managed monorepo with one
//    sub-package per directory under packages/.
if (libDir) {
  if (!existsSync(libDir) || !existsSync(path.join(libDir, "packages"))) {
    console.warn(`⚠ --lib-dir ${libDir} doesn't look like typescript-utcp; skipping overlay.`);
  } else {
    run(pm, ["run", "build"], { cwd: libDir });

    const pkgsDir = path.join(libDir, "packages");
    const subdirs = readdirSync(pkgsDir, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name);

    let overlayCount = 0;
    for (const sub of subdirs) {
      const pkgJsonPath = path.join(pkgsDir, sub, "package.json");
      if (!existsSync(pkgJsonPath)) continue;
      const pkgName = JSON.parse(readFileSync(pkgJsonPath, "utf8")).name;
      if (!pkgName) continue;

      const targetPkgDir = path.join(bridgeDir, "node_modules", ...pkgName.split("/"));
      const localDist = path.join(pkgsDir, sub, "dist");
      const targetDist = path.join(targetPkgDir, "dist");

      if (!existsSync(targetPkgDir)) continue; // Bridge doesn't depend on this package.
      if (!existsSync(localDist)) {
        console.warn(`⚠ ${pkgName}: local dist missing at ${localDist}; skipping.`);
        continue;
      }

      console.log(`> overlay  ${localDist}  ->  ${targetDist}`);
      rmSync(targetDist, { recursive: true, force: true });
      mkdirSync(targetDist, { recursive: true });
      cpSync(localDist, targetDist, { recursive: true });
      overlayCount++;
    }
    console.log(`  Overlaid ${overlayCount} package(s) from ${libDir}.`);
  }
} else {
  console.log("• Skipping typescript-utcp overlay (--lib-dir none).");
}

// 3. Build the bridge against the (possibly overlaid) deps.
run(pm, ["run", "build"], { cwd: bridgeDir });

// 4. Register with Claude Code (user scope). Removes a stale entry first so
//    the command is idempotent.
spawnSync("claude", ["mcp", "remove", name, "--scope", "user"], {
  stdio: "ignore",
  shell: true,
});

const distEntry = path.join(bridgeDir, "dist", "index.js").replace(/\\/g, "/");
const cfg = configPath.replace(/\\/g, "/");
const mcpJson = JSON.stringify({
  type: "stdio",
  command: "node",
  args: [distEntry],
  env: { UTCP_CONFIG_FILE: cfg },
});

const isWindows = os.platform() === "win32";
const quotedJson = isWindows
  ? `"${mcpJson.replace(/"/g, '\\"')}"`
  : `'${mcpJson.replace(/'/g, `'\\''`)}'`;

const cmdLine = `claude mcp add-json --scope user ${name} ${quotedJson}`;
console.log(`> ${cmdLine}`);
const r = spawnSync(cmdLine, { stdio: "inherit", shell: true });
if (r.status !== 0) {
  console.error(`✗ claude mcp add-json failed (exit ${r.status}).`);
  process.exit(r.status ?? 1);
}

console.log(`\n✓ Registered MCP server '${name}' (user scope).`);
console.log(`  Entry:  ${distEntry}`);
console.log(`  Config: ${cfg}`);
console.log(`\nRestart Claude Code to load the server. After editing the bridge or any`);
console.log(`typescript-utcp package, re-run this script then restart Claude Code.`);
