def run_prediction():
    print("Available coins:", ", ".join(symbol_map.keys()))
    coin = input("Enter coin symbol (e.g. BTC, ETH, SOL): ").upper()
    interval = input("Enter interval ('1h' for hourly, '1d' for daily): ").strip()
    steps = int(input("Enter number of forecast steps (e.g. 24 for 24h, 7 for 7d): "))

    # Build model path automatically
    model_path = f"{coin.lower()}_{'hourly' if interval=='1h' else 'daily'}_lstm.keras"

    forecast = predict_future_price_inr(
        coin=coin,
        interval=interval,
        forecast_steps=steps,
        model_path=model_path
    )

    print("\n=== Forecast Results ===")
    print(forecast)
    

run_prediction()