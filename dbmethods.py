from cs50 import SQL
from helpers import lookup, usd


def getstocks(user_id, db):
    symbols = db.execute("SELECT symbol FROM watch WHERE userid = :userid",
                         userid=user_id)
    stocks = []
    for symbol in symbols:
        stock = lookup(symbol['symbol'])
        if stock is not None:
            stocks.append(stock)
    return stocks


def currentstocks(user_id, db):
    stocks = []
    symbols = db.execute('select distinct symbol from store where userid = :id', id=user_id)
    for symbol in symbols:
        stock = lookup(symbol['symbol'])
        stock["stock_count"] = int(
            db.execute('SElECT SUM(shares) FROM store WHERE userid = :id AND symbol = :symbol', id=user_id,
                       symbol=stock['symbol'])[0]['SUM(shares)'])
        if stock["stock_count"] > 0:
            stock['worth'] = stock["stock_count"] * stock["price"]
            stock['worthtext'] = usd(stock["stock_count"] * stock["price"])
            stocks.append(stock)
    return stocks


def stocksmoney(list):
    stock_sum = 0
    for item in list:
        stock_sum += item['worth']
    return usd(stock_sum)
