import imp
from helpers import lookup, usd


def GetWatchStocks(user_id, db):
    db.execute("SELECT symbol FROM Watch WHERE userid = %s",(user_id,))
    symbols = DbSelect(db)    
    stocks = []
    for symbol in symbols:
        stock = lookup(symbol['symbol'])
        if stock is not None:
            stocks.append(stock)
    return stocks


def GetUserProtfolio(user_id, db):
    stocks = []
    db.execute('select symbol, amount from Shares where userid = %s', (user_id,))
    symbols = DbSelect(db)
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

def GetUserSymbols(user_id, db):
    db.execute('select symbol, amount from Shares where userid = %s', (user_id,))
    return DbSelect(db)

def GetSymbolsData(symbols):
    stocks = []
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
    db.execute('select cash from Users where id = %s', (user_id,))
    cash = DbSelect(db)
    currentcash = int(cash[0]['cash'])
    db.execute('SElECT amount FROM Shares WHERE userid = %s AND symbol = %s',
                                (user_id, symbol))
    cash = DbSelect(db)
    if len(cash) == 0:
        usershares = 0
    else:
        usershares = int(cash[0]['amount'])

    if usershares >= amount:
        db.execute('update Users set cash = %s where id = %s',
                   (currentcash + (amount * currentprice), user_id))
        db.execute(
            'insert into Store (userid, symbol, price, shares) values (%s, %s, %s, %s)',
            (user_id, symbol, currentprice, 0 - amount))
        db.execute('update Shares set amount = %s where userid = %s and symbol= %s',
                   ((usershares - amount), user_id, symbol))
        return True, True

    else:
        return False, "Invalid, You don't have as much stocks"


def BuyStocks(user_id, stock, amount, db):
    db.execute('select cash from Users where id = %s', (user_id,))
    query = DbSelect(db)
    budget = float(query[0]['cash'])

    if stock is None:
        return False, "Invalid stock symbol"
    else:
        if (stock["price"]) * amount < budget:
            db.execute(
                'insert into Store (userid, symbol, price, shares) values (%s, %s, %s, %s)',
                (user_id, stock['symbol'], float(stock['price']), amount))

            db.execute('update Users set cash = %s where id = %s',
                       (budget - (float(stock['price']) * amount), user_id))
            db.execute('SElECT amount FROM Shares WHERE userid = %s AND symbol = %s', (user_id,stock['symbol']))
            query = DbSelect(db)
            if len(query) == 0:
                 db.execute('insert into Shares (userid, symbol, amount) values (%s, %s, %s)',
                        (user_id, stock['symbol'], amount))
            else:
                usershares = int(query[0]['amount'])
                usershares = amount+usershares
                db.execute('update Shares set amount = %s where userid = %s and symbol= %s',
                            (usershares , user_id, stock['symbol']))
            return True, True
        else:
            return False, "You Don't Have Enough Money"



def DbSelect(cursor):
    list = []
    for row in cursor:
        result = dict(zip(cursor.column_names,row))
        for key in result:
            if issubclass(type(result[key]), bytearray):
                result[key] = str(result[key], "utf-8")
        list.append(result)
    return list