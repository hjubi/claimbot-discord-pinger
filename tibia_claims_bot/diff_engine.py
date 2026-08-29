"""Computes the set of meaningful changes between two board snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .models import Board, Reservation, Spawn


class ChangeType(str, Enum):
    NEW_RESERVATION = "new_reservation"
    RESERVATION_CANCELLED = "reservation_cancelled"
    CLAIM_STARTED = "claim_started"
    CLAIM_ENDED = "claim_ended"
    STATUS_CHANGED = "status_changed"
    SPAWN_ADDED = "spawn_added"
    SPAWN_REMOVED = "spawn_removed"


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    type: ChangeType
    area_name: str
    spawn_name: str
    reservation: Optional[Reservation] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.area_name, self.spawn_name)


def diff_boards(previous: Optional[Board], current: Board) -> list[ChangeEvent]:
    """Compare two boards and return a list of change events.

    If `previous` is None (first run, no prior snapshot), no events are
    returned — the current snapshot simply becomes the new baseline.
    """
    if previous is None:
        return []

    events: list[ChangeEvent] = []
    old_spawns = previous.by_key()
    new_spawns = current.by_key()

    for key, new_spawn in new_spawns.items():
        old_spawn = old_spawns.get(key)
        if old_spawn is None:
            events.append(
                ChangeEvent(
                    type=ChangeType.SPAWN_ADDED,
                    area_name=new_spawn.area_name,
                    spawn_name=new_spawn.name,
                )
            )
            continue
        events.extend(_diff_spawn(old_spawn, new_spawn))

    for key, old_spawn in old_spawns.items():
        if key not in new_spawns:
            events.append(
                ChangeEvent(
                    type=ChangeType.SPAWN_REMOVED,
                    area_name=old_spawn.area_name,
                    spawn_name=old_spawn.name,
                )
            )

    events.sort(key=lambda e: e.sort_key)
    return events


def _diff_spawn(old: Spawn, new: Spawn) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []

    old_reservations = {r.id: r for r in old.reservations}
    new_reservations = {r.id: r for r in new.reservations}

    for res_id, res in new_reservations.items():
        if res_id not in old_reservations:
            events.append(
                ChangeEvent(
                    type=ChangeType.NEW_RESERVATION,
                    area_name=new.area_name,
                    spawn_name=new.name,
                    reservation=res,
                )
            )

    for res_id, res in old_reservations.items():
        if res_id not in new_reservations:
            events.append(
                ChangeEvent(
                    type=ChangeType.RESERVATION_CANCELLED,
                    area_name=old.area_name,
                    spawn_name=old.name,
                    reservation=res,
                )
            )

    old_current_id = old.current.id if old.current else None
    new_current_id = new.current.id if new.current else None
    if old_current_id != new_current_id:
        if new.current is not None:
            events.append(
                ChangeEvent(
                    type=ChangeType.CLAIM_STARTED,
                    area_name=new.area_name,
                    spawn_name=new.name,
                    reservation=new.current,
                )
            )
        elif old.current is not None:
            events.append(
                ChangeEvent(
                    type=ChangeType.CLAIM_ENDED,
                    area_name=old.area_name,
                    spawn_name=old.name,
                    reservation=old.current,
                )
            )

    if old.status != new.status:
        events.append(
            ChangeEvent(
                type=ChangeType.STATUS_CHANGED,
                area_name=new.area_name,
                spawn_name=new.name,
                old_status=old.status,
                new_status=new.status,
            )
        )

    return events
