import os
import requests
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# --- Symbol map ---
symbol_map = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "DOGE": "DOGEUSDT", 
     "LTC": "LTCUSDT", "SOL": "SOLUSDT",
    "ADA": "ADAUSDT", 
    "BNB": "BNBUSDT", 
     "XRP": "XRPUSDT"
}

def predict_future_price_inr(coin: str, interval: str, forecast_steps: int = 24, 
                             rate_inr_per_usd: float = 85.96, model_path: str = None):
    """
    Predicts future prices of a cryptocurrency in INR using a trained LSTM model.

    Args:
        coin (str): Coin symbol like "BTC", "ETH", "SOL"
        interval (str): Binance interval ("1h" for hourly, "1d" for daily)
        forecast_steps (int): How many steps to forecast (hours if '1h', days if '1d')
        rate_inr_per_usd (float): Conversion rate from USD to INR
        model_path (str): Path to the trained model file (.keras or .h5). 
                          If None, auto-selects based on coin & interval.

    Returns:
        pd.DataFrame: DataFrame with forecasted timestamps and predicted INR prices
    """
    # --- Resolve symbol ---
    symbol = symbol_map.get(coin.upper(), "BTCUSDT")

    # --- Auto-select model file ---
    if model_path is None:
        model_path = f"{coin.lower()}_{'hourly' if interval=='1h' else 'daily'}_lstm.keras"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}. Train & save your model first.")

    # --- Fetch historical data from Binance ---
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": 1000}
    data = requests.get(url, params=params).json()

    df = pd.DataFrame(data, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","qav","num_trades","tbbav","tbqav","ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df["close"] = df["close"].astype(float)

    # --- Scale ---
    scaler = MinMaxScaler()
    values = df[["close"]].values.astype("float32")
    scaled = scaler.fit_transform(values)

    # --- Load Model ---
    model = load_model(model_path)
    LOOKBACK = model.input_shape[1]

    # --- Forecast ---
    last_window = scaled[-LOOKBACK:].copy().reshape(1, LOOKBACK, 1)
    future_scaled = []

    for _ in range(forecast_steps):
        nxt = model.predict(last_window, verbose=0)[0, 0]
        future_scaled.append(nxt)
        last_window = np.concatenate([last_window[:,1:,:], nxt.reshape(1,1,1)], axis=1)

    # --- Inverse Transform (USD → INR) ---
    future_usd = scaler.inverse_transform(np.array(future_scaled).reshape(-1, 1)).flatten()
    future_inr = future_usd * rate_inr_per_usd

    # --- Future Timestamps ---
    freq = "H" if interval == "1h" else "D"
    future_times = pd.date_range(start=df.index[-1] + pd.Timedelta(1, unit=freq),
                                 periods=forecast_steps, freq=freq)

    # --- Output ---
    forecast_df = pd.DataFrame({
        "timestamp": future_times,
        "predicted_price_inr": future_inr
    })
    return forecast_df

