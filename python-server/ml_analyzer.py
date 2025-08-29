import joblib
import logging
import pandas as pd
import numpy as np
import json

GRIEF_MODEL_PATH = "grief_model.joblib"
ACTION_MODEL_PATH = "action_prediction_model.json"
logger = logging.getLogger(__name__)

# --- Action Prediction Model Cache ---
_action_model_cache = None


# This must be consistent between training and prediction.
# It defines the "shape" of the data the grief model expects.
FEATURE_COLUMNS = [
    'break_count',
    'place_count',
    'move_count',
    'servers_count'
]

def extract_features(df: pd.DataFrame) -> list:
    """
    Extracts a feature vector from a player's recent events DataFrame.
    The order of features in the returned list MUST match FEATURE_COLUMNS.
    """
    if df.empty:
        return [0] * len(FEATURE_COLUMNS)

    # Calculate features
    break_count = len(df[df['event_type'] == 'BlockBreak'])
    place_count = len(df[df['event_type'] == 'BlockPlace'])
    move_count = len(df[df['event_type'] == 'PlayerMove'])
    servers_count = df['server_id'].nunique()

    # The feature vector
    features = [break_count, place_count, move_count, servers_count]
    return features

def load_model_and_predict(features: list) -> tuple[int, float]:
    """
    Loads the trained grief detection model from disk and makes a prediction.
    """
    try:
        model = joblib.load(GRIEF_MODEL_PATH)

        features_array = np.array(features).reshape(1, -1)

        prediction = model.predict(features_array)[0]
        probability = model.predict_proba(features_array)[0][1]

        logger.debug(f"Grief Prediction: class={prediction}, probability={probability:.2f}")
        return int(prediction), float(probability)

    except FileNotFoundError:
        logger.warning(f"Grief model file not found at '{GRIEF_MODEL_PATH}'. ML prediction is disabled.")
        return 0, 0.0
    except Exception as e:
        logger.error(f"Error loading grief model or predicting: {e}", exc_info=True)
        return 0, 0.0

def _load_action_model():
    """Loads the action prediction model from JSON, caching it in memory."""
    global _action_model_cache
    if _action_model_cache is not None:
        return _action_model_cache

    try:
        with open(ACTION_MODEL_PATH, 'r') as f:
            _action_model_cache = json.load(f)
            logger.info(f"Action prediction model loaded from '{ACTION_MODEL_PATH}'.")
            return _action_model_cache
    except FileNotFoundError:
        logger.warning(f"Action prediction model not found at '{ACTION_MODEL_PATH}'. Next-action prediction is disabled.")
        # Set cache to an empty dict to avoid trying to load again
        _action_model_cache = {}
        return None
    except Exception as e:
        logger.error(f"Error loading action prediction model: {e}", exc_info=True)
        return None

def predict_next_action(current_action: str) -> str | None:
    """Predicts the most likely next action based on the current action."""
    model = _load_action_model()
    if not model or current_action not in model:
        return None

    next_actions = model[current_action]

    if not next_actions:
        return None
    # Return the action with the highest probability
    return max(next_actions, key=next_actions.get)
