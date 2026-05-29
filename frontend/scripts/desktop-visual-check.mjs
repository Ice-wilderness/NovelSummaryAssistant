import { existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultOutput = resolve(root, "..", ".codex_tmp", "studio-desktop-check.png");
const url = process.env.STUDIO_CHECK_URL || "http://127.0.0.1:5173";
const output = resolve(process.env.STUDIO_CHECK_OUTPUT || defaultOutput);
const viewport = process.env.STUDIO_CHECK_VIEWPORT || "1440,1000";

const candidates = [
  process.env.STUDIO_CHECK_BROWSER,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
].filter(Boolean);

const browser = candidates.find((candidate) => candidate && existsSync(candidate));

if (!browser) {
  console.error("No supported browser found. Set STUDIO_CHECK_BROWSER to Chrome or Edge.");
  process.exit(1);
}

mkdirSync(dirname(output), { recursive: true });

const result = spawnSync(
  browser,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    `--window-size=${viewport}`,
    "--virtual-time-budget=2500",
    `--screenshot=${output}`,
    url
  ],
  { stdio: "inherit" }
);

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

console.log(`Desktop visual check screenshot: ${output}`);
