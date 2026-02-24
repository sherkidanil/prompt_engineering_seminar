# Create server parameters for stdio connection
import asyncio
import os

import httpx
from dotenv import find_dotenv, load_dotenv
from langchain_gigachat.chat_models.gigachat import GigaChat
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from rich import print as rprint

load_dotenv(find_dotenv(usecwd=True))


def _resolve_gigachat_credentials() -> str:
    credentials = os.getenv("GIGACHAT_CREDENTIALS") or os.getenv("API_KEY")
    if not credentials:
        raise ValueError(
            "Set GIGACHAT_CREDENTIALS or API_KEY in your .env before running agent_http.py"
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

# LLM GigaChat
model = GigaChat(
    model="GigaChat-2-Max",
    credentials=_resolve_gigachat_credentials(),
    verify_ssl_certs=False,
    streaming=False,
    max_tokens=8000,
    timeout=600,
)


def _log(ans):
    for message in ans['messages']:
        rprint(f"[{type(message).__name__}] {message.content} {getattr(message, 'tool_calls', '')}")


async def main():
    client = MultiServerMCPClient(
        {
            "math": {
                "url": "http://127.0.0.1:8000/sse",
                "transport": "sse",
                "httpx_client_factory": _httpx_client_factory,
            }
        }
    )
    tools = await client.get_tools()
    agent = create_react_agent(model, tools)

    agent_response = await agent.ainvoke({"messages": [
        {"role": "user", "content": "What is (3 + 5) * 12?"}]})
    _log(agent_response)

    agent_response = await agent.ainvoke({"messages": [
        {"role": "user", "content": "How old is John Doe?"}]})
    _log(agent_response)

# Run the main function
asyncio.run(main())
