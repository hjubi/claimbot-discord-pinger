"""Formats ChangeEvent objects into rich Discord embeds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord

from .config import settings
from .diff_engine import ChangeEvent, ChangeType

_TYPE_EMOJI = {
    ChangeType.NEW_RESERVATION: "🆕",
    ChangeType.RESERVATION_CANCELLED: "❌",
    ChangeType.CLAIM_STARTED: "▶️",
    ChangeType.CLAIM_ENDED: "⏹️",
    ChangeType.STATUS_CHANGED: "🔄",
    ChangeType.SPAWN_ADDED: "➕",
    ChangeType.SPAWN_REMOVED: "➖",
}

_TYPE_LABEL = {
    ChangeType.NEW_RESERVATION: "New reservation",
    ChangeType.RESERVATION_CANCELLED: "Reservation cancelled",
    ChangeType.CLAIM_STARTED: "Claim started",
    ChangeType.CLAIM_ENDED: "Claim ended",
    ChangeType.STATUS_CHANGED: "Status changed",
    ChangeType.SPAWN_ADDED: "Spawn added to board",
    ChangeType.SPAWN_REMOVED: "Spawn removed from board",
}


def _to_unix(iso_str: Optional[str]) -> Optional[int]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return int(dt.astimezone(timezone.utc).timestamp())
    except ValueError:
        return None


def _color_for(event_type: ChangeType) -> int:
    if event_type in (ChangeType.NEW_RESERVATION, ChangeType.CLAIM_STARTED, ChangeType.SPAWN_ADDED):
        return settings.embed_color_new
    if event_type in (ChangeType.RESERVATION_CANCELLED, ChangeType.CLAIM_ENDED, ChangeType.SPAWN_REMOVED):
        return settings.embed_color_removed
    return settings.embed_color_status


def _field_value_for(event: ChangeEvent) -> str:
    if event.type == ChangeType.STATUS_CHANGED:
        return f"`{event.old_status}` → `{event.new_status}`"

    if event.reservation is not None:
        res = event.reservation
        lines = [f"**Character:** {res.display_name}"]
        start_ts = _to_unix(res.starts_at)
        end_ts = _to_unix(res.ends_at)
        if start_ts:
            lines.append(f"**From:** <t:{start_ts}:f> (<t:{start_ts}:R>)")
        if end_ts:
            lines.append(f"**Until:** <t:{end_ts}:f> (<t:{end_ts}:R>)")
        return "\n".join(lines)

    return "\u200b"


def build_embeds(events: list[ChangeEvent], server_name: str = "Karmeya") -> list[discord.Embed]:
    """Group change events into one or more Discord embeds, respecting field limits."""
    if not events:
        return []

    embeds: list[discord.Embed] = []
    chunk_size = settings.max_events_per_message
    chunks = [events[i : i + chunk_size] for i in range(0, len(events), chunk_size)]
    total_chunks = len(chunks)

    for idx, chunk in enumerate(chunks, start=1):
        embed = discord.Embed(
            title=f"🗺️ TibiaClaims — {server_name} board update",
            description=f"Detected **{len(events)}** change(s) on the claims board.",
            color=_color_for(chunk[0].type),
            timestamp=datetime.now(timezone.utc),
        )
        for event in chunk:
            name = f"{_TYPE_EMOJI[event.type]} {_TYPE_LABEL[event.type]} — {event.area_name} / {event.spawn_name}"
            embed.add_field(name=name[:256], value=_field_value_for(event)[:1024], inline=False)

        footer = "TibiaClaims Board Watcher"
        if total_chunks > 1:
            footer += f" • page {idx}/{total_chunks}"
        embed.set_footer(text=footer)
        embeds.append(embed)

    return embeds
