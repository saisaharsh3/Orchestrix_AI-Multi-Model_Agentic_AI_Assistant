"""
mcp_server.py - Orchestrix as a Model Context Protocol (MCP) server.

Lets any MCP client (Claude Desktop, Claude Code, Cursor, …) use your
assistant's tools: search your local PDF index, read your calendar and inbox,
check prices and weather. Runs over stdio:

    python mcp_server.py

Read-only tools are always exposed. Tools that send, create or control
something (email, calendar, tasks, phone, and `ask_orchestrix`, which runs the
full assistant) are exposed only with ORCHESTRIX_MCP_ALLOW_WRITE=true.
Requests act as ORCHESTRIX_MCP_USER (default: TELEGRAM_CHAT_ID), so the
server sees that user's documents, memory and saved locations.
"""

import contextlib
import os
import sys
from pathlib import Path

# MCP clients start servers from an arbitrary working directory; data/, logs/
# and credentials/ are relative to the project, so run from there.
os.chdir(Path(__file__).resolve().parent)

import anyio  # noqa: E402
import mcp.types as types  # noqa: E402
from mcp.server.lowlevel import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402

from config.settings import settings  # noqa: E402
from core.agent.tools import READ, TOOLS, ToolContext  # noqa: E402
from core.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

ASK_TOOL = "ask_orchestrix"

INSTRUCTIONS = (
    "Orchestrix is the user's personal, local-first assistant. Use search_my_documents for "
    "questions about the user's own PDFs, and the calendar/inbox/tasks tools for their schedule "
    "and mail. Read-only tools have no side effects."
)


def exposed_tools() -> list:
    return [t for t in TOOLS.values() if t.kind == READ or settings.MCP_ALLOW_WRITE]


def tool_specs() -> list[types.Tool]:
    specs = [
        types.Tool(
            name=t.name,
            description=t.description,
            inputSchema=t.schema,
            annotations=types.ToolAnnotations(
                readOnlyHint=t.kind == READ,
                destructiveHint=t.kind != READ,
                openWorldHint=True,
            ),
        )
        for t in exposed_tools()
    ]
    if settings.MCP_ALLOW_WRITE:
        specs.append(
            types.Tool(
                name=ASK_TOOL,
                description=(
                    "Send a message to the full Orchestrix assistant, exactly as if typed in chat. "
                    "It may act on the message (e.g. phone control); email and calendar still ask "
                    "for a follow-up 'yes'."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
                annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True),
            )
        )
    return specs


def run_tool(name: str, arguments: dict) -> str:
    """Execute one tool synchronously (called from a worker thread)."""
    # stdout is the MCP channel: anything a tool prints must go to stderr instead.
    with contextlib.redirect_stdout(sys.stderr):
        if name == ASK_TOOL and settings.MCP_ALLOW_WRITE:
            from core.orchestrator import respond
            return respond(arguments["message"], user_id=settings.MCP_USER_ID).text

        tool = TOOLS.get(name)
        if tool is None or tool not in exposed_tools():
            raise ValueError(f"Unknown or disabled tool: {name}")

        from core.session import sessions
        ctx = ToolContext(user_id=settings.MCP_USER_ID, session=sessions.get(settings.MCP_USER_ID))
        return tool.execute(ctx, arguments)


def build_server() -> Server:
    server = Server("orchestrix", version="0.3.0", instructions=INSTRUCTIONS)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return tool_specs()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        logger.info(f"MCP call: {name}")
        text = await anyio.to_thread.run_sync(run_tool, name, arguments or {})
        return [types.TextContent(type="text", text=text)]

    return server


def _warm_up() -> None:
    """
    Load heavy libraries before serving, on the main thread.

    Loading FAISS / PyTorch from a worker thread while the stdio transport is
    running stalled every request for ~90 s on Windows (FAISS's loader queries
    the platform via WMI). Doing it up front keeps tool calls fast.
    """
    import platform

    platform.uname()  # cache the (slow on Windows) platform query
    from core.session import sessions

    session = sessions.get(settings.MCP_USER_ID)
    if session.has_documents:
        logger.info("Loading document index…")
        with contextlib.redirect_stdout(sys.stderr):
            session.pdf_store  # noqa: B018 - property access triggers the load
        logger.info("Document index ready")


async def _serve() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    logger.info(
        f"Orchestrix MCP server starting (user={settings.MCP_USER_ID}, "
        f"write tools {'ON' if settings.MCP_ALLOW_WRITE else 'off'})"
    )
    _warm_up()
    anyio.run(_serve)


if __name__ == "__main__":
    main()
