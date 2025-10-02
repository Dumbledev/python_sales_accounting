from flask import Flask ,render_template, session, redirect, request, url_for
from flask_bcrypt import Bcrypt
import uuid
from datetime import date, datetime
import json
from kenobi import KenobiDB
import time


app = Flask(__name__)
app.config["SECRET_KEY"] = "*****"
bcrypt = Bcrypt(app)

db_url = "http://admin:admin@127.0.0.1:5984/a_rahim_inventory"
db_find_url = db_url + "/_find"
current_user = {}
User = KenobiDB("users.json")
Product = KenobiDB("products.json")
Sale = KenobiDB("sales.json")
Credit = KenobiDB("credits.json")
Product_Entry = KenobiDB("product_entries.db")

time_now = datetime.now()
time_now = time_now.strftime("%I:%M:%S %p")
date_today = date.today()
date_today = date_today.strftime("%Y-%m-%d")
day = datetime.strptime(date_today, "%Y-%m-%d")
day = day.day
month = datetime.strptime(date_today, "%Y-%m-%d")
month = month.month  
year = datetime.strptime(date_today, "%Y-%m-%d")
year = year.year


#User
@app.route("/")
def home():
    if "logged_in" not in session or session["role"] != "user":
        return redirect(url_for("login"))
    user = User.search("_id", session["_id"])
    d_sale = Sale.search("day", day)
    return render_template("home.html", user=user[0], d_sales=d_sale)

@app.route("/user_dashboard")
def user_dashboard():
    d_sales = Sale.search("day", day)
    user = User.search("_id", session["_id"])[0]
    user_sales = []
    u_total_sales = 0
    d_credits = Credit.search("day", day)
    u_total_credits = 0
    user_credits = []
    for i in d_sales:
        if i["user"][0]["_id"] == user["_id"]:
            user_sales.append(i)
    for i in user_sales:
        u_total_sales = u_total_sales + i["total"]
    for i in d_credits:
        if i["user"]["_id"] == user["_id"]:
            user_credits.append(i)
    for i in user_credits:    
        u_total_credits = u_total_credits + i["credit_amount"]
    return render_template("user_dashboard.html", user_sales=user_sales, u_total_sales=u_total_sales, 
                           user_credits=user_credits, u_total_credits=u_total_credits)

@app.route("/user_m_sales")
def user_m_sales():
    m_sales = Sale.search("month", month)
    user = User.search("_id", session["_id"])[0]
    user_sales = []
    u_total_sales = 0
    d_credits = Credit.search("day", day)
    u_total_credits = 0
    user_credits = []
    for i in m_sales:
        if i["user"][0]["_id"] == user["_id"]:
            user_sales.append(i)
    for i in user_sales:
        u_total_sales = u_total_sales + i["total"]
    for i in d_credits:
        if i["user"]["_id"] == user["_id"]:
            user_credits.append(i)
    for i in user_credits:    
        u_total_credits = u_total_credits + i["credit_amount"]
    return render_template("user_m_sales.html", user_sales=user_sales, u_total_sales=u_total_sales, 
                           user_credits=user_credits, u_total_credits=u_total_credits)

@app.route("/new_sale_handler")
def new_sale_handler():
    user = get_user()
    id = str(uuid.uuid4())
    data = {"_id":id, "user":user, "products": [], 
            "credit":0, "customer":"", 
            "date":date_today, "day":day, 
            "month":month, "total":0, "checkout":False,
            "creditor_name":"nil", "amount_paid":0,
            "checkout_method":"", "time":time_now}
    Sale.insert(data)
    return redirect(url_for("sale", id=id))

@app.route("/sale/<id>")
def sale(id):
    sale = Sale.search("_id", id)
    sale = sale[0]
    products = Product.all()
    return render_template("new_sale.html", sale=sale, products=products)

@app.route("/sale_product_handler", methods=["POST"])
def sale_product_handler():
    if request.method == "POST":
        id = request.form["id"]
        sale = Sale.search("_id", id)
        name = request.form["name"]
        quantity = request.form["quantity"]
        label = str.lower(request.form["quantity_label"])
        price = 0
        get_product = Product.search("name", name)
        get_product = get_product[0]
        if label == "pcs":
            price = get_product["selling_price_pcs"]
        elif label == "pkt":
            price = get_product["selling_price_pkt"]
        elif label == "carton":
            price = get_product["selling_price_carton"]  
        elif label == "sack":
            price = get_product["selling_price_sack"]  

        product_on_sale = {
            "_id":str(uuid.uuid4()),
            "name":name,
            "quantity":int(quantity),
            "label":label,
            "price": int(price),
            "total": int(price) * int(quantity),
        }
        products = sale[0]["products"]
        products.append(product_on_sale)
        Sale.update("_id", id, {"products":products})        
        total = 0
        for i in sale[0]["products"]:
            total = total + i["total"]
        Sale.update("_id", id, {"total":total})
        return redirect("/sale/"+id)

@app.route("/sale_checkout_handler", methods=["POST"])
def sale_checkout_handler():
    if request.method == "POST":
        id = request.form["id"]
        creditor_name = request.form["creditor_name"]
        amount_paid = int(request.form["amount_paid"])
        checkout_method = request.form["checkout_method"]
        sale = Sale.search("_id", id)[0]
        Sale.update("_id", id, {"checkout_method":checkout_method})
        Sale.update("_id", id, {"amount_paid":amount_paid})
        user = User.search("_id", session["_id"])[0]
        if amount_paid < sale["total"]:
            Sale.update("_id", id, {"checkout":False})
            Sale.update("_id", id, {"creditor_name":creditor_name})
            Credit.insert({
                "_id":str(uuid.uuid4()),
                "creditor_name": creditor_name,
                "credit_amount": sale["total"] - amount_paid,
                "date":date_today,
                "time":time_now,
                "month":month,
                "day":day,
                "sale_id":id,
                "resolved":False,
                "user": user
            }) 
        else:
            Sale.update("_id", id, {"checkout":True})            
    return redirect("/")

@app.route("/credits")
def credits():
    credits = Credit.all()
    return render_template("credits.html", credits=credits)

@app.route("/credit/<id>")
def credit(id):
    credit = Credit.search("_id", id)[0]
    sale = Sale.search("_id", credit["sale_id"])[0]
    return render_template("credit.html", credit=credit, sale=sale)

@app.route("/update_credit_handler", methods=["POST"])
def update_credit():
    if request.method == "POST":
        id = request.form["id"]
        credit = Credit.search("_id", id)[0]
        sale = Sale.search("_id", credit["sale_id"])[0]
        Sale.update("_id", sale["_id"], {"amount_paid": sale["amount_paid"] + float(request.form["credit_amount"])})
        # sale = Sale.search("_id", credit["sale_id"])[0]
        Credit.update("_id", id, {"credit_amount": credit["credit_amount"] - float(request.form["credit_amount"])})
        # Sale.update("_id", sale["_id"], {"amount_paid": float(request.form["credit_amount"])})
        credit = Credit.search("_id", id)[0]
        if credit["credit_amount"] <= 0:
            Credit.update("_id", id, {"resolved":True})
            Sale.update("_id", sale["_id"], {"checkout":True})
    return redirect("/credit/"+id)

@app.route("/delete_credit/<id>")
def delete_credit(id):
    Credit.remove("_id", id)
    return redirect("/credits")

@app.route("/resolve_credit/<id>")
def resolve_credit(id):
    Credit.update("_id", id, {"resolved":True})
    sale_id = Credit.search("_id", id)[0]["sale_id"]
    Sale.update("_id", sale_id, {"checkout":True})
    return redirect("/credits")

@app.route("/delete_sale/<id>")
def delete_sale(id):
    Sale.remove("_id", id)
    return redirect("/")

#Admin
@app.route("/admin")
def admin():
    user = User.search("_id", session["_id"])
    all_products = Product.all()
    m_total_sales = 0
    m_sales = Sale.search("month", month)
    d_total_sales = 0
    d_sales = Sale.search("day", day)    
    m_credits = Credit.all()
    m_total_credit = 0
    m_product_entries = Product_Entry.all()
    product_entries = Product_Entry.search("month", month)
    m_entries_total = 0
    for i in product_entries:
        m_entries_total = m_entries_total + i["est_pcs_profit"]
    for c in m_credits:
        m_total_credit = m_total_credit + c["credit_amount"]
    for i in m_sales:
        m_total_sales = m_total_sales + i["total"]
    for i in d_sales:
        d_total_sales = d_total_sales + i["total"]        
    return render_template("admin/admin.html", user=user[0], all_products=all_products, 
                           m_sales=m_sales, m_total_sales=m_total_sales, m_total_credit=m_total_credit,
                           m_product_entries=m_product_entries, m_entries_total=m_entries_total, 
                           d_total_sales=d_total_sales)

    
@app.route("/products")
def products():
    products = Product.all()
    user = get_user()
    return render_template("admin/products.html", user=user, products=products)


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form["name"]
        buying_price_pcs = float(request.form["buying_price_pcs"])
        selling_price_pcs = float(request.form["selling_price_pcs"])
        buying_price_pkt = float(request.form["buying_price_pkt"])
        selling_price_pkt = float(request.form["selling_price_pkt"])
        buying_price_carton = float(request.form["buying_price_carton"])
        selling_price_carton = float(request.form["selling_price_carton"])        
        quantity_label = request.form.getlist("sell_category")
        user = get_user()
        product = {
                    "_id":str(uuid.uuid4()), 
                    "name":name, 
                    "buying_price_pcs":buying_price_pcs, 
                    "selling_price_pcs":selling_price_pcs,
                    "buying_price_pkt":buying_price_pkt, 
                    "selling_price_pkt":selling_price_pkt, 
                    "buying_price_carton":buying_price_carton, 
                    "selling_price_carton":selling_price_carton,                                         
                    "quantity_label":quantity_label,
                   "user":user, 
                   "date": date_today, 
                   "day":day, 
                   "month":month,
                   "year":year, 
                   }
        Product.insert(product)
        return redirect(url_for("products"))
    else:
        user = get_user()       
        return render_template("admin/add_product.html", user=user)
    
@app.route("/product_entries")
def product_entries():
    products = Product.all()
    product_entries = Product_Entry.search("month", month)
    total = 0
    for i in product_entries:
        product_quantity = 0
        total = total + i["est_pcs_profit"]
        sales = Sale.search("month", month)
    user = User.search("_id", session["_id"])[0]
    return render_template("admin/product_entries.html", products=products, user=user,
                            entries=product_entries, total=total)


@app.route("/add_product_entry_handler", methods=["POST"])
def add_product_entry_handler():
    user = User.search("_id", session["_id"])[0]
    if request.method == "POST":
        product = Product.search("name", request.form["name"])[0]
        data = {
            "_id":str(uuid.uuid4()),
            "name":request.form["name"],
            "quantity": int(request.form["quantity"]),
            "user":user,
            "date":date_today,
            "time":time_now,
            "month":month,
            "day":day, 
            "product":product,
            "est_pcs_profit":float(request.form["quantity"]) * product["selling_price_pcs"]
            }
        Product_Entry.insert(data)
    return redirect("/product_entries")
    

@app.route("/product_update/<id>")
def product_update(id):
    product = Product.search("_id", id)[0]
    user = get_user()  
    return render_template("admin/product_update.html", product=product, user=user) 


@app.route("/product_update_handler", methods=["POST"])   
def product_update_handler():
    id = request.form["id"]
    user = User.search("_id", session["_id"])[0]

    Product.update("_id", id, {"name": request.form["name"]})
    Product.update("_id", id, {"buying_price_pcs":float(request.form["buying_price_pcs"])})
    Product.update("_id", id, {"selling_price_pcs":float(request.form["selling_price_pcs"])})
    Product.update("_id", id, {"buying_price_pkt":float(request.form["buying_price_pkt"])})
    Product.update("_id", id, {"selling_price_pkt":float(request.form["selling_price_pkt"])})
    Product.update("_id", id, {"buying_price_carton":float(request.form["buying_price_carton"])})
    Product.update("_id", id, {"selling_price_carton":float(request.form["selling_price_carton"])})
    Product.update("_id", id, {"updated_by":user})
    Product.update("_id", id, {"update_on":date_today})
    Product.update("_id", id, {"updated":True})
    return redirect("/products")

@app.route("/delete_product/<id>")
def delete_product(id):
    Product.remove("_id", id)
    return redirect("/products")

@app.route("/users")
def users():
    users = User.all()
    user = User.search("_id", session["_id"])[0]
    products = Product.all()
    return render_template("admin/users.html", users=users, user=user, products=products)

@app.route("/user/<id>")
def user(id):
    usr = User.search("_id", id)[0]
    user = User.search("_id", session["_id"])
    d_sales = Sale.search("day", day)
    user_sales = []
    u_total_sales = 0
    d_credits = Credit.search("day", day)
    u_total_credits = 0
    user_credits = []
    for i in d_sales:
        if i["user"][0]["_id"] == usr["_id"]:
            user_sales.append(i)
    for i in user_sales:
        u_total_sales = u_total_sales + i["total"]
    for i in d_credits:
        if i["user"]["_id"] == usr["_id"]:
            user_credits.append(i)
    for i in user_credits:    
        u_total_credits = u_total_credits + i["credit_amount"]
    return render_template("admin/user.html", user_sales=user_sales, u_total_sales=u_total_sales, 
                           user_credits=user_credits, u_total_credits=u_total_credits, usr=usr, user=user)

# Auth
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        user = User.search("username", username)
        if len(user) != 0:
            return render_template("register.html", msg="User Already Exist")
        hased_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        user = {"_id":str(uuid.uuid4()), "name":name, "username":username, "password":hased_pw, "role":"user"}
        User.insert(user)
        return redirect(url_for("users"))
    else:
        user = User.search("_id", session["_id"])[0]
        return render_template("admin/register.html", user=user)

@app.route("/admin_register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        user = User.search("username", username)
        if len(user) != 0:
            return render_template("register.html", msg="User Already Exist")
        hased_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        user = {"_id":str(uuid.uuid4()), 
                "name":name, 
                "username":username, 
                "password":hased_pw, 
                "role":"admin"}
        User.insert(user)
        return redirect(url_for("login"))
    else:
        return render_template("admin_register.html")    

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.search("username", username)
        if len(user) == 0 or bcrypt.check_password_hash(user[0]["password"], password) == False:
            return render_template("login.html", msg="User Does Not Exist/Invalid Details Submited")
        user = user[0]
        session["logged_in"] = True
        session["_id"] = user["_id"]
        session["role"] = user["role"]
        if user["role"] == "admin":
            return redirect(url_for("admin"))
        else:
            return redirect(url_for("home"))
    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def is_user():
    if "logged_in" not in session or session["role"] != "user":
        return redirect(url_for("login"))

def is_admin():
    if "logged_in" not in session or session["role"] != "admin":
        return redirect(url_for("login"))   

def get_user():
    user = User.search("_id", session["_id"])
    return user
    
if __name__ == "__main__":
    app.run(debug=True)