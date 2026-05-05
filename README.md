# zendesk-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes Zendesk ticket read and write tools to [Claude Code](https://claude.com/claude-code) and other MCP clients.

## What it does

- Search and fetch Zendesk tickets, comments, and attachments
- Post public replies and internal notes
- Set ticket status and assign tickets to agents
- Read and write time-tracking entries
- Format a ticket as a Markdown issue draft for handoff to a tracker (GitLab, GitHub, Jira)
- (Optional) Read linked GitLab issues / MRs / commits via the [Git-Zen](https://www.zendesk.com/marketplace/apps/support/630175/git-zen-zendesk-and-gitlab-integration/) Zendesk app

## Prerequisites

- Python 3.10 or newer
- A Zendesk OAuth client. A Zendesk admin can create one at:
  `https://<your-subdomain>.zendesk.com/admin/apps-integrations/apis/zendesk-api/oauth_clients`
  Set the redirect URL to `http://localhost:8787/callback` and request scopes `read write`.

## Install

From a clone of this repository:

```bash
pip install -e .
```

Or for development (includes pytest):

```bash
pip install -e ".[dev]"
```

## OAuth setup

Run the interactive setup:

```bash
python -m zendesk_mcp setup
```

You will be prompted for:

1. Your Zendesk subdomain (e.g. `acme` for `acme.zendesk.com`)
2. The OAuth client ID created by your admin
3. The OAuth client secret
4. (Optional) A Git-Zen integration field ID — see [Optional: Git-Zen integration](#optional-git-zen-integration)

The setup opens a browser for the OAuth authorization step, then writes a token to `~/.config/zendesk-mcp/config.json` (mode `0600`).

If you have no browser, the URL is printed to the terminal — open it on any device, click **Allow**, and paste the resulting redirect URL back into the prompt.

## Register with Claude Code

```bash
claude mcp add --scope user zendesk -- python -m zendesk_mcp
```

Then add the read tools to `permissions.allow` in `~/.claude/settings.json` to avoid per-call prompts:

```json
{
  "permissions": {
    "allow": [
      "mcp__zendesk__zendesk_get_ticket",
      "mcp__zendesk__zendesk_get_comments",
      "mcp__zendesk__zendesk_list_attachments",
      "mcp__zendesk__zendesk_download_attachment",
      "mcp__zendesk__zendesk_search_tickets",
      "mcp__zendesk__zendesk_ticket_to_gitlab_context"
    ]
  }
}
```

Write tools (`zendesk_post_comment`, `zendesk_post_internal_note`, `zendesk_set_ticket_status`, `zendesk_assign_ticket`, `zendesk_log_time`) are intentionally not in the default allow-list — Claude will prompt you per call.

## Tools

| Tool | What it does |
|---|---|
| `zendesk_search_tickets` | Search tickets by status, priority, type, assignee, requester, tags, or keyword |
| `zendesk_get_ticket` | Get one ticket's metadata |
| `zendesk_get_comments` | Get the conversation thread on a ticket |
| `zendesk_list_attachments` | List attachments on a ticket |
| `zendesk_download_attachment` | Download an attachment to a local cache directory |
| `zendesk_ticket_to_gitlab_context` | Format a ticket and its conversation as a Markdown issue draft |
| `zendesk_post_comment` | Post a public reply on a ticket |
| `zendesk_post_internal_note` | Post an agent-only internal note on a ticket |
| `zendesk_set_ticket_status` | Set ticket status (`new`, `open`, `pending`, `hold`, `solved`, `closed`) |
| `zendesk_assign_ticket` | Assign a ticket to an agent by email or `me` |
| `zendesk_get_time_tracking` | Read time-tracking entries for a ticket |
| `zendesk_log_time` | Log a time entry against a ticket |
| `zendesk_get_git_zen_links` | (Git-Zen only) Get linked GitLab issues / MRs / commits for a ticket |

## Optional: Git-Zen integration

If your Zendesk instance uses the [Git-Zen](https://www.zendesk.com/marketplace/apps/support/630175/git-zen-zendesk-and-gitlab-integration/) app, the `zendesk_get_git_zen_links` tool can read its custom-field payload. Find your instance's Git-Zen custom field ID under **Admin → Tickets → Fields** (it is a numeric ID), then either set it during `python -m zendesk_mcp setup` or edit `~/.config/zendesk-mcp/config.json` to add:

```json
{
  "git_zen_field_id": 12345678901234
}
```

Without this configured, `zendesk_get_git_zen_links` returns a "not configured" message.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests run on Python 3.10, 3.11, and 3.12 in CI (see `.github/workflows/test.yml`).

## License

[Apache-2.0](LICENSE)
