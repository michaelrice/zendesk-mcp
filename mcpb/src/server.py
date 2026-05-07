"""MCPB bundle entry point — delegates to the installed zendesk_mcp package."""
from zendesk_mcp.server import main

if __name__ == "__main__":
    main()
