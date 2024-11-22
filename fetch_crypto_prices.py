import sqlite3
import requests
from datetime import datetime
import os

# Define the cryptocurrency IDs you want to track (now with 10 cryptocurrencies)
CRYPTOCURRENCIES = [
    "bitcoin", "ethereum", "dogecoin", "litecoin", "polkadot",
    "binancecoin", "solana", "cardano", "ripple", "uniswap"
]
API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Database connection function
def create_database():
    conn = sqlite3.connect("/home/ubuntu/crypto_dashboard/crypto_data.db", timeout=10)
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

# Function to fetch and store cryptocurrency prices
def fetch_and_store_prices():
    # Requesting prices for all 10 cryptocurrencies in INR
    params = {
        "ids": ",".join(CRYPTOCURRENCIES),
        "vs_currencies": "inr"  # Fetching prices in INR
    }
    response = requests.get(API_URL, params=params)

    if response.status_code == 200:
        prices = response.json()
        print("Fetched prices:", prices)  # Log the response to check the structure

        # Check if 'inr' data exists for each cryptocurrency
        for currency_id, data in prices.items():
            if "inr" in data:
                price = data["inr"]  # Get the price in INR
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"Preparing to insert {currency_id} with price: ₹{price} at {timestamp}")  # Log insertion

                try:
                    # Check if database is accessible and working
                    conn = sqlite3.connect("crypto_data.db")
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO crypto_prices (currency_id, price, timestamp)
                        VALUES (?, ?, ?)
                    ''', (currency_id, price, timestamp))
                    conn.commit()
                    conn.close()

                    print(f"Stored {currency_id} price: ₹{price} at {timestamp}")
                except sqlite3.Error as e:
                    print(f"Error inserting data for {currency_id}: {e}")
            else:
                print(f"No INR data available for {currency_id}")
    else:
        print("Failed to fetch data:", response.status_code, response.text)

if __name__ == "__main__":
    if not os.path.exists("crypto_data.db"):
        print("Database file not found!")
    create_database()
    fetch_and_store_prices()