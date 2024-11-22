from flask import Flask, render_template, jsonify, request
import requests
import threading
import logging
import time
import sqlite3

app = Flask(__name__)

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Create a SQLite database to store cryptocurrency prices
def create_database():
    conn = sqlite3.connect("crypto_data.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency_id TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Function to store cryptocurrency data in the SQLite database
def store_crypto_prices(data):
    conn = sqlite3.connect("crypto_data.db")
    cursor = conn.cursor()
    
    for item in data:
        cursor.execute('''
            INSERT INTO crypto_prices (currency_id, price)
            VALUES (?, ?)
        ''', (item['id'], item['current_price']))
    
    conn.commit()
    conn.close()

# Function to fetch cryptocurrency prices
def fetch_crypto_prices():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': 'inr',
        'order': 'market_cap_desc',
        'per_page': 10,
        'page': 1,
        'sparkline': False
    }

    backoff_time = 1

    while True:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Store the data in the database
            store_crypto_prices(data)
            
            logging.info("Successfully fetched and stored crypto prices.")
            break

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logging.warning("Rate limit exceeded. Backing off...")
                time.sleep(backoff_time)
                backoff_time *= 2
            else:
                logging.error(f"Error while fetching prices: {e}")
                break
        except Exception as e:
            logging.error(f"Unexpected error while fetching prices: {e}")
            break

# Periodic task to fetch cryptocurrency prices every 5 minutes
def fetch_prices_periodically():
    while True:
        fetch_crypto_prices()
        time.sleep(300)

# Route to render the main page
@app.route('/')
def index():
    return render_template("index.html")

# Route to get the latest cryptocurrency data from the database
@app.route('/crypto_data')
def crypto_data_route():
    conn = sqlite3.connect("crypto_data.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT currency_id, price, timestamp 
        FROM crypto_prices 
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    rows = cursor.fetchall()
    conn.close()

    data = [{'currency_id': row[0], 'price': row[1], 'timestamp': row[2]} for row in rows]
    return jsonify(data)

# Route to get average and latest price comparison for a cryptocurrency
@app.route('/crypto_compare/<crypto_id>', methods=['GET'])
def crypto_compare(crypto_id):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({"error": "Please provide both start_date and end_date parameters."}), 400

    conn = sqlite3.connect("crypto_data.db")
    cursor = conn.cursor()

    # Get average price over the specified date range
    cursor.execute('''
        SELECT AVG(price) 
        FROM crypto_prices 
        WHERE currency_id = ? AND DATE(timestamp) BETWEEN DATE(?) AND DATE(?)
    ''', (crypto_id, start_date, end_date))
    avg_price_row = cursor.fetchone()

    # Check if there is data within the selected date range
    if avg_price_row[0] is None:
        return jsonify({
            "error": f"No data available for {crypto_id} within the selected date range. "
                     "Please try expanding the date range."
        }), 404

    # Get the latest price within the specified end date
    cursor.execute('''
        SELECT price, timestamp 
        FROM crypto_prices 
        WHERE currency_id = ? AND DATE(timestamp) <= DATE(?)
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (crypto_id, end_date))
    latest_price_row = cursor.fetchone()
    conn.close()

    if latest_price_row is None:
        return jsonify({
            "error": f"No latest price data for {crypto_id} up to the selected end date."
        }), 404

    avg_price = avg_price_row[0]
    latest_price, latest_timestamp = latest_price_row

    # Calculate the percentage difference
    percentage_diff = ((latest_price - avg_price) / avg_price) * 100

    # Determine comparison message
    comparison = "higher than" if latest_price > avg_price else "lower than" if latest_price < avg_price else "equal to"
    
    return jsonify({
        'crypto_id': crypto_id,
        'latest_price': latest_price,
        'latest_timestamp': latest_timestamp,
        'average_price': round(avg_price, 2),
        'percentage_diff': round(percentage_diff, 2),
        'comparison': f"The latest price is {comparison} the average price by {round(abs(percentage_diff), 2)}%."
    })

if __name__ == "__main__":
    create_database()
    threading.Thread(target=fetch_prices_periodically, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)