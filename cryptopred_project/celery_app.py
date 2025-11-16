import os
import requests
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import warnings
from celery import Celery
from pathlib import Path

# Suppress unnecessary TensorFlow and UserWarning messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')

# --- Celery Configuration ---
celery = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# --- Symbol Mapping ---
symbol_map = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "LTC": "LTCUSDT",
    "XRP": "XRPUSDT", "DOGE": "DOGEUSDT", "SOL": "SOLUSDT", "BCH": "BCHUSDT"
}

# Get the absolute path to the project directory
BASE_DIR = Path(__file__).resolve().parent

@celery.task
def get_prediction_data(coin: str, interval_type: str):
    """
    Fetches live data, runs a prediction model, and returns the formatted data.
    """
    try:
        # === 1. Set Parameters ===
        binance_interval = "1h" if interval_type == 'hourly' else "1d"
        forecast_steps = 24 if interval_type == 'hourly' else 30
        
        symbol = symbol_map.get(coin.upper())
        if not symbol:
            raise ValueError(f"Invalid coin symbol: {coin}")

        # Build a robust, absolute path to the model file
        interval_abbr = "1h" if interval_type == 'hourly' else "1d"
        model_path = BASE_DIR / "models" / f"{coin.lower()}_{interval_abbr}_lstm.keras"
        
        if not os.path.exists(model_path):
            # This error will now be very specific in the Celery terminal
            raise FileNotFoundError(f"Model file not found at absolute path: {model_path}")

        # === 2. Fetch Live Data from Binance ===
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": binance_interval, "limit": 1000}
        data = requests.get(url, params=params).json()

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume",
                                         "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close"] = df["close"].astype(float)
        
        # === 3. Preprocess Data and Scale ===
        scaler = MinMaxScaler()
        scaled_prices = scaler.fit_transform(df[["close"]].values.astype("float32"))

        # === 4. Load Model and Make Predictions ===
        model = load_model(str(model_path), compile=False)
        lookback = model.input_shape[1]

        last_window = scaled_prices[-lookback:].reshape(1, lookback, 1)
        future_predictions_scaled = []

        for _ in range(forecast_steps):
            next_pred_scaled = model.predict(last_window, verbose=0)[0, 0]
            future_predictions_scaled.append(next_pred_scaled)
            last_window = np.append(last_window[:, 1:, :], [[[next_pred_scaled]]], axis=1)

        # === 5. Format the Results for the API ===
        future_prices_usd = scaler.inverse_transform(np.array(future_predictions_scaled).reshape(-1, 1)).flatten()
        
        freq = "H" if interval_type == 'hourly' else "D"
        last_timestamp = df["timestamp"].iloc[-1]
        future_timestamps = pd.date_range(start=last_timestamp, periods=forecast_steps + 1, freq=freq)[1:]

        response_data = {
            "coin": coin,
            "interval": interval_type,
            "predictions": [
                {
                    "timestamp": ts.isoformat(),
                    "predicted_price_usd": round(float(price), 4)
                }
                for ts, price in zip(future_timestamps, future_prices_usd)
            ]
        }
        
        return response_data
    except Exception as e:
        # This print statement is crucial for debugging
        print(f"!!! CELERY TASK FAILED: {e}")
        raise

