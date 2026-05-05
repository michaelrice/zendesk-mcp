import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("zendesk-mcp")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        from zendesk_mcp.setup import run_setup
        run_setup()
        return

    from zendesk_mcp.tools.ticket import register_ticket_tools
    from zendesk_mcp.tools.comments import register_comments_tools
    from zendesk_mcp.tools.attachments import register_attachment_tools
    from zendesk_mcp.tools.gitlab_context import register_gitlab_context_tools
    from zendesk_mcp.tools.write_comments import register_write_comment_tools
    from zendesk_mcp.tools.update_ticket import register_update_ticket_tools
    from zendesk_mcp.tools.time_tracking import register_time_tracking_tools
    from zendesk_mcp.tools.git_zen import register_git_zen_tools

    register_ticket_tools(mcp)
    register_comments_tools(mcp)
    register_attachment_tools(mcp)
    register_gitlab_context_tools(mcp)
    register_write_comment_tools(mcp)
    register_update_ticket_tools(mcp)
    register_time_tracking_tools(mcp)
    register_git_zen_tools(mcp)

    mcp.run()


if __name__ == "__main__":
    main()
