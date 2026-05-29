import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultOutput = resolve(root, "..", ".codex_tmp", "studio-desktop-check.png");
const defaultOutputDir = resolve(root, "..", ".codex_tmp", "studio-desktop-checks");
const baseUrl = process.env.STUDIO_CHECK_URL || "http://127.0.0.1:5173";
const output = resolve(process.env.STUDIO_CHECK_OUTPUT || defaultOutput);
const outputDir = resolve(process.env.STUDIO_CHECK_OUTPUT_DIR || defaultOutputDir);
const viewport = process.env.STUDIO_CHECK_VIEWPORT || "1440,1000";
const [viewportWidth, viewportHeight] = viewport.split(",").map((value) => Number.parseInt(value, 10));
const requestedScenarios =
  process.env.STUDIO_CHECK_SCENARIOS ||
  "empty,loaded,running,terminal,repair,trigger,logs";

const candidates = [
  process.env.STUDIO_CHECK_BROWSER,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
].filter(Boolean);

const browser = candidates.find((candidate) => candidate && existsSync(candidate));

const scenarioDefinitions = {
  empty: {
    label: "empty project",
    view: "novel",
    fixture: "empty",
    expected: "小说总结"
  },
  loaded: {
    label: "loaded project",
    view: "novel",
    fixture: "loaded",
    expected: "visual-loaded-project"
  },
  running: {
    label: "running task",
    view: "novel",
    fixture: "running",
    expected: "正在生成大总结草稿"
  },
  terminal: {
    label: "terminal task",
    view: "article",
    fixture: "terminal",
    expected: "exports/article/final.md"
  },
  repair: {
    label: "repair warning",
    view: "novel",
    fixture: "repair-warning",
    expected: "项目修复需要确认覆盖策略"
  },
  trigger: {
    label: "trigger scan report review",
    view: "trigger_scan",
    fixture: "trigger-report",
    expected: "雷点扫描"
  },
  logs: {
    label: "log-heavy session",
    view: "apis",
    fixture: "log-heavy",
    expected: "视觉检查日志 48"
  }
};

if (!browser) {
  console.error("No supported browser found. Set STUDIO_CHECK_BROWSER to Chrome or Edge.");
  process.exit(1);
}

if (!Number.isFinite(viewportWidth) || !Number.isFinite(viewportHeight)) {
  console.error("STUDIO_CHECK_VIEWPORT must be formatted as width,height.");
  process.exit(1);
}

const scenarios = requestedScenarios
  .split(",")
  .map((name) => name.trim())
  .filter(Boolean)
  .map((name) => {
    const scenario = scenarioDefinitions[name];
    if (!scenario) {
      console.error(`Unknown desktop visual check scenario: ${name}`);
      process.exit(1);
    }
    return { name, ...scenario };
  });

function wait(ms) {
  return new Promise((resolveWait) => {
    setTimeout(resolveWait, ms);
  });
}

function getFreePort() {
  return new Promise((resolvePort, rejectPort) => {
    const server = createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      server.close(() => {
        if (address && typeof address === "object") {
          resolvePort(address.port);
        } else {
          rejectPort(new Error("Unable to allocate a local debugging port."));
        }
      });
    });
    server.on("error", rejectPort);
  });
}

async function fetchJson(url, attempts = 50) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.json();
      }
      lastError = new Error(`${response.status} ${response.statusText}`);
    } catch (error) {
      lastError = error;
    }
    await wait(120);
  }
  throw lastError ?? new Error(`Unable to fetch ${url}`);
}

function scenarioUrl(scenario) {
  const url = new URL(baseUrl);
  url.searchParams.set("view", scenario.view);
  if (scenario.fixture) {
    url.searchParams.set("studioVisualFixture", scenario.fixture);
  }
  return url.toString();
}

class CdpSession {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 0;
    this.pending = new Map();
    this.eventWaiters = new Map();
  }

  connect() {
    return new Promise((resolveConnect, rejectConnect) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.addEventListener("open", () => resolveConnect());
      this.ws.addEventListener("error", rejectConnect);
      this.ws.addEventListener("message", (event) => this.handleMessage(event));
      this.ws.addEventListener("close", () => {
        for (const { reject } of this.pending.values()) {
          reject(new Error("Chrome DevTools connection closed."));
        }
        this.pending.clear();
      });
    });
  }

  handleMessage(event) {
    const message = JSON.parse(event.data);
    if (message.id && this.pending.has(message.id)) {
      const { resolveSend, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) {
        reject(new Error(message.error.message));
      } else {
        resolveSend(message.result ?? {});
      }
      return;
    }

    if (message.method && this.eventWaiters.has(message.method)) {
      const waiters = this.eventWaiters.get(message.method);
      this.eventWaiters.delete(message.method);
      waiters.forEach((resolveWaiter) => resolveWaiter(message.params ?? {}));
    }
  }

  send(method, params = {}) {
    const id = (this.id += 1);
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolveSend, reject) => {
      this.pending.set(id, { resolveSend, reject });
    });
  }

  waitForEvent(method, timeoutMs = 10000) {
    return new Promise((resolveEvent, rejectEvent) => {
      const timer = setTimeout(() => {
        rejectEvent(new Error(`Timed out waiting for ${method}`));
      }, timeoutMs);
      const waiters = this.eventWaiters.get(method) ?? [];
      waiters.push((params) => {
        clearTimeout(timer);
        resolveEvent(params);
      });
      this.eventWaiters.set(method, waiters);
    });
  }

  close() {
    this.ws?.close();
  }
}

async function captureScenario(cdp, scenario) {
  const url = scenarioUrl(scenario);
  const screenshotPath = join(outputDir, `${scenario.name}.png`);
  const loadEvent = cdp.waitForEvent("Page.loadEventFired", 15000);

  await cdp.send("Page.navigate", { url });
  await loadEvent;
  await cdp.send("Runtime.evaluate", {
    awaitPromise: true,
    expression: "document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()"
  });
  await wait(1800);

  const textResult = await cdp.send("Runtime.evaluate", {
    expression: "document.body.innerText",
    returnByValue: true
  });
  const bodyText = String(textResult.result?.value ?? "");
  if (!bodyText.includes(scenario.expected)) {
    throw new Error(`Scenario '${scenario.name}' did not render expected text: ${scenario.expected}`);
  }

  const screenshot = await cdp.send("Page.captureScreenshot", {
    captureBeyondViewport: false,
    format: "png"
  });
  writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
  return screenshotPath;
}

async function main() {
  mkdirSync(dirname(output), { recursive: true });
  mkdirSync(outputDir, { recursive: true });

  const port = await getFreePort();
  const userDataDir = mkdtempSync(join(tmpdir(), "studio-desktop-check-"));
  const browserProcess = spawn(
    browser,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${userDataDir}`,
      `--window-size=${viewportWidth},${viewportHeight}`,
      "about:blank"
    ],
    { stdio: ["ignore", "ignore", "pipe"] }
  );

  browserProcess.stderr.on("data", (chunk) => {
    const text = String(chunk);
    if (!text.includes("QQBrowser user data path not found")) {
      process.stderr.write(text);
    }
  });

  try {
    await fetchJson(`http://127.0.0.1:${port}/json/version`);
    const targets = await fetchJson(`http://127.0.0.1:${port}/json/list`);
    const pageTarget = targets.find((target) => target.type === "page");
    if (!pageTarget?.webSocketDebuggerUrl) {
      throw new Error("Unable to find a Chrome page target for screenshot capture.");
    }

    const cdp = new CdpSession(pageTarget.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: viewportWidth,
      height: viewportHeight,
      deviceScaleFactor: 1,
      mobile: false
    });

    const outputs = [];
    for (const scenario of scenarios) {
      const screenshotPath = await captureScenario(cdp, scenario);
      outputs.push({ scenario, screenshotPath });
      console.log(`Desktop visual check [${scenario.label}]: ${screenshotPath}`);
    }
    cdp.close();

    if (outputs.length > 0) {
      copyFileSync(outputs[0].screenshotPath, output);
      console.log(`Desktop visual check screenshot: ${output}`);
    }
  } finally {
    browserProcess.kill();
    await wait(300);
    try {
      rmSync(userDataDir, { recursive: true, force: true });
    } catch (error) {
      console.warn(`Unable to remove temporary browser profile: ${userDataDir}`);
    }
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
