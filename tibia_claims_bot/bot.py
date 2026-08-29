"""Discord bot entrypoint: periodically polls the TibiaClaims board and
posts embed notifications for any detected changes."""

from __future__ import annotations

import logging

import aiohttp
import discord
from discord.ext import commands, tasks

from .api_client import TibiaClaimsApiError, TibiaClaimsClient
from .config import settings
from .diff_engine import diff_boards
from .models import Board
from .notifier import build_embeds
from .storage import SnapshotStore

logger = logging.getLogger(__name__)

# Discord allows at most 10 embeds per message.
_MAX_EMBEDS_PER_MESSAGE = 10


class TibiaClaimsBot(commands.Bot):
    """A minimal, single-purpose bot: watch one endpoint, report changes."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!tibia ", intents=intents, help_command=None)

        self._store = SnapshotStore(settings.state_file)
        self._session: aiohttp.ClientSession | None = None
        self._client: TibiaClaimsClient | None = None
        self._channel: discord.abc.Messageable | None = None
        self._consecutive_failures = 0

    async def setup_hook(self) -> None:
        self._session = aiohttp.ClientSession()
        self._client = TibiaClaimsClient(settings.api_url, self._session)
        self.poll_board.change_interval(seconds=settings.poll_interval_seconds)
        self.poll_board.start()

    async def close(self) -> None:
        self.poll_board.cancel()
        if self._session is not None:
            await self._session.close()
        await super().close()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s (id=%s)", self.user, self.user.id if self.user else "?")
        channel = self.get_channel(settings.channel_id)
        if channel is None:
            try:
                channel = await self.fetch_channel(settings.channel_id)
            except discord.DiscordException as exc:
                logger.error("Could not resolve channel %s: %s", settings.channel_id, exc)
                return
        self._channel = channel
        logger.info("Notifications will be posted to #%s", getattr(channel, "name", channel.id))

    @tasks.loop(seconds=60)
    async def poll_board(self) -> None:
        if self._client is None:
            return
        try:
            current_board, raw_payload = await self._client.fetch_board()
        except TibiaClaimsApiError as exc:
            self._consecutive_failures += 1
            logger.warning(
                "Fetch failed (%d consecutive failure(s)): %s", self._consecutive_failures, exc
            )
            if self._consecutive_failures in (3, 10, 30):
                await self._notify_failure(exc)
            return

        self._consecutive_failures = 0

        previous_raw = self._store.load()
        previous_board = Board.from_dict(previous_raw) if previous_raw else None

        events = diff_boards(previous_board, current_board)

        # Always persist the latest snapshot, even with no changes, so the
        # baseline stays fresh (fetchedAt, etc.).
        self._store.save(raw_payload)

        if not events:
            logger.debug("No changes detected.")
            return

        logger.info("Detected %d change(s); sending notification(s).", len(events))
        await self._send_events(events)

    @poll_board.before_loop
    async def before_poll_board(self) -> None:
        await self.wait_until_ready()

    async def _send_events(self, events) -> None:
        if self._channel is None:
            logger.error("No target channel resolved; dropping %d event(s).", len(events))
            return

        embeds = build_embeds(events, server_name="Karmeya")
        for i in range(0, len(embeds), _MAX_EMBEDS_PER_MESSAGE):
            batch = embeds[i : i + _MAX_EMBEDS_PER_MESSAGE]
            try:
                await self._channel.send(embeds=batch)
            except discord.DiscordException as exc:
                logger.error("Failed to send notification embeds: %s", exc)

    async def _notify_failure(self, exc: Exception) -> None:
        if self._channel is None:
            return
        embed = discord.Embed(
            title="⚠️ TibiaClaims Board Watcher — fetch failing",
            description=(
                f"Could not reach the TibiaClaims API for {self._consecutive_failures} "
                f"consecutive attempt(s).\n```\n{exc}\n```"
            ),
            color=0xE74C3C,
        )
        try:
            await self._channel.send(embed=embed)
        except discord.DiscordException:
            logger.exception("Failed to send failure notification.")


def run() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    bot = TibiaClaimsBot()
    bot.run(settings.discord_token, log_handler=None)
