import data_handling as d
import json
import csv
import datetime as dt
from binance.client import Client 
import os 
import time
import math
import argparse

with open('config/config.json', 'r') as config:
    configs = json.load(config)
    client = Client(configs["api"], configs["secret"])
    alts = configs["alts"]

#lot size tracker
lot_size = {}
#set the starting BTC investment given to the bot (for reporting purposes - see gain/loss by the bot against if you had just HODLed). This is of course optional, but if no value is supplied the report() function should be removed
starting_amt_btc = 0.00189
#rate limiting buys and reports - don't touch these. 
next_buytime = 0
next_report = 0
#auto-start function while waiting for initial BTC buy order to fill (for when account has no BTC)- to use this, uncomment the following line and the commented out lines in the main function
#start_trading = False 

def main():
    #global start_trading
    parser = argparse.ArgumentParser()
    parser.add_argument('--t', required=False, dest='t', action='store_true', help="use --t flag for testing mode (transactions are not sent to Binance API)")
    args = parser.parse_args()
    while True:
        time.sleep(120) #set to run every 2 minutes to minimize system usage (no advantage is gained from running at smaller interval)
        #if start_trading == False:
        #    balances = d.get_asset_balances()
        #    if len(balances) != 0:
        #        start_trading = True
        #    else:
        #        continue
        print("Calling trade")
        print(dt.datetime.now())
        trade(args.t) 
        report()

def report():
    global next_report
    global starting_amt_btc
    init_report()
    if next_report != 0:
        if dt.datetime.now() < next_report:
            return
    if not os.path.exists("transactions.log"):
        return
    time = dt.datetime.now.strftime("%d/%m/%Y %H:%M:%S")
    value_of_portfolio = d.get_account_balance_USD()
    value_of_btc = starting_amt_btc * d.get_current_price("BTCBUSD")
    gain = ((value_of_portfolio - value_of_btc)/value_of_btc)*100
    with open("portfolio_value.csv", 'a') as pv:
        writer =csv.DictWriter(pv, fieldnames = ["time", "portfolio value", "value of initial investment", "percentage gain/loss"])
        row = {'time': time, 'portfolio value': value_of_portfolio, 'value of initial investment': value_of_btc, 'percentage gain/loss': gain}
        writer.writerow(row)
    next_report = dt.datetime.now() + dt.timedelta(minutes=10)
        
def init_report():
    if os.path.exists("portfolio_value.csv"):
        return
    with open('portfolio_value.csv', 'w') as pv:
        writer = csv.DictWriter(pv, fieldnames = ["time", "portfolio value", "value of initial investment", "percentage gain/loss"])
        writer.writeheader()


def trade(test_mode):
    global next_buytime
    if buy():
        print("buy time")
        alt = choose_alt_buy()
        if alt is None:
            return
        else:
            symbol = alt+"BTC"
            bap = get_lot_size(symbol)
            if bap is None:
                print("something went wrong, invalid trading pair")
                return
            qty = float(d.get_asset_free_balance("BTC"))
            #btc_price = d.get_current_price("BTCUSDT")
            #default buy amt is minimum transaction value of 0.0001 btc 
            if qty < 0.00011:
                return
            else:
                btc_qty = 0.0001100
            price = float(d.get_current_price(symbol))
            order_qty=round(btc_qty/price,bap)
            price = format(price, '.8f')
            print(price, order_qty, alt)
            if test_mode:
                print(alt, order_qty, price)
                #TODO: test logs 
                return
            order = client.order_limit_buy(symbol=symbol,quantity=order_qty,price=price)
            print(order)
            d.log_transaction(alt, "buy", price, btc_qty, order_qty)
            next_buytime = dt.datetime.now() + dt.timedelta(minutes=15)
    elif sell():
        print("sell time")
        alt = choose_alt_sell()
        if alt is None:
            return
        else:
            symbol = alt+"BTC"
            bap = get_lot_size(symbol)
            if bap is None:
                print("something went wrong, invalid trading pair")
                return
            qty = float(d.get_asset_free_balance(alt))
            order_qty = round(qty/2,7)
            price = float(d.get_current_price(symbol))
            if price * order_qty < 0.0001:
                if price * qty < 0.0001:
                    return
                else:
                    order_qty = round(0.0001/price,bap)
            order = client.limit_order_sell(symbol=symbol, quantity=order_qty, price=price)
            d.log_transaction(alt,"sell",price, (price * order_qty), order_qty)


def buy():
    #if BTC dominance up, price up or sideways, and strong movement towards greed
    if (d.get_btc_dominance_change() > 0 
    and d.get_current_price("BTCUSDT") - d.get_sma(7, "BTCUSDT") > 0 
    and (d.get_fear_index_change_nominal("d") >= 10 or d.get_fear_index_change_nominal("w") >= 20)):
        return True
    return False

def sell():
    if (d.get_btc_dominance_change() < 0 
    and d.get_current_price("BTCUSDT") - d.get_sma(7,"BTCUSDT") < 0 
    and (d.get_fear_index_change_nominal("d") <= -10 or d.get_fear_index_change_nominal("w") <= -20)):
        return True
    return False

def get_last_24h(buy_or_sell):
    if not os.path.exists("transactions.log"):
        return []
    with open("transactions.log", 'r') as t:
        alts = []
        reader = csv.reader(t)
        for row in reversed(list(reader)):
            if row[1] != buy_or_sell:
                continue
            time = row[-1]
            time_obj = dt.datetime.striptime(time, "%d/%m/%Y %H:%M:%S")
            now = dt.datetime.now()
            if now - dt.timedelta(hours=24) <= time_obj <= now:
                alts.append(row[0])
            else:
                return alts
    return alts

def get_lot_size(symbol): 
    global lot_size
    if symbol not in lot_size.keys():
        with open('config/lot_size.json', 'r') as ls:
            data = json.load(ls)
            for ds in data["symbols"]:
                if ds["symbol"] == symbol:
                    bap = ds["stepSize"]
                    ls = 0:
                    decimal =False
                    for i in bap:
                        if i == '1':
                            ls += 1
                            break
                        elif i == '.':
                            decimal=True
                            continue
                        else:
                            if decimal==True:
                                ls+= 1
            lot_size[symbol] = ls
            return ls
    else:
        return lot_size[symbol]
    return None

def choose_alt_buy():
    global next_buytime
    prices = get_relative_prices(alts)
    #remove alts that have trades in the last 24 hrs 
    rm = get_last_24h("buy")
    #rate limiting
    if next_buytime != 0:
        if dt.datetime.now() < next_buytime:
            return None
    #TODO :mechanism for not buying asset in freefall (possible? Relative Strength Index?)
    #for key in prices.keys():
    #    if d.in_freefall(key):
    #        rm.append(key)
    #remove unwanted buys 
    if len(rm) == len(prices):
        return None
    for key in rm:
        del prices[key]
    #find best prices buy option
    target = min(prices.values())
    for key, value in prices.items():
        if value == target:
            return key

def get_relative_prices(altlist):
    if len(altlist) == 0:
        return {}
    relative_prices = {}
    for alt in altlist:
        symbol = alt+"BTC"
        sma = d.get_sma(30, symbol)
        relative_prices[alt] = (d.get_current_price(symbol) - sma)/sma
    return relative_prices

def choose_alt_sell():
    owned = d.get_asset_balances()
    owned_list = []
    for coin in owned:
        if coin["asset"] != "BTC" and coin["asset"] != "USDT":
            owned_list.append(coin["asset"])
    if len(owned_list) == 0:
        return None
    prices = get_relative_prices(owned_list)
    for key in get_last_24h("sell"):
        del prices[key]
    target = max(prices.values())
    while True:
        for key, value in prices.items():
            if value == target:
                if d.get_current_price(key+"BTC") > d.get_avg_buy_price(key):
                    return key
                else:
                    prices[key] = -math.inf
                    target = max(prices.values())
        if prices.values().count(-math.inf) == len(prices.values()):
            return None


if __name__ == '__main__':
    main()