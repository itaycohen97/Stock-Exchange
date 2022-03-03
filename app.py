from flask import Flask

import mysql.connector
from dbmethods import *
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
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

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
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
    return render_template('home.html', session=session)



@app.route('/watchlist')
@login_required
def watchlist():
    print(session['user_id'])
    session["watch_list"] = GetStocks(session['user_id'], db)
    return render_template('watch_list.html', session=session)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'GET':
        return render_template('search.html')
    else:
        session['last_search'] = lookup(request.form.get('search'))
        return render_template('profile.html', session=session, stock=session['last_search'])


@app.route('/test')
def test():
    session['user_id'] = 1
    return render_template('home.html', session=session, search="h")


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
                user = DbSelect(db)
                session["user_id"] = user[0]['id']
                session["full_name"] = user[0]['fullname']
                session["user_name"] = user[0]['username']
                db.execute('select cash from Users where id = %s', (session["user_id"],))
                rows = DbSelect(db)
                session["budget"] = usd(float(rows[0]['cash']))
                return redirect("/")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == 'GET':
        return redirect('/')
    else:
        stock = lookup(request.form.get("symbol"))
        amount = float(request.form.get("amount"))
        try_buy = BuyStocks(session['user_id'], stock, amount, db)
        if try_buy[0] is True:
            flash('Sold ' + str(amount) + ' ' + str(stock['symbol']) + ' stock.')
            dbcon.commit()
            session["stocks"] = GetUserProtfolio(session['user_id'], db)
            session["stocksmoney"] = MoneyInvested(session["stocks"])
            db.execute('select cash from Users where id = %s', (session["user_id"],))
            cash = DbSelect(db)
            session["budget"] = usd(float(cash[0]['cash']))
            return redirect("/")
        else:
            print(try_buy[1])
            return render_template('home.html', error=try_buy[1], session=session)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == 'POST':
        symbol = request.form.get("symbol")
        amount = int(request.form.get("amount"))
        try_sell = SellStocks(session["user_id"], symbol, amount, db)
        if try_sell[0] is True:
            flash('Sold ' + str(amount) + ' ' + str(symbol) + ' stock.')
            session["stocks"] = GetUserProtfolio(session['user_id'], db)
            dbcon.commit()
            session["stocksmoney"] = MoneyInvested(session["stocks"])
            db.execute('select cash from Users where id = %s', (session["user_id"],))
            budget = DbSelect(db)
            session["budget"] = usd(float(budget[0]['cash']))
            return redirect("/")
        else:
            return render_template('home.html', error=try_sell[1],session=session)
    else:
        return redirect('/')

@app.route("/history")
@login_required
def history():
    # """Show history of transactions"""
    db.execute('select * from Store where userid = %s', (session["user_id"],))
    data = DbSelect(db)
    print(data)
    return render_template("history.html", history=data, session=session)


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
        user = DbSelect(db)
        print(user)
        # Ensure username exists and password is correct
        if len(user) != 1 or not check_password_hash(user[0]["hash"], request.form.get("password")):
            return render_template("login.html", error='Invalid Username or Password')

        # Remember which user has logged in
        session["user_id"] = user[0]["id"]
        session["user_name"] = user[0]["username"]
        session["full_name"] = user[0]["fullname"]
        session["stocks"] = GetUserProtfolio(session['user_id'], db)
        stockmoney = MoneyInvested(session["stocks"])
        session["stocksmoney"] = usd(stockmoney)
        db.execute('select cash from Users where id = %s', (session["user_id"],))
        budget = float(DbSelect(db)[0]['cash'])
        session["budget"] = usd(budget)
        profit = (((budget+stockmoney)/10000)-1)*100
        session['Profit'] = Precent(profit)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route('/addwatchlist', methods=['GET', 'POST'])
@login_required
def add():
    symbol = request.form.get('symbol')
    db.execute('select * from Watch where userid = %s and symbol = %s', (session['user_id'], symbol))
    check = DbSelect(db)
    if check == None or len(check) != 0:
        redirect('/')
    else:
        print
        db.execute('insert into Watch (userid, symbol) values (%s, %s)',(session['user_id'], symbol))
        print(db)
        dbcon.commit()
    return redirect('/watchlist')


@app.route('/removefromwatch', methods=['GET', 'POST'])
@login_required
def remove():
    symbol = request.form.get('symbol')
    db.execute("DELETE FROM Watch WHERE userid = %s and symbol = %s", (session['user_id'], symbol))
    dbcon.commit()
    return redirect('/watchlist')



if __name__ == '__main__':
    app.run(debug=True)
