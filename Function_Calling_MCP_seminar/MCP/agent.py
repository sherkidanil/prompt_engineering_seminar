# Create server parameters for stdio connection
import asyncio
import os

from dotenv import find_dotenv, load_dotenv
from langchain_gigachat import GigaChat
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich import print as rprint

load_dotenv(find_dotenv(usecwd=True))


def _resolve_gigachat_credentials() -> str:
    credentials = os.getenv("GIGACHAT_CREDENTIALS") or os.getenv("API_KEY")
    if not credentials:
        raise ValueError(
            "Set GIGACHAT_CREDENTIALS or API_KEY in your .env before running agent.py"
        )
    return credentials

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
    server_params = StdioServerParameters(
        command="python",
        args=["math_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(model, tools)

            agent_response = await agent.ainvoke({"messages": [
                {"role": "user", "content": "What is (3 + 5) * 12?"}]})
            _log(agent_response)
            
            agent_response = await agent.ainvoke({"messages": [
                {"role": "user", "content": "How old is John Doe?"}]})
            _log(agent_response)

# Run the main function
asyncio.run(main())
