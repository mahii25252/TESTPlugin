import asyncio
import websockets
import logging
import json
import pandas as pd
import os
from datetime import datetime, timedelta, timezone
from database import init_db, log_event, add_confirmed_griefer, update_block_state, DB_PATH
from ml_analyzer import extract_features, load_model_and_predict, predict_next_action

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# A dictionary to hold connections to Minecraft servers, keyed by server_id
CONNECTED_SERVERS = {}

async def periodic_global_analyzer():
    """Periodically analyzes global player data for advanced patterns."""
    while True:
        # Adjust sleep time for production, 60 seconds is reasonable
        await asyncio.sleep(60)
        logger.info("[Global Analyzer] Starting periodic analysis...")

        try:
            # Analyze players active in the last 5 minutes
            time_threshold = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            db_path = "grief_data.db"

            async with aiosqlite.connect(db_path) as db:
                # Get players active in the last 5 minutes
                cursor = await db.execute(
                    "SELECT DISTINCT player_uuid FROM events WHERE timestamp >= ?",
                    (time_threshold,)
                )
                active_players = await cursor.fetchall()
                logger.info(f"[Global Analyzer] Found {len(active_players)} active players to analyze.")

                for (player_uuid,) in active_players:
                    # Get all events for this player in the last 5 minutes across all servers
                    cursor = await db.execute(
                        "SELECT server_id, event_type, data, player_name FROM events WHERE player_uuid = ? AND timestamp >= ?",
                        (player_uuid, time_threshold)
                    )
                    player_events = await cursor.fetchall()

                    if not player_events:
                        continue

                    df = pd.DataFrame(player_events, columns=['server_id', 'event_type', 'data', 'player_name'])

                    # --- Feature Extraction and ML Prediction ---
                    features = extract_features(df)
                    prediction, probability = load_model_and_predict(features)

                    # Define a threshold for sending an alert
                    ML_ALERT_THRESHOLD = 0.80

                    if prediction == 1 and probability > ML_ALERT_THRESHOLD:
                        player_name = df['player_name'].iloc[-1] # Get the most recent name
                        logger.warning(f"[ML-ALERT] Player {player_name} ({player_uuid[:8]}) flagged as potential griefer with probability {probability:.2f}")

                        alert_message = {
                            "type": "grief_alert",
                            "player": player_name,
                            "reason": f"ML model detected anomalous behavior (score: {probability:.2f})",
                            "location": "Across multiple servers"
                        }

                        # Send alert to all connected servers this player was active on
                        active_server_ids = df['server_id'].unique()
                        for server_id in active_server_ids:
                            if server_id in CONNECTED_SERVERS:
                                websocket = CONNECTED_SERVERS[server_id]
                                logger.info(f"Sending ML alert for player {player_name} to server {server_id}")
                                # Fire and forget the task
                                asyncio.create_task(websocket.send(json.dumps(alert_message)))

        except Exception as e:
            logger.error(f"[Global Analyzer] Error in periodic task: {e}", exc_info=True)


async def predict_and_log_action(event_data: dict):
    """Predicts the next action for a player and logs it."""
    current_action = event_data.get("eventType")
    player_name = event_data.get("playerName", "Unknown")
    if not current_action:
        return

    predicted_action = predict_next_action(current_action)

    if predicted_action:
        logger.info(f"[Action Prediction] Player {player_name} did '{current_action}'. Predicted next action: '{predicted_action}'.")


async def connection_handler(websocket, path):
    """Handles incoming WebSocket connections from Minecraft plugins."""
    server_id = websocket.request_headers.get("Server-ID")
    if not server_id:
        logger.warning("Connection refused: 'Server-ID' header missing.")
        await websocket.close(code=1011, reason="'Server-ID' header is required")
        return

    remote_address = websocket.remote_address
    logger.info(f"Server '{server_id}' connected from {remote_address}.")
    CONNECTED_SERVERS[server_id] = websocket

    try:
        async for message in websocket:
            logger.debug(f"Message from '{server_id}': {message}")

            # First, log the event to the database
            await log_event(server_id, message)

            # Then, dispatch the message to the appropriate handler.
            try:
                event_data = json.loads(message)
                event_type = event_data.get("type")

                if event_type == "grief_confirmation":
                    player_uuid = event_data.get("playerUUID")
                    player_name = event_data.get("playerName")
                    if player_uuid and player_name:
                        logger.info(f"Received grief confirmation for player {player_name} from server {server_id}.")
                        asyncio.create_task(add_confirmed_griefer(player_uuid, player_name, message))
                else:
                    # Handle world state updates for relevant events
                    if event_type in ["BlockBreak", "BlockPlace"]:
                        block_data = event_data.get("block", {})
                        world = block_data.get("world")
                        x, y, z = block_data.get("x"), block_data.get("y"), block_data.get("z")

                        if all(v is not None for v in [world, x, y, z]):
                            new_block_type = "AIR" if event_type == "BlockBreak" else block_data.get("type", "UNKNOWN")
                            asyncio.create_task(update_block_state(server_id, world, x, y, z, new_block_type))

                    # Also, predict the next action
                    asyncio.create_task(predict_and_log_action(event_data))

            except json.JSONDecodeError:
                logger.warning(f"Could not decode JSON from '{server_id}': {message}")

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Server '{server_id}' disconnected: {e.code} {e.reason}")
    except Exception as e:
        logger.error(f"An unexpected error occurred for server '{server_id}': {e}", exc_info=True)
    finally:
        if server_id in CONNECTED_SERVERS:
            del CONNECTED_SERVERS[server_id]
            logger.info(f"Removed server '{server_id}' from active connections.")

async def periodic_db_cleanup():
    """Periodically checks DB size and cleans up old records if it exceeds the limit."""
    # 500 GB in bytes. Set threshold at 95%.
    DB_SIZE_LIMIT_GB = 500
    DB_SIZE_LIMIT_BYTES = DB_SIZE_LIMIT_GB * (1024**3)
    CLEANUP_THRESHOLD_BYTES = DB_SIZE_LIMIT_BYTES * 0.95

    while True:
        # Check every hour
        await asyncio.sleep(3600)

        try:
            db_size = os.path.getsize(DB_PATH)
            logger.info(f"[DB Cleanup] Current DB size: {db_size / (1024**3):.2f} GB. Limit: {DB_SIZE_LIMIT_GB} GB.")

            if db_size > CLEANUP_THRESHOLD_BYTES:
                logger.warning(f"[DB Cleanup] DB size ({db_size / (1024**3):.2f} GB) exceeds threshold. Starting cleanup...")

                async with aiosqlite.connect(DB_PATH) as db:
                    # Get total rows
                    cursor = await db.execute("SELECT COUNT(*) FROM events")
                    total_rows = (await cursor.fetchone())[0]

                    # Calculate 10% of rows to delete
                    rows_to_delete = int(total_rows * 0.1)
                    if rows_to_delete == 0:
                        logger.info("[DB Cleanup] No rows to delete.")
                        continue

                    logger.info(f"[DB Cleanup] Attempting to delete the oldest {rows_to_delete} rows ({total_rows} total)...")

                    # Using subquery to get IDs of oldest rows
                    delete_cursor = await db.execute(f"DELETE FROM events WHERE id IN (SELECT id FROM events ORDER BY id ASC LIMIT {rows_to_delete})")
                    await db.commit()

                    deleted_count = delete_cursor.rowcount
                    logger.info(f"[DB Cleanup] Deleted {deleted_count} rows. Now running VACUUM to reclaim disk space. This may take a while...")

                    # VACUUM can be slow and blocks the DB.
                    await db.execute("VACUUM")
                    await db.commit()

                    logger.info("[DB Cleanup] VACUUM complete. Cleanup finished.")
        except FileNotFoundError:
            logger.info("[DB Cleanup] Database file not found, skipping cleanup check.")
        except Exception as e:
            logger.error(f"[DB Cleanup] Error during database cleanup: {e}", exc_info=True)


async def start_server():
    """Initializes the database and starts the WebSocket server and background tasks."""
    await init_db()

    logger.info("Starting background tasks...")
    asyncio.create_task(periodic_global_analyzer())
    asyncio.create_task(periodic_db_cleanup())

    host = "0.0.0.0"
    port = 8765

    async with websockets.serve(connection_handler, host, port):
        logger.info(f"Python WebSocket server is running on ws://{host}:{port}")
        await asyncio.Future()  # Keep the server running indefinitely

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server is shutting down.")
