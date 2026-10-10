"""MCP server: which tools are exposed and how calls are executed."""

import anyio
import pytest

import mcp_server
from core.agent.tools import READ, TOOLS, Tool


@pytest.fixture
def allow_write(monkeypatch):
    monkeypatch.setattr(mcp_server.settings, "MCP_ALLOW_WRITE", True)


def test_only_read_tools_by_default():
    names = {t.name for t in mcp_server.tool_specs()}
    assert "search_my_documents" in names and "check_inbox" in names
    assert "send_email" not in names and mcp_server.ASK_TOOL not in names
    assert all(t.annotations.readOnlyHint for t in mcp_server.tool_specs())


def test_write_tools_when_enabled(allow_write):
    specs = {t.name: t for t in mcp_server.tool_specs()}
    assert specs["send_email"].annotations.destructiveHint
    assert mcp_server.ASK_TOOL in specs


def test_disabled_tool_cannot_be_called():
    with pytest.raises(ValueError, match="disabled"):
        mcp_server.run_tool("send_email", {"to": "a@b.c", "subject": "s", "body": "b"})


def test_tool_output_never_reaches_stdout(monkeypatch, capsys):
    def noisy(ctx, query):
        print("library chatter")  # would corrupt the stdio protocol
        return f"result for {query}"

    monkeypatch.setitem(TOOLS, "web_search", Tool("web_search", "", READ, noisy, {"query": {"type": "string"}}, ["query"]))
    assert mcp_server.run_tool("web_search", {"query": "mcp"}) == "result for mcp"
    out = capsys.readouterr()
    assert out.out == "" and "library chatter" in out.err


def test_ask_orchestrix_runs_pipeline(allow_write):
    assert "Orchestrix" in mcp_server.run_tool(mcp_server.ASK_TOOL, {"message": "/help"})


def test_server_lists_and_calls_tools_over_protocol():
    """Round-trip through a real MCP client session over in-memory streams."""
    from mcp.shared.memory import create_connected_server_and_client_session

    async def scenario():
        server = mcp_server.build_server()
        async with create_connected_server_and_client_session(server) as client:
            listed = await client.list_tools()
            result = await client.call_tool("get_current_time", {})
            return {t.name for t in listed.tools}, result

    names, result = anyio.run(scenario)
    assert "search_my_documents" in names
    days = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    assert not result.isError and result.content[0].text.startswith(days)
