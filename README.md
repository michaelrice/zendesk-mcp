# zendesk-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes Zendesk ticket read and write tools to [Claude Code](https://claude.com/claude-code) and other MCP clients.

## What it does

- Search, list (paginated), and fetch Zendesk tickets, comments, and attachments
- Create new tickets and update existing ticket fields
- Post public replies and internal notes
- Set ticket status and assign tickets to agents
- Read and write time-tracking entries
- Format a ticket as a Markdown issue draft for handoff to a tracker (GitLab, GitHub, Jira)
- Two MCP prompts (`analyze-ticket`, `draft-ticket-response`) for ticket analysis and response drafting
- (Optional) Expose Zendesk Help Center articles as an MCP resource
- (Optional) Read linked GitLab issues / MRs / commits via the [Git-Zen](https://www.zendesk.com/marketplace/apps/support/630175/git-zen-zendesk-and-gitlab-integration/) Zendesk app

## Prerequisites

- Python 3.10 or newer
- A Zendesk OAuth client. A Zendesk admin can create one at:
  `https://<your-subdomain>.zendesk.com/admin/apps-integrations/apis/zendesk-api/oauth_clients`
  Set the redirect URL to `http://localhost:8787/callback` and request scopes `read write`.

## Install

Install into a project-local virtualenv. Using a venv keeps `zendesk-mcp` and its dependencies isolated from your system Python and from other projects, and is the recommended path for everything below.

From a clone of this repository:

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
```

For development (also installs pytest):

```bash
.venv/bin/pip install -e ".[dev]"
```

> Throughout this README, commands use the venv's binaries via `.venv/bin/...`. You can instead `source .venv/bin/activate` once per shell and drop the prefix — the result is the same.

## OAuth setup

Run the interactive setup using the venv's Python:

```bash
.venv/bin/python -m zendesk_mcp setup
```

You will be prompted for:

1. Your Zendesk subdomain (e.g. `acme` for `acme.zendesk.com`)
2. The OAuth client ID created by your admin
3. The OAuth client secret
4. (Optional) A Git-Zen integration field ID — see [Optional: Git-Zen integration](#optional-git-zen-integration)
5. (Optional) Whether to enable the Help Center knowledge base resource — see [Optional: Help Center knowledge base](#optional-help-center-knowledge-base)

The setup opens a browser for the OAuth authorization step, then writes a token to `~/.config/zendesk-mcp/config.json` (mode `0600`).

If you have no browser, the URL is printed to the terminal — open it on any device, click **Allow**, and paste the resulting redirect URL back into the prompt.

## Register with Claude Code

Register the MCP server using the venv's Python by absolute path. Claude Code launches the server in a fresh shell that does **not** inherit your activated venv, so the absolute path is required — pointing at a bare `python` here will fail to import `zendesk_mcp`.

```bash
ZENDESK_MCP_DIR="$(pwd)"   # run this from the repo root, after install
claude mcp add --scope user zendesk -- "$ZENDESK_MCP_DIR/.venv/bin/python" -m zendesk_mcp
```

Or just inline the absolute path you want:

```bash
claude mcp add --scope user zendesk -- /absolute/path/to/zendesk-mcp/.venv/bin/python -m zendesk_mcp
```

Then add the read tools to `permissions.allow` in `~/.claude/settings.json` to avoid per-call prompts:

```json
{
  "permissions": {
    "allow": [
      "mcp__zendesk__zendesk_get_ticket",
      "mcp__zendesk__zendesk_get_tickets",
      "mcp__zendesk__zendesk_get_comments",
      "mcp__zendesk__zendesk_list_attachments",
      "mcp__zendesk__zendesk_download_attachment",
      "mcp__zendesk__zendesk_search_tickets",
      "mcp__zendesk__zendesk_ticket_to_gitlab_context"
    ]
  }
}
```

Write tools (`zendesk_post_comment`, `zendesk_post_internal_note`, `zendesk_set_ticket_status`, `zendesk_assign_ticket`, `zendesk_create_ticket`, `zendesk_update_ticket`, `zendesk_log_time`) are intentionally not in the default allow-list — Claude will prompt you per call.

## Tools

| Tool | What it does |
|---|---|
| `zendesk_search_tickets` | Search tickets by status, priority, type, assignee, requester, tags, or keyword |
| `zendesk_get_tickets` | List tickets with pagination and sorting (page, per_page, sort_by, sort_order) |
| `zendesk_get_ticket` | Get one ticket's metadata |
| `zendesk_create_ticket` | Create a new ticket (subject, description, optional priority/type/assignee_id/requester_id/tags/custom_fields) |
| `zendesk_update_ticket` | Update one or more fields on an existing ticket (status, priority, subject, type, assignee_id, requester_id, tags, custom_fields, due_at) |
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

## Prompts

The server exposes two MCP prompts that some clients (e.g. Claude Desktop) surface as slash commands:

| Prompt | Argument | What it does |
|---|---|---|
| `analyze-ticket` | `ticket_id` | Asks the model to fetch the ticket and produce a summary, status/timeline, and key interaction points |
| `draft-ticket-response` | `ticket_id` | Asks the model to fetch the ticket and draft a customer-facing response (with a confirmation step before posting) |

## Optional: Git-Zen integration

If your Zendesk instance uses the [Git-Zen](https://www.zendesk.com/marketplace/apps/support/630175/git-zen-zendesk-and-gitlab-integration/) app, the `zendesk_get_git_zen_links` tool can read its custom-field payload. Find your instance's Git-Zen custom field ID under **Admin → Tickets → Fields** (it is a numeric ID), then either set it during `.venv/bin/python -m zendesk_mcp setup` or edit `~/.config/zendesk-mcp/config.json` to add:

```json
{
  "git_zen_field_id": 12345678901234
}
```

Without this configured, `zendesk_get_git_zen_links` returns a "not configured" message.

## Optional: Help Center knowledge base

If your Zendesk instance has a published Help Center, you can expose its sections and articles as the `zendesk://knowledge-base` MCP resource. The resource returns a single JSON document covering all sections and articles, cached for one hour.

This is opt-in. Enable it by either answering "y" to the prompt during `.venv/bin/python -m zendesk_mcp setup`, or by adding the following to `~/.config/zendesk-mcp/config.json`:

```json
{
  "knowledge_base_enabled": true
}
```

When the flag is absent or false, the resource is not registered, keeping the server's resource list empty for instances without a Help Center.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

Tests run on Python 3.10, 3.11, and 3.12 in CI (see `.github/workflows/test.yml`).

## License

[Apache-2.0](LICENSE)
