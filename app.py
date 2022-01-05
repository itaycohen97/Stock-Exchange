from flask import Flask

import os
from dbmethods import *
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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
db = SQL("sqlite:///finance.db")


@app.route('/')
@login_required
def home():
    return render_template('home.html', session=session)

@app.route('/watchlist')
@login_required
def watchlist():
    session["watch_list"] = getstocks(session['user_id'], db)
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
            rows = db.execute("SELECT * FROM users WHERE username = :username",
                              username=request.form.get("username"))
            if len(rows) != 0:
                return render_template("register.html", error="Username already exist")
            else:
                new_username = request.form.get("username")
                hash = generate_password_hash(request.form.get("password"))
                fullname = request.form.get("fullname")
                db.execute('insert into users (username, hash, fullname) values (:username, :hash, :fullname)',
                           username=new_username, hash=hash, fullname=fullname)
                user = db.execute('select * from users where username =:username', username=new_username)
                session["user_id"] = user[0]['id']
                session["full_name"] = user[0]['fullname']
                session["user_name"] = user[0]['username']
                session["budget"] = usd(float(
                    db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash']))

                return redirect("/")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == 'GET':
        return redirect('/')
    else:
        quote = lookup(request.form.get("symbol"))
        budget = float(db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash'])
        amount = float(request.form.get("amount"))
        if quote != None:
            if (quote["price"]) * amount < budget:
                db.execute(
                    'insert into store (userid, symbol, price, shares) values (:userid, :symbol, :price, :shares)',
                    userid=session["user_id"], symbol=quote['symbol'], price=float(quote['price']), shares=amount)
                db.execute('update users set cash = :cash where id = :id',
                           cash=budget - (float(quote['price']) * amount), id=session["user_id"])
                session["budget"] = usd(float(
                    db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash']))
                session["stocks"] = currentstocks(session['user_id'], db)
                session["stocksmoney"] = stocksmoney(session["stocks"])
                session["budget"] = usd(
                    float(db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash']))
                return redirect("/")
            else:
                return render_template("home.html", error="You Don't Have Enough Money", session=session)
        else:
            return render_template("buy.html", error="Wrong Symbol")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == 'POST':
        symbol = request.form.get("symbol")
        # check if there is enough bought
        if symbol != None:
            currentprice = float(lookup(request.form.get("symbol"))['price'])
            currentcash = int(db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash'])
            sellamount = int(request.form.get("amount"))
            usershares = int(db.execute('SElECT SUM(shares) FROM store WHERE userid = :id AND symbol = :symbol',
                                        id=session["user_id"], symbol=symbol)[0]['SUM(shares)'])

            if usershares >= sellamount:
                db.execute('update users set cash = :cash where id = :id',
                           cash=(currentcash + (sellamount * currentprice)), id=session["user_id"])
                db.execute(
                    'insert into store (userid, symbol, price, shares) values (:userid, :symbol, :price, :shares)',
                    userid=session["user_id"], symbol=symbol, price=currentprice, shares=0 - sellamount)
                flash('Sold ' + str(sellamount) + ' ' + str(symbol) + ' stock.')
                session["stocks"] = currentstocks(session['user_id'], db)
                session["stocksmoney"] = stocksmoney(session["stocks"])
                session["budget"] = usd(
                    float(db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash']))
                return redirect("/")

            else:
                return render_template('sell.html', error="Invalid, You don't have as much stocks")
        else:
            return render_template('sell.html', error="Invalid stock symbol")



    else:
        return redirect('/')

@app.route("/history")
@login_required
def history():
    # """Show history of transactions"""
    data = db.execute('select * from store where userid = :id', id=session["user_id"])
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

        user = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(user) != 1 or not check_password_hash(user[0]["hash"], request.form.get("password")):
            return render_template("login.html", error='Invalid Username or Password')

        # Remember which user has logged in
        session["user_id"] = user[0]["id"]
        session["user_name"] = user[0]["username"]
        session["full_name"] = user[0]["fullname"]
        session["stocks"] = currentstocks(session['user_id'], db)
        session["stocksmoney"] = stocksmoney(session["stocks"])
        session["budget"] = usd(float(db.execute('select cash from users where id = :id', id=session["user_id"])[0]['cash']))

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
def add():
    symbol = request.form.get('symbol')
    check = db.execute('select * from watch where userid = :userid and symbol = :symbol', userid=session['user_id'],
                       symbol=symbol)
    if len(check) != 0:
        redirect('/')
    else:
        db.execute('insert into watch (userid, symbol) values (:userid, :symbol)',
                   userid=session['user_id'], symbol=symbol)

    return redirect('/watchlist')


if __name__ == '__main__':
    app.run()
