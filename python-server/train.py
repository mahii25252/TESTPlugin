import pandas as pd
import sqlite3
import logging
import joblib
import json
from collections import defaultdict
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from ml_analyzer import FEATURE_COLUMNS # Import to ensure consistency

# --- Configuration ---
DB_PATH = "grief_data.db"
GRIEF_MODEL_PATH = "grief_model.joblib"
ACTION_MODEL_PATH = "action_prediction_model.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_data():
    """Fetches all event data and confirmed griefer UUIDs from the database."""
    logging.info(f"Connecting to database at '{DB_PATH}'...")
    with sqlite3.connect(DB_PATH) as con:
        events_df = pd.read_sql_query("SELECT * FROM events", con)
        griefers_df = pd.read_sql_query("SELECT player_uuid FROM confirmed_griefers", con)
    logging.info(f"Fetched {len(events_df)} events and {len(griefers_df)} confirmed griefers.")
    return events_df, griefers_df['player_uuid'].tolist()

def create_features_and_labels(events_df, confirmed_griefers):
    """
    Performs feature engineering and labeling.
    This is a simplified example aggregating over a player's entire history.
    A better model would use features from sliding time windows.
    """
    logging.info("Engineering features for each player...")

    # Group by player to create a single feature set for each player
    player_features = events_df.groupby('player_uuid').apply(lambda df: pd.Series({
        'break_count': len(df[df['event_type'] == 'BlockBreak']),
        'place_count': len(df[df['event_type'] == 'BlockPlace']),
        'move_count': len(df[df['event_type'] == 'PlayerMove']),
        'servers_count': df['server_id'].nunique()
    })).reset_index()

    # Ensure the columns match what the predictor expects
    player_features = player_features[['player_uuid'] + FEATURE_COLUMNS]

    # Label the data
    player_features['is_griefer'] = player_features['player_uuid'].isin(confirmed_griefers).astype(int)

    logging.info(f"Created feature set for {len(player_features)} players.")
    logging.info(f"Positive (griefer) samples: {player_features['is_griefer'].sum()}")
    logging.info(f"Negative (normal) samples: {len(player_features) - player_features['is_griefer'].sum()}")

    return player_features

def train_grief_model(events_df, confirmed_griefers):
    """Trains and saves the grief detection model."""
    logging.info("--- Training Grief Detection Model ---")
    if not confirmed_griefers:
        logging.warning("No confirmed griefers found. Grief model will not be effective.")

    player_data = create_features_and_labels(events_df, confirmed_griefers)
    if len(player_data) < 10:
        logging.error("Not enough player data to train grief model (less than 10 players).")
        return

    has_both_classes = player_data['is_griefer'].nunique() > 1
    X = player_data[FEATURE_COLUMNS]
    y = player_data['is_griefer']

    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', oob_score=True)

    if has_both_classes:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        model.fit(X_train, y_train)
        logging.info(f"Grief model test accuracy: {model.score(X_test, y_test):.3f}")
    else:
        model.fit(X, y)

    logging.info(f"Grief model OOB score: {model.oob_score_:.3f}")
    joblib.dump(model, GRIEF_MODEL_PATH)
    logging.info(f"Grief model saved to '{GRIEF_MODEL_PATH}'")

def train_action_predictor(events_df):
    """Trains and saves the next-action prediction model (Markov Chain)."""
    logging.info("--- Training Action Prediction Model ---")
    transitions = defaultdict(lambda: defaultdict(int))

    # Sort events by player and time to process them in order
    events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
    events_df = events_df.sort_values(by=['player_uuid', 'timestamp'])

    # Group by player and create sequences of actions
    sequences = events_df.groupby('player_uuid')['event_type'].apply(list)

    for seq in sequences:
        for i in range(len(seq) - 1):
            current_action = seq[i]
            next_action = seq[i+1]
            transitions[current_action][next_action] += 1

    # Convert counts to probabilities
    prob_matrix = {}
    for current_action, next_actions in transitions.items():
        total_transitions = sum(next_actions.values())
        prob_matrix[current_action] = {na: count / total_transitions for na, count in next_actions.items()}

    with open(ACTION_MODEL_PATH, 'w') as f:
        json.dump(prob_matrix, f, indent=4)
    logging.info(f"Action prediction model (Markov Chain) saved to '{ACTION_MODEL_PATH}'")

def main():
    """Main function to run all training pipelines."""
    events_df, confirmed_griefers = fetch_data()

    if events_df.empty:
        logging.error("No event data found. Aborting training.")
        return

    train_grief_model(events_df, confirmed_griefers)
    train_action_predictor(events_df)


if __name__ == "__main__":
    logging.info("--- Starting All Offline Training Pipelines ---")
    main()
    logging.info("--- All Training Finished ---")
