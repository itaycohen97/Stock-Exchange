import mysql.connector, datetime, json
from dbmethods import *
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp, gettempdir
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, Precent

# Configure application
app = Flask(__name__)



# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
try:
    user = json.loads(request.cookies.get("user"))
except:
    user = {}


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = datetime.timedelta(hours=2)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
server = "sql6.freemysqlhosting.net"
username = "sql6476401"
password = "gpGZg7Gw2b"
dbname = "sql6476401"
dbcon = mysql.connector.connect(host=server, user=username, password=password, db=dbname)
if (not dbcon):
    print("error")
    exit
# cursor_class=MySQLCursorPrepared
db = dbcon.cursor(buffered=True)
dbcon.autocommit = True



@app.route('/')
@login_required
def home():
    global user
    if not user:
        user = json.loads(request.cookies.get("user"))
    if "stocks" not in user:
        user['stocks'] = GetSymbolsData(user['stocks_symbols'])
    # stocks = json.loads(request.cookies.get("stocks"))
    return render_template('home.html', user=user)



@app.route('/watchlist')
@login_required
def watchlist():
    global user
    user['watch_list'] = GetWatchStocks(user['user_id'], db)
    return render_template('watch_list.html', user=user)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
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
                    "budget": usd(10000)
                }
                logged_in = redirect('/')
                logged_in.set_cookie('user', json.dumps(user))
                return logged_in


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    global user
    if request.method == 'GET':
        return redirect('/')
    else:
        stock = lookup(request.form.get("symbol"))
        amount = float(request.form.get("amount"))
        try_buy = BuyStocks(user['user_id'], stock, amount, db)
        if try_buy[0] is True:
            flash('Sold ' + str(amount) + ' ' + str(stock['symbol']) + ' stock.')
            dbcon.commit()
            user['stocks_symbols'] = GetUserSymbols(user['user_id'], db)
            user["stocks"] = GetSymbolsData(user['stocks_symbols'])
            user["stocksmoneynondisplay"] = MoneyInvested(user["stocks"])
            user["stocksmoney"] =usd(user["stocksmoneynondisplay"])
            db.execute('select cash from Users where id = %s', (user["user_id"],))
            cash = DbSelect(db)
            user["budget"] = usd(float(cash[0]['cash']))
            user['stocks'] = GetSymbolsData(user['stocks_symbols'])
            return redirect("/")
        else:
            return render_template('home.html', error=try_buy[1], user=user)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    global user
    if request.method == 'POST':
        symbol = request.form.get("symbol")
        amount = int(request.form.get("amount"))
        try_sell = SellStocks(user["user_id"], symbol, amount, db)
        if try_sell[0] is True:
            flash('Sold ' + str(amount) + ' ' + str(symbol) + ' stock.')
            user['stocks_symbols'] = GetUserSymbols(user['user_id'], db)
            user["stocks"] = GetSymbolsData(user['stocks_symbols'])
            user["stocksmoneynondisplay"] = MoneyInvested(user["stocks"])
            user["stocksmoney"] =usd(user["stocksmoneynondisplay"])
            db.execute('select cash from Users where id = %s', (user["user_id"],))
            cash = DbSelect(db)
            user["budget"] = usd(float(cash[0]['cash']))
            user['stocks'] = GetSymbolsData(user['stocks_symbols'])
            return redirect("/")
        else:
            return render_template('home.html', error=try_sell[1],user=user)
    else:
        return redirect('/')

@app.route("/history")
@login_required
def history():
    # """Show history of transactions"""
    db.execute('select * from Store where userid = %s order by Date Desc', (user["user_id"],))
    data = DbSelect(db)
    return render_template("history.html", history=data, user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    error = ''

    # Forget previous user
    session.clear()

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
            "budget": usd(budget),
            "Profit": Precent(profit),
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

    # Forget any user_id
    if request.cookies.get('user'):
        loggedout = redirect("/")
        loggedout.delete_cookie('user')

        return loggedout
    # Redirect user to login form
    return redirect("/")


@app.route('/addwatchlist', methods=['GET', 'POST'])
@login_required
def add():
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
    symbol = request.form.get('symbol')
    db.execute("DELETE FROM Watch WHERE userid = %s and symbol = %s", (user['user_id'], symbol))
    dbcon.commit()
    return redirect('/watchlist')



if __name__ == '__main__':
    app.run(debug=True)
