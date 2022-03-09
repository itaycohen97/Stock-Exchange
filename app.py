import mysql.connector, json, os
from dbmethods import *
from flask import Flask, flash, redirect, render_template, request
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, Precent

# Configure application
app = Flask(__name__)



# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True



# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd


server = os.environ.get('DbServer')
username = os.environ.get('DbUserName')
password = os.environ.get('DbPassword')
dbname = os.environ.get('DbName')

dbcon = mysql.connector.connect(host=server, user=username, password=password, db=dbname)
if (not dbcon):
    print("error")
    exit
# cursor_class=MySQLCursorPrepared
db = dbcon.cursor(buffered=True)
dbcon.autocommit = True
try:
    user = json.loads(request.cookies.get("user"))
except:
    user = {}



@app.route('/')
@login_required
def home():
    GetUser()
    GetUserStocks()
    return render_template('home.html', user=user)



@app.route('/watchlist')
@login_required
def watchlist():
    global user
    GetUser()
    user['watch_list'] = GetWatchStocks(user['user_id'], db)
    return render_template('watch_list.html', user=user)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    GetUser()
    if request.method == 'GET':
        return render_template('search.html')
    else:
        global user
        user['last_search'] = lookup(request.form.get('search'))
        return render_template('profile.html', user=user, stock=user['last_search'])


@app.route('/test')
def test():
    user['user_id'] = 1
    return render_template('home.html', user=user, search="h")


@app.route("/register", methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'GET':
        return render_template('register.html')

    elif request.method == 'POST':

        # make sure that user enter username
        if not request.form.get("username"):
            return render_template("register.html", error='Must Provide Username')

        # make sure that user enter password
        elif not request.form.get("password"):
            return render_template("register.html", error='Must Provide Password')

        # make sure password match
        elif request.form.get('password') != request.form.get('confirmation'):
            return render_template("register.html", error="Passwords don't Match")

        else:
            db.execute("SELECT * FROM Users WHERE username = %s",
                              (request.form.get("username"),))
            rows = DbSelect(db)
            if len(rows) != 0:
                return render_template("register.html", error="Username already exist")
            else:
                new_username = request.form.get("username")
                hash = generate_password_hash(request.form.get("password"))
                fullname = request.form.get("fullname")
                db.execute('insert into Users (username, hash, fullname) values (%s, %s, %s)',
                           (new_username, hash, fullname))
                dbcon.commit()
                db.execute('select * from Users where username =%s', (new_username,))
                userdata = DbSelect(db)
                db.execute('select cash from Users where id = %s', (new_username,))
                rows = DbSelect(db)

                user = {
                    "user_id": userdata[0]['id'],
                    "full_name": userdata[0]['fullname'],
                    "user_name": userdata[0]['username'],
                    "budgetnondisplay":10000,
                    "budget": usd(10000),
                    "stocks_symbols": [],
                    "profitnondisplay":0,
                    "profit": Precent(0),
                    "stocksmoneynondisplay":0,
                    "stocksmoney":usd(0)
                }

                logged_in = redirect('/')
                logged_in.set_cookie('user', json.dumps(user))
                return logged_in


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == 'GET':
        return redirect('/')
    else:
        global user
        GetUser()
        stock = lookup(request.form.get("symbol"))
        amount = float(request.form.get("amount"))
        try_buy = BuyStocks(user['user_id'], stock, amount, db)
        if try_buy[0] is True:
            dbcon.commit()
            user['stocks_symbols'] = GetUserSymbols(user['user_id'], db)
            user["stocksmoney"] =usd(user["stocksmoneynondisplay"])
            db.execute('select cash from Users where id = %s', (user["user_id"],))
            cash = DbSelect(db)
            user["budget"] = usd(float(cash[0]['cash']))
            user['stocks'] = GetSymbolsData(user['stocks_symbols'])
            user.pop("stocks")
            res = redirect("/")
            res.set_cookie('user', json.dumps(user))
            print(user)
            return res
        else:
            return render_template('home.html', error=try_buy[1], user=user)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == 'POST':
        GetUser()
        global user
        symbol = request.form.get("symbol")
        amount = int(request.form.get("amount"))
        try_sell = SellStocks(user["user_id"], symbol, amount, db)
        if try_sell[0] is True:
            flash('Sold ' + str(amount) + ' ' + str(symbol) + ' stock.')
            user['stocks_symbols'] = GetUserSymbols(user['user_id'], db)
            user["stocksmoney"] =usd(user["stocksmoneynondisplay"])
            db.execute('select cash from Users where id = %s', (user["user_id"],))
            cash = DbSelect(db)
            user["budget"] = usd(float(cash[0]['cash']))
            user['stocks'] = GetSymbolsData(user['stocks_symbols'])
            user.pop("stocks")
            res = redirect("/")
            res.set_cookie('user', json.dumps(user))
            return res
        else:
            return render_template('home.html', error=try_sell[1],user=user)
    else:
        return redirect('/')

@app.route("/history")
@login_required
def history():
    GetUser()
    # """Show history of transactions"""
    db.execute('select * from Store where userid = %s order by date desc', (user["user_id"],))
    data = DbSelect(db)
    return render_template("history.html", history=data, user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    error = ''
    

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", error='Must Provide Username')

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", error='Must Provide Password')

        # Query database for username

        db.execute("SELECT * FROM Users WHERE username = %s",
                          (request.form.get("username"),))
        user_data = DbSelect(db)
        # Ensure username exists and password is correct
        if len(user_data) != 1 or not check_password_hash(user_data[0]["hash"], request.form.get("password")):
            return render_template("login.html", error='Invalid Username or Password')

        # Remember which user has logged in
        db.execute('select cash from Users where id = %s', (user_data[0]["id"],))
        budget = float(DbSelect(db)[0]['cash'])
        stocks = GetUserProtfolio(user_data[0]["id"], db)
        stockmoney = MoneyInvested(stocks)
        profit = (((budget+stockmoney)/10000)-1)*100

        global user
        user = {
            "user_id":user_data[0]["id"],
            "user_name": user_data[0]["username"],
            "full_name": user_data[0]["fullname"],
            "stocksmoneynondisplay": stockmoney,
            "stocksmoney": usd(stockmoney),
            "budgetnondisplay":budget,
            "budget": usd(budget),
            "profitnondisplay":profit,
            "profit": Precent(profit),
            "stocks_symbols": GetUserSymbols(user_data[0]["id"], db)
        }
        

        logged_in = redirect('/')
        logged_in.set_cookie('user', json.dumps(user))
    
        # Redirect user to home page
        return logged_in

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    global user
    user = {}
    # Forget any user_id
    if request.cookies.get('user'):
        loggedout = redirect("/")
        loggedout.set_cookie('user', '')

        return loggedout
    # Redirect user to login form
    return redirect("/")


@app.route('/addwatchlist', methods=['GET', 'POST'])
@login_required
def add():
    GetUser()
    symbol = request.form.get('symbol')
    db.execute('select * from Watch where userid = %s and symbol = %s', (user['user_id'], symbol))
    check = DbSelect(db)
    if check == None or len(check) != 0:
        redirect('/')
    else:
        db.execute('insert into Watch (userid, symbol) values (%s, %s)',(user['user_id'], symbol))
        dbcon.commit()
    return redirect('/watchlist')


@app.route('/removefromwatch', methods=['GET', 'POST'])
@login_required
def remove():
    GetUser()
    symbol = request.form.get('symbol')
    db.execute("DELETE FROM Watch WHERE userid = %s and symbol = %s", (user['user_id'], symbol))
    dbcon.commit()
    return redirect('/watchlist')

def GetUser():
    global user
    try:
        user = json.loads(request.cookies.get("user"))
    except:
        user = {}

def GetUserStocks():
    global user
    user = json.loads(request.cookies.get("user"))
    try:
        user['stocks'] = GetSymbolsData(user['stocks_symbols'])
        user['stocksmoneynondisplay']=MoneyInvested(user['stocks'])
        user['stocksmoney']=usd(user['stocksmoneynondisplay'])
        user['profit'] = Precent((((user["budgetnondisplay"]+user['stocksmoneynondisplay'])/10000)-1)*100)
    except:
        user['stocks'] = []


if __name__ == '__main__':
    app.run(debug=True)
