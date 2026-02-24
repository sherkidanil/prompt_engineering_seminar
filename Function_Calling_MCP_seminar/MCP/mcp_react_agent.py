"""MCP ReAct agent with memory support."""
import asyncio
import json
import os

import httpx
from dotenv import load_dotenv, find_dotenv
from langchain_gigachat import GigaChat
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from rich import print

# Load environment variables
load_dotenv(find_dotenv(usecwd=True))


def _resolve_gigachat_credentials() -> str:
    credentials = os.getenv("GIGACHAT_CREDENTIALS") or os.getenv("API_KEY")
    if not credentials:
        raise ValueError(
            "Set GIGACHAT_CREDENTIALS or API_KEY in your .env before running mcp_react_agent.py"
        )
    return credentials


def _httpx_client_factory(
    headers: dict | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    # trust_env=False avoids system proxy interception for local SSE URLs.
    kwargs: dict = {
        "follow_redirects": True,
        "trust_env": False,
        "timeout": timeout or httpx.Timeout(30.0, read=300.0),
    }
    if headers is not None:
        kwargs["headers"] = headers
    if auth is not None:
        kwargs["auth"] = auth
    return httpx.AsyncClient(**kwargs)

# Initialize GigaChat with optimized settings
GIGA_CHAT = GigaChat(
    model="GigaChat-2-Max",
    credentials=_resolve_gigachat_credentials(),
    verify_ssl_certs=False,
    streaming=False,
    max_tokens=8000,
)

# Load MCP configuration
with open("mcp_config.json", "r", encoding="utf-8") as f:
    MCP_CONFIG = json.load(f)

for cfg in MCP_CONFIG.values():
    if cfg.get("transport") == "sse":
        cfg["httpx_client_factory"] = _httpx_client_factory


async def run_interactive_session(agent):
    """Run interactive chat session with the agent."""
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit", ""]:
            break

        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]}, 
            config={"configurable": {"thread_id": "1"}}
        )
        
        # Log tool calls
        messages = response['messages']
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    print(f"🔧 Tool: {tool_call['name']} | Args: {tool_call['args']}")
        
        print(f"Agent: {response['messages'][-1].content}")


async def main():
    """Main entry point for the MCP React agent."""
    mcp_client = MultiServerMCPClient(MCP_CONFIG)
    tools = await mcp_client.get_tools()
    # Create agent with MCP tools and memory
    agent = create_react_agent(
        GIGA_CHAT,
        tools=tools,
        prompt="You are a helpful assistant.",
        checkpointer=MemorySaver()
    )

    await run_interactive_session(agent)


if __name__ == "__main__":
    asyncio.run(main())
    
