from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from celery_app import get_prediction_data
import os
import traceback

app = Flask(__name__)
app.secret_key = 'your_very_secret_key'

# Simple in-memory user store for demonstration
users = {}  # { "username": "password" }
prediction_history = {} # { "username": [...] }

@app.route("/")
def index():
    if 'username' in session:
        return render_template('index.html', logged_in=True, username=session['username'])
    return render_template('index.html', logged_in=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.get(username) == password:
            session['username'] = username
            if username not in prediction_history:
                prediction_history[username] = []
            return redirect(url_for('predict'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template('signup.html', error="Username already exists")
        users[username] = password
        session['username'] = username
        prediction_history[username] = []
        return redirect(url_for('predict'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/predict")
def predict():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('predict.html')

@app.route("/about")
def about():
    return render_template('about.html')

# --- API Routes ---

@app.route('/api/predict', methods=['POST'])
def api_predict():
    if 'username' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    username = session['username']
    data = request.json
    coin = data.get('coin')
    interval_type = data.get('interval_type')
    print(f"Received prediction request for {coin} ({interval_type}). Sending to Celery...")

    try:
        # Send task to Celery worker
        task = get_prediction_data.delay(coin, interval_type)
        # Wait for the result with a 30-second timeout
        result = task.get(timeout=30) 
        
        # Store result in user's history
        prediction_history[username].insert(0, result)
        print("Prediction task successful. Sending data to frontend.")
        return jsonify({"success": True, "data": result})
    except Exception as e:
        print("--- AN ERROR OCCURRED DURING PREDICTION ---")
        traceback.print_exc()
        print("-----------------------------------------")
        error_message = f"Prediction failed: {e.__class__.__name__}. Check Celery worker terminal for details."
        return jsonify({"success": False, "message": error_message}), 500

@app.route('/api/history')
def api_history():
    if 'username' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    username = session['username']
    return jsonify({"success": True, "history": prediction_history.get(username, [])})

if __name__ == '__main__':
    app.run(debug=True)

