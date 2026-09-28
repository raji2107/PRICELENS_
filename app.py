from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import smtplib
import secrets

from urllib.parse import quote

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from werkzeug.security import generate_password_hash, check_password_hash

from config import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MAIL_PASSWORD
)

from scraper.price_scraper import scrape_product


app = Flask(__name__)

app.secret_key = "pricelens-secret-key-change-later"


# ==============================
# DATABASE CONNECTION
# ==============================

def get_db_connection():

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# ==============================
# EMAIL SERVICE
# ==============================

def send_email(to_email, subject, message):

    msg = MIMEMultipart()

    msg["From"] = MAIL_USERNAME
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(
        MIMEText(message, "plain")
    )

    server = None

    try:

        server = smtplib.SMTP(
            MAIL_SERVER,
            MAIL_PORT
        )

        if MAIL_USE_TLS:
            server.starttls()

        server.login(
            MAIL_USERNAME,
            MAIL_PASSWORD
        )

        server.sendmail(
            MAIL_USERNAME,
            to_email,
            msg.as_string()
        )

        return True

    except Exception as e:

        print(
            "Email Error:",
            e
        )

        return False

    finally:

        if server:

            try:
                server.quit()
            except Exception:
                pass


# ==============================
# VERIFICATION EMAIL
# ==============================

def send_verification_email(
    to_email,
    full_name,
    token
):

    verification_link = (
        "http://127.0.0.1:5000/verify/"
        + quote(token)
    )

    message = (
        "Hello " + full_name + ",\n\n"
        "Welcome to PriceLens!\n\n"
        "Thank you for creating your PriceLens account.\n\n"
        "Please verify your email address by clicking the link below:\n\n"
        + verification_link +
        "\n\n"
        "If you did not create a PriceLens account, "
        "you can ignore this email.\n\n"
        "Thank you,\n"
        "PriceLens Team"
    )

    return send_email(
        to_email,
        "Verify your PriceLens Account",
        message
    )


# ==============================
# PASSWORD VALIDATION
# ==============================

def validate_password(password):

    if len(password) < 6:

        return "Password must be at least 6 characters."

    if not any(
        char.isalpha()
        for char in password
    ):

        return "Password must contain at least one letter."

    if not any(
        char.isdigit()
        for char in password
    ):

        return "Password must contain at least one number."

    if not any(
        not char.isalnum()
        for char in password
    ):

        return "Password must contain at least one special symbol."

    return None


# ==============================
# HOME
# ==============================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# ==============================
# DASHBOARD
# ==============================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        user_id = session["user_id"]

        # =================================
        # TOTAL TRACKED PRODUCTS
        # =================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_products
            FROM products
            WHERE user_id = %s
            """,
            (user_id,)
        )

        total_products = cursor.fetchone()["total_products"]

        # =================================
        # PRODUCTS WITH PRICE DROP
        # =================================

        cursor.execute(
            """
            SELECT COUNT(*) AS price_drops
            FROM products
            WHERE user_id = %s
              AND current_price IS NOT NULL
              AND highest_price IS NOT NULL
              AND current_price < highest_price
            """,
            (user_id,)
        )

        price_drops = cursor.fetchone()["price_drops"]

        # =================================
        # ACTIVE TARGET ALERTS
        # =================================

        cursor.execute(
            """
            SELECT COUNT(*) AS active_alerts
            FROM products
            WHERE user_id = %s
              AND current_price IS NOT NULL
              AND target_price IS NOT NULL
              AND current_price <= target_price
            """,
            (user_id,)
        )

        active_alerts = cursor.fetchone()["active_alerts"]

        # =================================
        # AVERAGE SAVINGS
        # =================================

        cursor.execute(
            """
            SELECT
                AVG(
                    GREATEST(
                        highest_price - current_price,
                        0
                    )
                ) AS average_savings
            FROM products
            WHERE user_id = %s
              AND current_price IS NOT NULL
              AND highest_price IS NOT NULL
            """,
            (user_id,)
        )

        average_savings_result = cursor.fetchone()

        average_savings = (
            average_savings_result["average_savings"]
            or 0
        )

        # =================================
        # RECENT PRODUCTS
        # =================================

        cursor.execute(
            """
            SELECT
                id,
                product_name,
                current_price,
                target_price,
                highest_price,
                lowest_price,
                average_price,
                product_image,
                product_url,
                created_at
            FROM products
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (user_id,)
        )

        recent_products = cursor.fetchall()

        # =================================
        # PRICE HISTORY
        # =================================

        cursor.execute(
            """
            SELECT
                ph.product_id,
                ph.price,
                ph.recorded_at,
                p.product_name
            FROM price_history ph
            JOIN products p
                ON ph.product_id = p.id
            WHERE p.user_id = %s
            ORDER BY ph.recorded_at ASC
            LIMIT 30
            """,
            (user_id,)
        )

        price_history = cursor.fetchall()

        for row in price_history:
            row["price"] = float(row["price"])

            if row["recorded_at"]:
               row["recorded_at"] = row["recorded_at"].strftime(
                   "%Y-%m-%d %H:%M:%S"
               )

        # =================================
        # DASHBOARD RENDER
        # =================================

        return render_template(
            "dashboard.html",
            user_name=session["user_name"],
            total_products=total_products,
            price_drops=price_drops,
            active_alerts=active_alerts,
            average_savings=average_savings,
            recent_products=recent_products,
            price_history=price_history
        )

    except Exception as e:

        print(
            "❌ Dashboard Error:",
            e
        )

        return (
            "<h3>Dashboard Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/dashboard'>Go Back</a>"
        )

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()


# ==============================
# PRODUCTS
# ==============================

@app.route("/products")
def products():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM products
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (
                session["user_id"],
            )
        )

        products_list = cursor.fetchall()

        return render_template(
            "products.html",
            products=products_list
        )

    except Exception as e:

        return (
            "<h3>Database Error</h3>"
            "<p>" + str(e) + "</p>"
        )

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()


# ==============================
# ADD / TRACK PRODUCT
# ==============================

@app.route(
    "/add-product",
    methods=["POST"]
)
def add_product():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    product_url = request.form.get(
        "product_url",
        ""
    ).strip()

    target_price = request.form.get(
        "target_price",
        ""
    ).strip()

    # ==============================
    # VALIDATION
    # ==============================

    if not product_url or not target_price:

        return (
            "<h3>Please enter Product URL "
            "and Target Price.</h3>"
            "<a href='/products'>Go Back</a>"
        )

    try:

        target_price = float(
            target_price
        )

        if target_price <= 0:

            return (
                "<h3>Target price must be "
                "greater than 0.</h3>"
                "<a href='/products'>Go Back</a>"
            )

    except ValueError:

        return (
            "<h3>Invalid target price.</h3>"
            "<a href='/products'>Go Back</a>"
        )

    # ==============================
    # SCRAPE PRODUCT
    # ==============================

    print()
    print("================================")
    print("PriceLens Product Tracking")
    print("================================")
    print("URL:", product_url)
    print("Target Price:", target_price)
    print("Starting scraper...")

    try:

        product = scrape_product(
            product_url
        )

    except Exception as e:

        print(
            "Scraping Error:",
            e
        )

        return (
            "<h3>Scraping failed.</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/products'>Go Back</a>"
        )

    # ==============================
    # CHECK SCRAPER RESULT
    # ==============================

    if not product:

        return (
            "<h3>Unable to fetch "
            "product details.</h3>"
            "<p>Please check the product URL.</p>"
            "<a href='/products'>Go Back</a>"
        )

    product_name = product.get(
        "name"
    )

    current_price = product.get(
        "price"
    )

    product_image = product.get(
        "image"
    )

    print(
        "Product Name:",
        product_name
    )

    print(
        "Current Price:",
        current_price
    )

    print(
        "Product Image:",
        product_image
    )

    if not product_name:

        return (
            "<h3>Product name could not "
            "be extracted.</h3>"
            "<a href='/products'>Go Back</a>"
        )

    if current_price is None:

        return (
            "<h3>Product price could not "
            "be extracted.</h3>"
            "<a href='/products'>Go Back</a>"
        )

    # ==============================
    # CONVERT PRICE
    # ==============================

    try:

        current_price = float(
            current_price
        )

    except (
        ValueError,
        TypeError
    ):

        return (
            "<h3>Invalid product price "
            "returned by scraper.</h3>"
            "<a href='/products'>Go Back</a>"
        )

    # ==============================
    # SAVE PRODUCT
    # ==============================

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO products
            (
                user_id,
                product_url,
                product_name,
                current_price,
                target_price,
                product_image,
                highest_price,
                lowest_price,
                average_price
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                session["user_id"],
                product_url,
                product_name,
                current_price,
                target_price,
                product_image,
                current_price,
                current_price,
                current_price
            )
        )

        product_id = cursor.lastrowid

        # ==============================
        # FIRST PRICE HISTORY RECORD
        # ==============================

        cursor.execute(
            """
            INSERT INTO price_history
            (
                product_id,
                price
            )
            VALUES
            (
                %s,
                %s
            )
            """,
            (
                product_id,
                current_price
            )
        )

        conn.commit()

        print()
        print("================================")
        print("Product saved successfully!")
        print("================================")
        print("Name:", product_name)
        print("Price:", current_price)
        print("Target:", target_price)
        print("Price history saved!")

    except Exception as e:

        if conn:

            conn.rollback()

        print(
            "Database Error:",
            e
        )

        return (
            "<h3>Database Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/products'>Go Back</a>"
        )

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()

    # ==============================
    # TARGET PRICE ALERT
    # ==============================

    if current_price <= target_price:

        print()
        print(
            "🎯 TARGET PRICE REACHED!" 
        )

        alert_subject = (
            "🎯 PriceLens - "
            "Target Price Reached!"
        )

        alert_message = f"""
Hello {session["user_name"]},

Good news! 🎉

Your tracked product has reached your target price.

Product:
{product_name}  ,

Current Price:
₹{current_price:,.2f}

Target Price:
₹{target_price:,.2f}

🔥 The current price is now at or below your target price.

You can check the product here:

{product_url}

Happy Shopping!

PriceLens Team
"""

        email_success = send_email(
            session["user_email"],
            alert_subject,
            alert_message
        )

        if email_success:

            print(
                "📧 Target alert email sent!"
            )

        else:


            print(
                "⚠️ Target reached, "
                "but email failed."
            )

    else:

        print(
            "Price is still above "
            "target price."
        )

    # ==============================
    # RETURN
    # ==============================

    return redirect(
        url_for("products")
    )


# ==============================
# LOGIN
# ==============================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        try:

            conn = get_db_connection()

            cursor = conn.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if not user:

                return (
                    "<h3>Invalid email "
                    "or password.</h3>"
                    "<a href='/login'>Go Back</a>"
                )

            if not check_password_hash(
                user["password"],
                password
            ):

                return (
                    "<h3>Invalid email "
                    "or password.</h3>"
                    "<a href='/login'>Go Back</a>"
                )

            if not user["email_verified"]:

                return (
                    "<h3>Email not verified.</h3>"
                    "<p>Please check your Gmail "
                    "and verify your email address "
                    "first.</p>"
                    "<a href='/login'>Go Back</a>"
                )

            session["user_id"] = user["id"]

            session["user_name"] = (
                user["full_name"]
            )

            session["user_email"] = (
                user["email"]
            )

            return redirect(
                url_for("dashboard")
            )

        except Exception as e:

            return (
                "<h3>Database Error</h3>"
                "<p>" + str(e) + "</p>"
                "<a href='/login'>Go Back</a>"
            )

    return render_template(
        "login.html"
    )
    
    # ==============================
# ALERTS
# ==============================

@app.route("/alerts")
def alerts():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                pa.id,
                pa.product_id,
                pa.target_price,
                pa.sent_at,
                p.product_name,
                p.current_price,
                p.product_image,
                p.product_url
            FROM price_alerts pa
            JOIN products p
                ON pa.product_id = p.id
            WHERE pa.user_id = %s
            ORDER BY pa.sent_at DESC
            """,
            (session["user_id"],)
        )

        alerts = cursor.fetchall()

        return render_template(
            "alerts.html",
            user_name=session["user_name"],
            alerts=alerts
        )

    except Exception as e:
        print("❌ Alerts Error:", e)
        return (
            "<h3>Alerts Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/dashboard'>Go Back</a>"
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ==============================
# PRICE ANALYTICS
# ==============================
@app.route("/price-analytics")
def price_analytics():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, product_name, current_price, target_price,
               highest_price, lowest_price, average_price,
               product_image, product_url
        FROM products
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    products = cursor.fetchall()

    cursor.execute("""
        SELECT ph.product_id, ph.price, ph.recorded_at,
               p.product_name
        FROM price_history ph
        JOIN products p ON ph.product_id = p.id
        WHERE p.user_id = %s
        ORDER BY ph.recorded_at ASC
    """, (session["user_id"],))

    price_history = cursor.fetchall()

    for row in price_history:
        row["price"] = float(row["price"])
        if row["recorded_at"]:
            row["recorded_at"] = row["recorded_at"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    cursor.execute("""
        SELECT
            COUNT(*) AS total_products,
            COALESCE(AVG(current_price), 0) AS avg_current,
            COALESCE(AVG(average_price), 0) AS avg_average,
            COALESCE(MAX(highest_price), 0) AS highest_recorded,
            COALESCE(MIN(lowest_price), 0) AS lowest_recorded
        FROM products
        WHERE user_id = %s
    """, (session["user_id"],))

    stats = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "price_analytics.html",
        user_name=session["user_name"],
        products=products,
        price_history=price_history,
        stats=stats
    )

# ==============================
# WATCHLIST
# ==============================

@app.route("/watchlist")
def watchlist():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                product_name,
                current_price,
                target_price,
                highest_price,
                lowest_price,
                average_price,
                product_image,
                product_url
            FROM products
            WHERE user_id = %s
            ORDER BY id DESC
        """, (session["user_id"],))

        products = cursor.fetchall()

        return render_template(
            "watchlist.html",
            user_name=session["user_name"],
            products=products
        )

    except Exception as e:

        print("❌ Watchlist Error:", e)

        return (
            "<h3>Watchlist Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/dashboard'>Go Back</a>"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()




# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )

# ==============================
# PROFILE
# ==============================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                full_name,
                email,
                email_verified,
                created_at
            FROM users
            WHERE id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()

        return render_template(
            "profile.html",
            user=user,
            user_name=session["user_name"]
        )

    except Exception as e:

        print("❌ Profile Error:", e)

        return (
            "<h3>Profile Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/dashboard'>Go Back</a>"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==============================
# SETTINGS
# ==============================

@app.route("/settings")
def settings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "settings.html",
        user_name=session["user_name"]
    )











# ==============================
# REGISTER
# ==============================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if (
            not full_name
            or not email
            or not password
        ):

            return (
                "<h3>Please fill in "
                "all required fields.</h3>"
                "<a href='/register'>Go Back</a>"
            )

        error = validate_password(
            password
        )

        if error:

            return (
                "<h3>" + error + "</h3>"
                "<a href='/register'>Go Back</a>"
            )

        if password != confirm_password:

            return (
                "<h3>Passwords do not match.</h3>"
                "<a href='/register'>Go Back</a>"
            )

        hashed_password = (
            generate_password_hash(
                password
            )
        )

        verification_token = (
            secrets.token_urlsafe(32)
        )

        conn = None
        cursor = None

        try:

            conn = get_db_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password,
                    email_verified,
                    verification_token
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    full_name,
                    email,
                    hashed_password,
                    False,
                    verification_token
                )
            )

            conn.commit()

            email_sent = (
                send_verification_email(
                    email,
                    full_name,
                    verification_token
                )
            )

            if email_sent:

                return (
                    "<h2>Account created "
                    "successfully!</h2>"
                    "<p>A verification link "
                    "has been sent to your email.</p>"
                    "<p>Please check your Gmail "
                    "inbox and click the "
                    "verification link.</p>"
                    "<a href='/login'>"
                    "Go to Login"
                    "</a>"
                )

            return (
                "<h3>Account created, "
                "but email could not be sent.</h3>"
                "<p>Check the Flask terminal "
                "for the email error.</p>"
                "<a href='/login'>Go to Login</a>"
            )

        except mysql.connector.IntegrityError:

            return (
                "<h3>Email already registered.</h3>"
                "<a href='/register'>Go Back</a>"
            )

        except Exception as e:

            return (
                "<h3>Database Error</h3>"
                "<p>" + str(e) + "</p>"
                "<a href='/register'>Go Back</a>"
            )

        finally:

            if cursor:

                cursor.close()

            if conn:

                conn.close()

    return render_template(
        "register.html"
    )


# ==============================
# EMAIL VERIFICATION
# ==============================

@app.route(
    "/verify/<token>"
)
def verify_email(token):

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE verification_token = %s
            """,
            (token,)
        )

        user = cursor.fetchone()

        if not user:

            return (
                "<h3>Invalid or expired "
                "verification link.</h3>"
                "<a href='/login'>"
                "Go to Login"
                "</a>"
            )

        cursor.execute(
            """
            UPDATE users
            SET
                email_verified = TRUE,
                verification_token = NULL
            WHERE id = %s
            """,
            (user["id"],)
        )

        conn.commit()

        return (
            "<h2>Email verified "
            "successfully!</h2>"
            "<p>Your PriceLens account "
            "is now verified.</p>"
            "<p>You can now login "
            "to your account.</p>"
            "<a href='/login'>"
            "Go to Login"
            "</a>"
        )

    except Exception as e:

        return (
            "<h3>Verification Error</h3>"
            "<p>" + str(e) + "</p>"
            "<a href='/login'>"
            "Go to Login"
            "</a>"
        )

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()


# ==============================
# EMAIL TEST
# ==============================

@app.route("/email-test")
def email_test():

    success = send_email(
        MAIL_USERNAME,
        "PriceLens Email Test",
        "Hello! This is a test email from PriceLens."
    )

    if success:

        return (
            "<h2>Email sent successfully!</h2>"
            "<p>Check your Gmail inbox.</p>"
        )

    return (
        "<h3>Email sending failed.</h3>"
        "<p>Check the Flask terminal "
        "for the error.</p>"
    )


# ==============================
# DATABASE TEST
# ==============================

@app.route("/db-test")
def db_test():

    try:

        conn = get_db_connection()

        conn.close()

        return (
            "PriceLens MySQL "
            "Connection Successful!"
        )

    except Exception as e:

        return (
            "MySQL Connection Failed: "
            + str(e)
        )


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )