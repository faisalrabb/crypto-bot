import sys, os
#import pandas as pd 
from binance.client import Client 
from bs4 import BeautifulSoup as bs4
import requests
import json
import datetime as dt
import csv
import math

with open('config/config.json', 'r') as config:
    configs = json.load(config)
    client = Client(configs["api"], configs["secret"])
    alts = configs["alts"]
    cmc_api = configs["cmc"]

def main():
    print(get_account_balance_USD())

def get_timestamp(days_ago):
    timest = dt.datetime.now()-dt.timedelta(days=days_ago)
    timestamp = timest.timestamp() * 1000
    return str(timestamp)

def get_sma(days, ticker):
    timestamp = get_timestamp(days)
    return get_moving_average(ticker,'1h',timestamp)

def get_daily_sma(ticker):
    timestamp = get_timestamp(1)
    return get_moving_average(ticker,'1h',timestamp)

def get_current_price(ticker):
    candle = client.get_klines(symbol=ticker, interval=Client.KLINE_INTERVAL_1MINUTE)
    return float(candle[-1][1]) 

def get_moving_average(symbol, interval, starttime):
    bars = client.get_historical_klines(symbol, interval, starttime)
    #for line in bars:
    #    del line[5:]
    #df = pd.DataFrame(bars, columns=['date', 'open', 'high', 'low', 'close'])
    total_nominal = 0
    total_periods = 0
    for b in bars:
        #print(b)
        total_nominal += float(b[4])
        total_periods += 1
    return total_nominal/total_periods

#to reduce API calls 
def calculate_moving_average(bars, days):
    #assuming hourly klines
    num_bars = days * 24
    total_nominal = 0
    total_periods = 0 
    for b in bars[-num_bars:]:
        total_nominal += float(b[4])
        total_periods += 1
    return total_nominal/total_periods

#validity testing required for this function
#def in_freefall(alt):
#    bars = client.get_historical_klines(alt+"BTC", '1h', get_timestamp(3))
#    sma = []
#    for i in range(1,4):
#        sma.append(calculate_moving_average(bars, i))
#    for i in range(1, len(sma)):
#        if sma[i] < sma[i-1]:
#            return False
#    if get_current_price(alt+"BTC") > sma[0]:
#        return False
#    return True
    


def get_metrics_latest():
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': cmc_api
    }
    r=requests.get("https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest", headers=headers)
    data = r.json()
    return data

def get_btc_dominance_change():
    data = get_metrics_latest()
    return data["data"]["btc_dominance_24h_percentage_change"]


def get_btc_dominance():
    data = get_metrics_latest()
    return data["data"]["btc_dominance"]

def get_fear_index_period(time):
    #w = week, d=day, m=month
    if time == 'd':
        val = 1
    elif time == 'w':
        val = 2
    elif time == 'm':
        val = 3
    r=requests.get("https://alternative.me/crypto/fear-and-greed-index/")
    soup = bs4(r.content, 'html.parser')
    data = soup.find_all('div', {'class': 'fng-circle'})
    return data[val].text

def get_fear_index():
    r=requests.get("https://alternative.me/crypto/fear-and-greed-index/")
    soup = bs4(r.content, 'html.parser')
    data = soup.find('div', {'class': 'fng-circle'}).text
    return data

def get_fear_index_change(period):
    #w = week, d=day, m=month
    if period == 'd':
        old_val = get_fear_index_period('d')
    elif period == 'w':
        old_val = get_fear_index_period('w')
    elif period == 'm':
        old_val = get_fear_index_period('m')
    new_val = get_fear_index()
    return (float(new_val)-float(old_val))/float(old_val)

#TODO: transition from webscraping approach to API calls for higher number of periods (between 1-7 days)
def get_fear_index_change_nominal(period):
    #w = week, d=day, m=month
    if period == 'd':
        old_val = get_fear_index_period('d')
    elif period == 'w':
        old_val = get_fear_index_period('w')
    elif period == 'm':
        old_val = get_fear_index_period('m')
    new_val = get_fear_index()
    return float(new_val)-float(old_val)

def get_account_balance_USD():
    balances = get_asset_balances()
    balance_USD = 0
    for coin in balances:
        ticker = coin["asset"]
        if ticker == "USDT":
            continue
        total = float(coin["free"]) + float(coin["locked"])
        print(total)
        symbol = ticker+"BUSD"
        price = get_current_price(symbol)
        balance_USD += price * total
    return balance_USD

def get_asset_balances():
    info = client.get_account()
    balances = info["balances"]
    result = []
    for b in balances:
        if float(b['free']) == float(b['locked']) == 0.0:
            continue
        else:
            result.append(b)
    return result

def get_asset_free_balance(ticker):
    info = client.get_account()
    balances = info["balances"]
    for b in balances:
        if b["asset"] == ticker:
            return b["free"]
    return None

def get_asset_locked_balance(ticker):
    info = client.get_account()
    balances = info["balances"]
    for b in balances:
        if b["asset"] == ticker:
            return b["locked"]
    return None

def get_avg_buy_price(alt):
    if not os.path.exists("transactions.log"):
        return -math.inf
    total_paid = 0
    qty = 0
    with open("transactions.log", 'r') as t:
        reader= csv.reader(t)
        for row in reader:
            if row[0] == alt and row[1] == "buy":
                total_paid += int(row[3])
                qty += int(row[4])
    return total_paid/qty


def log_transaction(alt, side, price_btc, quantity_btc, quantity_alt):
    print(alt + " " + side + " "+ str(price_btc) + " " + str(quantity_btc)"BTC " + quantity_alt+alt)
    #buy side quantity_btc = total btc sold, quantity_alt = total alt received
    #sell side quantity_btc = total btc received, quantity_alt = total alt sold
    side = side.lower()
    time = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open("transactions.log", 'a') as t:
        writer = csv.writer(t)
        writer.writerow([alt, side, str(price_btc), str(quantity_btc), str(quantity_alt), time])


if __name__=="__main__":
    main()