def ticket_channel(ticket) -> str | None:
    """The channel a ticket arrived on: Zendesk's ``via.channel`` ("web", "email", "api", ...).

    Accepts a zenpy Ticket (``via`` is an object with a ``channel`` attribute) or a raw API
    ticket dict (``via`` is a dict). Returns None when the payload does not carry a string
    channel, so a missing field never produces a value that will not serialize.
    """
    via = ticket.get("via") if isinstance(ticket, dict) else getattr(ticket, "via", None)
    channel = via.get("channel") if isinstance(via, dict) else getattr(via, "channel", None)
    return channel if isinstance(channel, str) else None
