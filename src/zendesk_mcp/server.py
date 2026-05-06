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
    from zendesk_mcp.tools.create_ticket import register_create_ticket_tools
    from zendesk_mcp.tools.list_tickets import register_list_tickets_tools
    from zendesk_mcp.tools.knowledge_base import register_knowledge_base_resource
    from zendesk_mcp.prompts import register_prompts

    register_ticket_tools(mcp)
    register_comments_tools(mcp)
    register_attachment_tools(mcp)
    register_gitlab_context_tools(mcp)
    register_write_comment_tools(mcp)
    register_update_ticket_tools(mcp)
    register_time_tracking_tools(mcp)
    register_git_zen_tools(mcp)
    register_create_ticket_tools(mcp)
    register_list_tickets_tools(mcp)
    register_knowledge_base_resource(mcp)
    register_prompts(mcp)

    mcp.run()


if __name__ == "__main__":
    main()
