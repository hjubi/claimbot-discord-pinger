"""Data models mirroring the TibiaClaims claim-servers board API response."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class Reservation:
    id: str
    starts_at: Optional[str]
    ends_at: Optional[str]
    claim_day_key: Optional[str]
    character_name: Optional[str]
    claimant_name: Optional[str]
    claimant_kind: Optional[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reservation":
        return cls(
            id=data["id"],
            starts_at=data.get("startsAt"),
            ends_at=data.get("endsAt"),
            claim_day_key=data.get("claimDayKey"),
            character_name=data.get("characterName"),
            claimant_name=data.get("claimantName"),
            claimant_kind=data.get("claimantKind"),
        )

    @property
    def display_name(self) -> str:
        return self.character_name or self.claimant_name or "Unknown"


@dataclass(frozen=True, slots=True)
class Spawn:
    area_id: str
    area_name: str
    name: str
    slug: str
    status: str
    current: Optional[Reservation]
    next: Optional[Reservation]
    reservations: tuple[Reservation, ...] = field(default_factory=tuple)

    @property
    def key(self) -> str:
        """Stable identity for this spawn across snapshots."""
        return f"{self.area_id}:{self.slug}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Spawn":
        current = data.get("current")
        next_ = data.get("next")
        return cls(
            area_id=data["areaId"],
            area_name=data["areaName"],
            name=data["name"],
            slug=data["slug"],
            status=data.get("status", "unknown"),
            current=Reservation.from_dict(current) if current else None,
            next=Reservation.from_dict(next_) if next_ else None,
            reservations=tuple(
                Reservation.from_dict(r) for r in data.get("reservations", []) or []
            ),
        )


@dataclass(frozen=True, slots=True)
class Board:
    """A full snapshot of the claims board for one server."""

    spawns: tuple[Spawn, ...]
    fetched_at: Optional[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Board":
        spawns: list[Spawn] = []
        for area in data.get("areas", []) or []:
            for spawn_data in area.get("spawns", []) or []:
                spawns.append(Spawn.from_dict(spawn_data))
        return cls(spawns=tuple(spawns), fetched_at=data.get("fetchedAt"))

    def by_key(self) -> dict[str, Spawn]:
        return {spawn.key: spawn for spawn in self.spawns}
