import re
import sqlite3
import hmac
import hashlib
import time
import requests


response = requests.get("https://api.exchange.coinbase.com/products")

def create_db():
    # Connect to the database (/creating it if it doesn't exist)
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    # Create the data_candles table
    cursor.execute(
        "CREATE TABLE if not exists data_candles(id INTEGER PRIMARY KEY AUTOINCREMENT, date INT, high REAL, low REAL, open REAL, close REAL, volume REAL)"
    )
    # Create the data_full table
    cursor.execute(
        "CREATE TABLE if not exists data_full(id INTEGER PRIMARY KEY AUTOINCREMENT, uuid TEXT, traded_crypto REAL, price REAL, created_at INT, side TEXT)"
    )
    # Create the temp table
    cursor.execute(
        "CREATE TABLE if not exists temp(id INTEGER PRIMARY KEY AUTOINCREMENT, cex TEXT, trading_pair TEXT, duration TEXT, table_name TEXT, last_check INT, startdate INT, last_id INT)"
    )
    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# LIST OF ALL AVAILABLE CRYPTOCURRENCIES
def getAllCrypto():
    uri = 'https://api.pro.coinbase.com/currencies'
    response = requests.get(uri).json()

    for i in range(len(response)):
        if response[i]['details']['type'] == 'crypto':
            print(response[i]['id'])


def getDepth(direction="ask", pair="BTC-USD"):
    response = requests.get('https://api.exchange.coinbase.com/products/'+pair+'/book?level=1').json()
    
    if direction == 'ask' : print('Best ask : ',response['asks'])
    elif direction == 'bid': print('Best bid : ',response['bids'])
    else : print("You need to ask for ask, or bid, but not")


# GET ORDER BOOK FOR AN ASSET
def getOrderBook(asset):
    url = "https://api.exchange.coinbase.com/products/" + asset + "/book?level=2"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)

    print(response.text)


def refreshDataCandle(pair, duration):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    time = "".join(re.findall("[\d)]+",duration))
    duration = 60*int(time)

    if duration not in [60, 300, 900, 3600, 21600, 86400]:
        print("Error: Invalid duration")
    else:

        response = requests.get('https://api.exchange.coinbase.com/products/' + pair + '/candles?granularity=' + str(duration)).json()

        for candle in response:
            cursor.execute(
                "INSERT OR REPLACE INTO data_candles (date, high, low, open, close, volume) VALUES (?,?,?,?,?,?)",
                (candle[0], candle[2], candle[3], candle[4], candle[1], candle[5])
            )
    conn.commit()
    conn.close()


def refreshData(pair='BTC-USD'):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    response = requests.get(f'https://api.exchange.coinbase.com/products/{pair}/trades')

    if response.status_code == 200:
        data = response.json()
        for trade in data:
            print(trade)
            cursor.execute(
                "INSERT OR REPLACE INTO data_full (uuid, traded_crypto, price, created_at, side) VALUES (?,?,?,?,?)",
                (trade["trade_id"], trade["size"], pair, trade["time"], trade["side"])
            ) 
            conn.commit()
    else:
        print("An error occurred:", response.status_code)
    conn.close()


def createOrder(api_key, secret_key, direction, price, amount, pair='BTC-USD', orderType='LimitOrder'):
    params = {
        'product_id': pair,
        'side': direction,
        'price': price,
        'size': amount,
        'type': orderType,
    }

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'CoinbaseAPI/1.0',
        'CB-ACCESS-KEY': api_key,
        'CB-ACCESS-TIMESTAMP': str(time.time()),
        'CB-ACCESS-SIGN': hmac.new(secret_key.encode(), ''.join(
            [
                'POST',
                '/orders',
                '',
                'Content-Type: application/json',
                'User-Agent: CoinbaseAPI/1.0',
                'CB-ACCESS-KEY:' + api_key,
                'CB-ACCESS-TIMESTAMP:' + str(time.time()),
            ]
        ).encode(), hashlib.sha256).hexdigest()
    }

    response = requests.post('https://api.exchange.coinbase.com/orders', json=params, headers=headers)

    if response.status_code == 200:
        print(response.json())
    else:
        print(f'An error occurred: {response.status_code}')

def cancelOrder(api_key, secret_key, uuid): #you will need your api_key and secret_key
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'CoinbaseAPI/1.0',
        'CB-ACCESS-KEY': api_key,
        'CB-ACCESS-TIMESTAMP': str(time.time()),
        'CB-ACCESS-SIGN': hmac.new(secret_key.encode(), ''.join(
            [
                'DELETE',
                '/orders/' + uuid,
                '',
                'Content-Type: application/json',
                'User-Agent: CoinbaseAPI/1.0',
                'CB-ACCESS-KEY:' + api_key,
                'CB-ACCESS-TIMESTAMP:' + str(time.time()),
            ]
        ).encode(), hashlib.sha256).hexdigest()
    }

    response = requests.delete(f'https://api.exchange.coinbase.com/orders/{uuid}', headers=headers)

    if response.status_code == 200:
        print(response.json())
    else:
        print(f'An error occurred: {response.status_code}')
