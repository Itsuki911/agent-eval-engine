#!/usr/bin/env node

const { spawn } = require("node:child_process");
const path = require("node:path");

const bundleRoot = path.resolve(__dirname, "..");
const projectRoot = path.join(bundleRoot, "project");
const composeEnvironment = {
  ...process.env,
  POSTGRES_PORT: process.env.AGENT_EVAL_POSTGRES_PORT || "15432",
};
const pendingInput = [];
let stdinEnded = false;

process.stdin.on("data", (chunk) => pendingInput.push(chunk));
process.stdin.on("end", () => {
  stdinEnded = true;
});

function runDocker(argumentsList, stdinMode) {
  return spawn("docker", argumentsList, {
    cwd: projectRoot,
    env: composeEnvironment,
    stdio: [stdinMode, "pipe", "pipe"],
  });
}

function forwardLogs(processHandle) {
  processHandle.stdout.pipe(process.stderr);
  processHandle.stderr.pipe(process.stderr);
}

function waitForExit(processHandle, commandName) {
  return new Promise((resolve, reject) => {
    processHandle.once("error", (error) => {
      reject(new Error(`${commandName} を起動できません: ${error.message}`));
    });
    processHandle.once("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${commandName} が終了しました: exit_code=${code}`));
    });
  });
}

async function startMcpContainer() {
  const processHandle = runDocker(
    ["compose", "--project-name", "agent-eval-mcpb", "--project-directory", projectRoot, "--profile", "mcp", "up", "-d", "mcp"],
    "ignore",
  );
  forwardLogs(processHandle);
  await waitForExit(processHandle, "docker compose up");
}

async function main() {
  try {
    await startMcpContainer();
    const processHandle = runDocker(
      [
        "compose",
        "--project-name",
        "agent-eval-mcpb",
        "--project-directory",
        projectRoot,
        "exec",
        "-T",
        "mcp",
        "mcp",
        "run",
        "apps/mcp/server.py:mcp",
        "--transport",
        "stdio",
      ],
      "pipe",
    );
    for (const chunk of pendingInput) {
      processHandle.stdin.write(chunk);
    }
    process.stdin.pipe(processHandle.stdin);
    if (stdinEnded) {
      processHandle.stdin.end();
    }
    processHandle.stdout.pipe(process.stdout);
    processHandle.stderr.pipe(process.stderr);
    await waitForExit(processHandle, "docker compose exec");
  } catch (error) {
    process.stderr.write(`Agent Eval MCP を起動できません: ${error.message}\n`);
    process.exitCode = 1;
  }
}

main();
