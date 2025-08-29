import aiosqlite
import json
import logging

DB_PATH = "grief_data.db"
WORLD_DB_PATH = "world_data.db"

import time
from datetime import datetime, timezone

async def init_db():
    """Initializes all databases and creates tables if they don't exist."""
    # Initialize the main events database
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                player_uuid TEXT NOT NULL,
                player_name TEXT,
                data TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS confirmed_griefers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_uuid TEXT NOT NULL UNIQUE,
                player_name TEXT,
                timestamp TEXT NOT NULL,
                raw_data TEXT
            )
        """)
        # Create indexes for faster queries
        logging.info(f"Creating indexes for '{DB_PATH}'...")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_player_uuid ON events (player_uuid);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_events_event_type ON events (event_type);")
        await db.commit()
    logging.info(f"Database '{DB_PATH}' and its tables/indexes initialized successfully.")

    # Initialize the world state database
    async with aiosqlite.connect(WORLD_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                world_server_id TEXT NOT NULL,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                z INTEGER NOT NULL,
                block_type TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                PRIMARY KEY (world_server_id, x, y, z)
            )
        """)
        await db.commit()
    logging.info(f"Database '{WORLD_DB_PATH}' and its tables/indexes initialized successfully.")

async def log_event(server_id: str, event_json: str):
    """Parses a JSON string from the plugin and logs it to the database."""
    try:
        event_data = json.loads(event_json)

        timestamp = event_data.get("timestamp")
        event_type = event_data.get("eventType")
        player_uuid = event_data.get("playerUUID")
        player_name = event_data.get("playerName")

        if not all([server_id, timestamp, event_type, player_uuid]):
            logging.warning(f"Skipping event log due to missing essential data: {event_json}")
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO events (server_id, timestamp, event_type, player_uuid, player_name, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (server_id, timestamp, event_type, player_uuid, player_name, event_json)
            )
            await db.commit()
            logging.debug(f"Logged event from {server_id}: {event_type} by {player_name}")

    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from event: {event_json}")
    except Exception as e:
        logging.error(f"An error occurred while logging event: {e}")

async def add_confirmed_griefer(player_uuid: str, player_name: str, raw_data: str):
    """Adds or updates a player in the confirmed_griefers table."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO confirmed_griefers (player_uuid, player_name, timestamp, raw_data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(player_uuid) DO UPDATE SET
                    player_name = excluded.player_name,
                    timestamp = excluded.timestamp,
                    raw_data = excluded.raw_data
                """,
                (player_uuid, player_name, timestamp, raw_data)
            )
            await db.commit()
            logging.info(f"Added/Updated confirmed griefer: {player_name} ({player_uuid})")
    except Exception as e:
        logging.error(f"Error adding confirmed griefer {player_name}: {e}", exc_info=True)

async def update_block_state(server_id: str, world: str, x: int, y: int, z: int, block_type: str):
    """Adds or updates the state of a block in the world_data database."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    # Create a unique world identifier to prevent coordinate collisions between servers
    world_server_id = f"{server_id}_{world}"
    try:
        async with aiosqlite.connect(WORLD_DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO blocks (world_server_id, x, y, z, block_type, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(world_server_id, x, y, z) DO UPDATE SET
                    block_type = excluded.block_type,
                    last_updated = excluded.last_updated
                """,
                (world_server_id, x, y, z, block_type, timestamp)
            )
            await db.commit()
            logging.debug(f"Updated block at ({x},{y},{z}) in world '{world_server_id}' to {block_type}")
    except Exception as e:
        logging.error(f"Error updating block state: {e}", exc_info=True)
