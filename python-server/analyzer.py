import logging
from datetime import datetime, timedelta, timezone
import aiosqlite
import json

# --- Configuration ---
DB_PATH = "grief_data.db"
# The threshold for rapid block breaking detection
BLOCK_BREAK_THRESHOLD = 30
# The timeframe in seconds to check for rapid block breaking
BLOCK_BREAK_TIMEFRAME_SECONDS = 10

logger = logging.getLogger(__name__)

async def analyze_event(event_data: dict, websocket):
    """
    Analyzes an event and triggers alerts if necessary.
    This is the main entry point for the analyzer. It dispatches events
    to more specific analysis functions based on event type.
    """
    if event_data.get("eventType") == "BlockBreak":
        await _check_rapid_block_break(event_data, websocket)
    # Future event types can be dispatched here
    # elif event_data.get("eventType") == "PlayerChat":
    #     await _check_spam(event_data, websocket)


async def _check_rapid_block_break(event_data: dict, websocket):
    """Checks if a player is breaking blocks too quickly."""
    try:
        player_uuid = event_data.get("playerUUID")
        if not player_uuid:
            return

        player_name = event_data.get("playerName", "UnknownPlayer")
        server_id = websocket.request_headers.get("Server-ID")

        # Timestamps are stored as ISO 8601 strings (e.g., '2023-10-27T10:00:00.123Z')
        # SQLite can compare these strings lexicographically, which works for this format.
        timestamp_str = event_data["timestamp"]
        current_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        time_limit = current_time - timedelta(seconds=BLOCK_BREAK_TIMEFRAME_SECONDS)
        # Format back to the string format used in the DB
        time_limit_str = time_limit.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM events
                WHERE event_type = 'BlockBreak'
                  AND player_uuid = ?
                  AND server_id = ?
                  AND timestamp >= ?
                """,
                (player_uuid, server_id, time_limit_str)
            )
            result = await cursor.fetchone()
            block_break_count = result[0] if result else 0

        logger.debug(f"Player {player_name} broke {block_break_count} blocks in the last {BLOCK_BREAK_TIMEFRAME_SECONDS}s (Threshold: {BLOCK_BREAK_THRESHOLD}).")

        if block_break_count > BLOCK_BREAK_THRESHOLD:
            logger.warning(f"GRIEF ALERT: Player {player_name} broke {block_break_count} blocks on server {server_id}.")

            block_info = event_data.get("block", {})
            location_str = f"world: {block_info.get('world', 'N/A')}, x: {block_info.get('x', 'N/A')}, y: {block_info.get('y', 'N/A')}, z: {block_info.get('z', 'N/A')}"

            alert_message = {
                "type": "grief_alert",
                "player": player_name,
                "reason": f"Broke {block_break_count} blocks in {BLOCK_BREAK_TIMEFRAME_SECONDS} seconds",
                "location": location_str
            }
            await websocket.send(json.dumps(alert_message))
            logger.info(f"Sent grief alert for player {player_name} to server {server_id}.")

    except Exception as e:
        logger.error(f"Error during rapid block break analysis: {e}", exc_info=True)
