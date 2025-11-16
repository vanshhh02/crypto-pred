import tensorflow as tf

# Load your already trained model
# Replace this with the actual path to YOUR original model file
model = tf.keras.models.load_model("/Users/vanshagarwal/Documents/GitHub/ML-Driven-Web-Platform-for-Cryptocurrency-Price-Forecasting_August_2025/predictFuture-app/models/btc_1h_lstm.keras")
# Save it again in the correct location for your app
model.save('predictFuture-app/models/bch_hourly_lstm.keras')