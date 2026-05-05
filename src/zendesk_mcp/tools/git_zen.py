import json
from zendesk_mcp.client import get_client, ConfigError
from zendesk_mcp.config import load_config

_NOT_CONFIGURED_MESSAGE = (
    "Git-Zen field ID not configured. Set 'git_zen_field_id' in "
    "~/.config/zendesk-mcp/config.json to enable this tool."
)


def _get_git_zen_links_data(ticket_id: int) -> str:
    field_id = load_config().get("git_zen_field_id")
    if field_id is None:
        return _NOT_CONFIGURED_MESSAGE

    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        raw = None
        for f in (ticket.custom_fields or []):
            if f['id'] == field_id and f['value']:
                raw = f['value']
                break

        if not raw:
            return json.dumps({
                "ticket_id": ticket_id,
                "linked_issues": [],
                "linked_mrs": [],
                "linked_commits": [],
            }, indent=2)

        data = json.loads(raw)

        issues = []
        for group in data.get('issueGroup', []):
            for issue in group.get('issues', []):
                issues.append({
                    "project": f"{group['owner']}/{group['name']}",
                    "number": issue['number'],
                    "title": issue['name'],
                    "link": issue['link'],
                    "state": issue['state'],
                    "labels": [lbl['name'] for lbl in issue.get('labels', [])],
                    "weight": issue.get('weight'),
                    "milestone": issue.get('milestone'),
                })

        mrs = []
        for group in data.get('fileGroup', []):
            for mr in group.get('files', []):
                mrs.append({
                    "project": f"{group.get('owner', '')}/{group.get('name', '')}",
                    "number": mr.get('number', ''),
                    "title": mr.get('name', ''),
                    "link": mr.get('link', ''),
                    "state": mr.get('state', ''),
                })

        commits = []
        for group in data.get('commitGroup', []):
            for commit in group.get('commits', []):
                commits.append({
                    "project": f"{group.get('owner', '')}/{group.get('name', '')}",
                    "sha": commit.get('id', ''),
                    "message": commit.get('message', ''),
                    "link": commit.get('url', ''),
                })

        return json.dumps({
            "ticket_id": ticket_id,
            "linked_issues": issues,
            "linked_mrs": mrs,
            "linked_commits": commits,
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_git_zen_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_get_git_zen_links(ticket_id: int) -> str:
        """Get linked GitLab issues, merge requests, and commits for a Zendesk ticket via the Git-Zen integration. Returns structured lists with state, labels, weight, and direct GitLab links."""
        return _get_git_zen_links_data(ticket_id)
