import imp
from cs50 import SQL
from helpers import lookup, usd


def GetStocks(user_id, db):
    symbols = db.execute("SELECT symbol FROM watch WHERE userid = :userid",
                         userid=user_id)
    stocks = []
    for symbol in symbols:
        stock = lookup(symbol['symbol'])
        if stock is not None:
            stocks.append(stock)
    return stocks


def GetUserProtfolio(user_id, db):
    stocks = []
    symbols = db.execute('select symbol, amount from shares where userid = :id', id=user_id)
    for symbol in symbols:
        stock = lookup(symbol['symbol'])
        stock["symbol"] = symbol['symbol']
        stock["stock_count"] = symbol['amount']
        if stock["stock_count"] > 0:
            stock['price'] = stock["price"]
            stock['worth'] = stock["stock_count"] * stock["price"]
            stock['worthtext'] = usd(stock["stock_count"] * stock["price"])
            stocks.append(stock)
    return stocks


def MoneyInvested(list):
    stock_sum = 0
    for item in list:
        stock_sum += item['worth']
    return stock_sum


def SellStocks(user_id, symbol, amount, db):
    # check if there is enough bought
    if symbol is None:
        return False, "Invalid stock symbol"

    currentprice = float(lookup(symbol)['price'])
    currentcash = int(db.execute('select cash from users where id = :id', id=user_id)[0]['cash'])
    try:
        usershares = int(db.execute('SElECT amount FROM shares WHERE userid = :id AND symbol = :symbol',
                                    id=user_id, symbol=symbol)[0]['amount'])
    except:
        usershares = 0
    if usershares >= amount:
        db.execute('update users set cash = :cash where id = :id',
                   cash=(currentcash + (amount * currentprice)), id=user_id)
        db.execute(
            'insert into store (userid, symbol, price, shares) values (:userid, :symbol, :price, :shares)',
            userid=user_id, symbol=symbol, price=currentprice, shares=0 - amount)
        db.execute('update shares set amount = :amount where userid = :id and symbol= :symbol',
                   amount=usershares - amount, id=user_id, symbol=symbol)

        return True, True

    else:
        return False, "Invalid, You don't have as much stocks"


def BuyStocks(user_id, stock, amount, db):
    budget = float(db.execute('select cash from users where id = :id', id=user_id)[0]['cash'])
    if stock is None:
        return False, "Invalid stock symbol"
    else:
        if (stock["price"]) * amount < budget:
            db.execute(
                'insert into store (userid, symbol, price, shares) values (:userid, :symbol, :price, :shares)',
                userid=user_id, symbol=stock['symbol'], price=float(stock['price']), shares=amount)

            db.execute('update users set cash = :cash where id = :id',
                       cash=budget - (float(stock['price']) * amount), id=user_id)
            try:
                usershares = int(
                    db.execute('SElECT amount FROM shares WHERE userid = :id AND symbol = :symbol', id=user_id,
                               symbol=stock['symbol'])[0]['amount'])
                db.execute('update shares set amount = :amount where userid = :id and symbol= :symbol',
                           amount=usershares + amount, id=user_id, symbol=stock['symbol'])
            except:
                usershares = 0
                db.execute('insert into shares(userid, amount, symbol) values (:userid, :amount, :symbol)',
                           amount=usershares + amount, userid=user_id, symbol=stock['symbol'])

            return True, True
        else:
            return False, "You Don't Have Enough Money"
