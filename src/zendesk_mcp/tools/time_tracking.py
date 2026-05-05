import json
from zenpy.lib.api_objects import Ticket
from zendesk_mcp.client import get_client, ConfigError

_FIELD_TOTAL_TIME_SPENT = 30435145651479
_FIELD_TIME_SPENT_LAST_UPDATE = 30435145655959


def _get_custom_field(ticket, field_id: int):
    for f in (ticket.custom_fields or []):
        if f['id'] == field_id:
            return f['value']
    return None


def _format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"


def _get_time_tracking_data(ticket_id: int) -> str:
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        total = int(_get_custom_field(ticket, _FIELD_TOTAL_TIME_SPENT) or 0)
        last = int(_get_custom_field(ticket, _FIELD_TIME_SPENT_LAST_UPDATE) or 0)
        return json.dumps({
            "ticket_id": ticket_id,
            "total_time_spent_sec": total,
            "time_spent_last_update_sec": last,
            "total_time_human": _format_duration(total),
            "time_spent_last_update_human": _format_duration(last),
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def _log_time_data(ticket_id: int, seconds: int) -> str:
    if seconds <= 0:
        return f"seconds must be a positive integer, got {seconds}."
    try:
        client = get_client()
        ticket = client.tickets(id=ticket_id)
        current_total = int(_get_custom_field(ticket, _FIELD_TOTAL_TIME_SPENT) or 0)
        new_total = current_total + seconds
        update = Ticket(id=ticket_id)
        update.custom_fields = [
            {"id": _FIELD_TOTAL_TIME_SPENT, "value": new_total},
            {"id": _FIELD_TIME_SPENT_LAST_UPDATE, "value": seconds},
        ]
        client.tickets.update(update)
        return json.dumps({
            "ticket_id": ticket_id,
            "logged_sec": seconds,
            "logged_human": _format_duration(seconds),
            "new_total_sec": new_total,
            "new_total_human": _format_duration(new_total),
        }, indent=2)
    except ConfigError as e:
        return str(e)
    except Exception as e:
        if "RecordNotFound" in str(e) or "404" in str(e):
            return f"Ticket #{ticket_id} not found or not accessible with current credentials."
        return f"Zendesk API error: {e}"


def register_time_tracking_tools(mcp) -> None:
    @mcp.tool()
    def zendesk_get_time_tracking(ticket_id: int) -> str:
        """Get time tracking data for a Zendesk ticket. Returns total time spent and time spent on the last update, in both seconds and human-readable format (e.g. '2h 15m')."""
        return _get_time_tracking_data(ticket_id)

    @mcp.tool()
    def zendesk_log_time(ticket_id: int, seconds: int) -> str:
        """Log time spent on a Zendesk ticket. Adds seconds to the running total and records it as the last-update time. Returns logged amount and new total in seconds and human-readable format."""
        return _log_time_data(ticket_id, seconds)
