from openhands.sdk.mcp.config import MCPServer


def build_web_fetch_mcp_config() -> dict[str, MCPServer]:
    """MCP server config that lets an agent retrieve a URL's content from
    the internet, converted to markdown -- the official `fetch` MCP server
    (github.com/modelcontextprotocol/servers, `mcp-server-fetch` on PyPI),
    launched via `uvx` so it needs no project dependency (uvx runs it in
    an ephemeral venv on first use, caching it after).

    Deliberately a fetch tool, not a full browser-automation MCP server
    (Playwright/Puppeteer-style navigate/click/screenshot): this project
    already live-tested OpenHands' own built-in interactive browser tool
    and found it unreliable with qwen3:8b for exactly that kind of
    multi-step agentic decision-making (see README Status -- the
    reviewer's --review-url path never even called browser_navigate
    across 3 attempts). A single "fetch this URL, get text back" tool
    call is a much narrower, more bounded action, closer in shape to the
    single-completion pattern that *has* proven reliable (the planner,
    SimpleReviewer) than to full interactive browsing.

    Returns a raw ``mcp_config`` mapping, not tool instances: OpenHands'
    ``Agent`` takes MCP servers via its own ``mcp_config`` field and
    materializes the actual tools itself when a ``Conversation`` starts
    (see ``LocalConversation`` in the SDK) -- they are not constructed
    here and are not compatible with the plain ``tools`` list, which only
    accepts ``Tool`` specs (name/params), not live tool definitions.

    Pinned to mcp<1.7: the currently published mcp-server-fetch imports
    McpError from a location that was renamed to MCPError in newer `mcp`
    releases, so it fails to start against an unpinned/latest `mcp`
    resolved by uvx. Confirmed live that pinning fixes it; remove the pin
    once upstream mcp-server-fetch catches up.
    """

    return {
        "fetch": MCPServer(
            command="uvx",
            args=["--with", "mcp<1.7", "mcp-server-fetch"],
        )
    }
