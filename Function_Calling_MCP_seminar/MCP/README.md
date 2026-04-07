# GigaChat Agent + MCP Server Demo

This folder contains a practical MCP demo for GigaChat agents.

Available entry points:
- `agent.py` — local MCP client via `stdio`; starts and uses `math_server.py` without a separate server process.
- `agent_http.py` — HTTP/SSE MCP client; requires the MCP server running in SSE mode.
- `mcp_react_agent.py` — interactive ReAct agent that loads MCP servers from `mcp_config.json`.

Core MCP server:
- `math_server.py` exposes tools:
  - `add(a, b)`
  - `multiply(a, b)`
  - `find_preson(name)`

## What is MCP?

Model Context Protocol (MCP) is an open protocol that standardizes how applications and LLMs exchange context and tool definitions.

Benefits:
- reusable tool integrations,
- portability across model providers,
- cleaner architecture for agent-tool ecosystems.

Read more: https://modelcontextprotocol.io/introduction

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

This local file forwards to the repository-level `requirements_mcp.txt`, so from the repo root you can also run:

```bash
pip install -r requirements_mcp.txt
```

Create `.env` file (you can copy `.env.example`) and set credentials:

```bash
GIGACHAT_CREDENTIALS=<your_auth_token>
```

`API_KEY` is also supported by the scripts as a fallback:

```bash
API_KEY=<your_auth_token>
```

## Quick Start

### 1) Local stdio client

```bash
python agent.py
```

### 2) HTTP/SSE client

Run server first:

```bash
python math_server.py sse
```

Then in another terminal:

```bash
python agent_http.py
```

### 3) Interactive MCP ReAct agent

Configure servers in `mcp_config.json`, then run:

```bash
python mcp_react_agent.py
```

## Example prompts

- `What is (3 + 5) * 12?`
- `How old is John Doe?`
- `Multiply that age by 3.14159`
