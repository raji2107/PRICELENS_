import time
import mysql.connector
import smtplib

from apscheduler.schedulers.background import BackgroundScheduler

from scraper.price_scraper import scrape_product

from config import (
    DB_HOST,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MAIL_PASSWORD
)

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# =================================
# DATABASE CONNECTION
# =================================

def get_db_connection():

    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# =================================
# SEND EMAIL
# =================================

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
            "❌ Email Error:",
            e
        )

        return False

    finally:

        if server:

            try:
                server.quit()
            except Exception:
                pass


# =================================
# CHECK ALL PRODUCTS
# =================================

def check_prices():

    print()
    print("================================")
    print("PriceLens Automatic Price Check")
    print("================================")

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )

        # =================================
        # GET ALL PRODUCTS
        # =================================

        cursor.execute(
            """
            SELECT
                p.id,
                p.user_id,
                p.product_url,
                p.product_name,
                p.current_price,
                p.target_price,
                p.highest_price,
                p.lowest_price,
                p.average_price,
                u.full_name,
                u.email
            FROM products p
            JOIN users u
                ON p.user_id = u.id
            """
        )

        products = cursor.fetchall()

        print(
            "Products found:",
            len(products)
        )

        # =================================
        # CHECK EACH PRODUCT
        # =================================

        for product in products:

            print()
            print("--------------------------------")

            print(
                "Checking:",
                product["product_name"]
            )

            print(
                "URL:",
                product["product_url"]
            )

            # =================================
            # SCRAPE PRODUCT
            # =================================

            try:

                scraped_product = scrape_product(
                    product["product_url"]
                )

            except Exception as e:

                print(
                    "❌ Scraping Error:",
                    e
                )

                continue

            if not scraped_product:

                print(
                    "❌ Could not update product"
                )

                continue

            new_price = scraped_product.get(
                "price"
            )

            if new_price is None:

                print(
                    "❌ Price not found"
                )

                continue

            # =================================
            # CONVERT PRICE
            # =================================

            try:

                new_price = float(
                    new_price
                )

            except (TypeError, ValueError):

                print(
                    "❌ Invalid price:",
                    new_price
                )

                continue

            old_price = product[
                "current_price"
            ]

            target_price = product[
                "target_price"
            ]

            highest_price = product[
                "highest_price"
            ]

            lowest_price = product[
                "lowest_price"
            ]

            print(
                "Old Price:",
                old_price
            )

            print(
                "New Price:",
                new_price
            )

            print(
                "Target Price:",
                target_price
            )

            # =================================
            # PRICE CHANGE
            # =================================

            price_change = None
            price_drop_percent = None

            if old_price is not None:

                old_price_float = float(
                    old_price
                )

                price_change = (
                    new_price -
                    old_price_float
                )

                if old_price_float > 0:

                    price_drop_percent = (
                        (
                            old_price_float -
                            new_price
                        )
                        / old_price_float
                    ) * 100

            # =================================
            # HIGHEST PRICE
            # =================================

            if highest_price is None:

                new_highest_price = new_price

            else:

                new_highest_price = max(
                    float(highest_price),
                    new_price
                )

            # =================================
            # LOWEST PRICE
            # =================================

            if lowest_price is None:

                new_lowest_price = new_price

            else:

                new_lowest_price = min(
                    float(lowest_price),
                    new_price
                )

            # =================================
            # SAVE PRICE HISTORY
            # =================================

            cursor.execute(
                """
                INSERT INTO price_history
                (
                    product_id,
                    price
                )
                VALUES (%s, %s)
                """,
                (
                    product["id"],
                    new_price
                )
            )

            print(
                "✅ Price history saved"
            )

            # =================================
            # CALCULATE AVERAGE
            # =================================

            cursor.execute(
                """
                SELECT
                    AVG(price) AS average_price
                FROM price_history
                WHERE product_id = %s
                """,
                (
                    product["id"],
                )
            )

            average_result = cursor.fetchone()

            new_average_price = (
                average_result["average_price"]
            )

            # =================================
            # UPDATE PRODUCTS
            # =================================

            cursor.execute(
                """
                UPDATE products
                SET
                    current_price = %s,
                    highest_price = %s,
                    lowest_price = %s,
                    average_price = %s
                WHERE id = %s
                """,
                (
                    new_price,
                    new_highest_price,
                    new_lowest_price,
                    new_average_price,
                    product["id"]
                )
            )

            conn.commit()

            print(
                "✅ Product price updated"
            )

            print(
                "Highest Price:",
                new_highest_price
            )

            print(
                "Lowest Price:",
                new_lowest_price
            )

            print(
                "Average Price:",
                new_average_price
            )

            # =================================
            # SHOW PRICE CHANGE
            # =================================

            if price_change is not None:

                if price_change < 0:

                    print(
                        f"📉 Price dropped by "
                        f"₹{abs(price_change):,.2f}"
                    )

                    if price_drop_percent is not None:

                        print(
                            f"📉 Drop percentage: "
                            f"{price_drop_percent:.2f}%"
                        )

                elif price_change > 0:

                    print(
                        f"📈 Price increased by "
                        f"₹{price_change:,.2f}"
                    )

                else:

                    print(
                        "➡️ Price unchanged"
                    )

            # =================================
            # TARGET PRICE CHECK
            # =================================

            if (
                target_price is not None
                and new_price <= float(
                    target_price
                )
            ):

                print()
                print(
                    "🎯 TARGET PRICE REACHED!"
                )

                # =================================
                # CHECK DUPLICATE ALERT
                # =================================

                cursor.execute(
                    """
                    SELECT id
                    FROM price_alerts
                    WHERE product_id = %s
                      AND user_id = %s
                      AND target_price = %s
                    """,
                    (
                        product["id"],
                        product["user_id"],
                        target_price
                    )
                )

                existing_alert = cursor.fetchone()

                if existing_alert:

                    print(
                        "📧 Alert already sent. "
                        "Skipping duplicate email."
                    )

                else:

                    # =================================
                    # SEND ALERT EMAIL
                    # =================================

                    alert_subject = (
                        "🎯 PriceLens - "
                        "Target Price Reached!"
                    )

                    alert_message = f"""
Hello {product["full_name"]},

Good news! 🎉

Your tracked product has reached your target price.

Product:
{product["product_name"]}

Current Price:
₹{new_price:,.2f}

Target Price:
₹{float(target_price):,.2f}

🔥 The current price is now at or below your target price.

You can check the product here:

{product["product_url"]}

Happy Shopping!

PriceLens Team
"""

                    email_success = send_email(
                        product["email"],
                        alert_subject,
                        alert_message
                    )

                    if email_success:

                        cursor.execute(
                            """
                            INSERT INTO price_alerts
                            (
                                product_id,
                                user_id,
                                target_price
                            )
                            VALUES (%s, %s, %s)
                            """,
                            (
                                product["id"],
                                product["user_id"],
                                target_price
                            )
                        )

                        conn.commit()

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

        print()
        print("================================")
        print(
            "✅ Automatic price check complete"
        )
        print("================================")

    except Exception as e:

        print(
            "❌ Scheduler Error:",
            e
        )

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()


# =================================
# START AUTOMATIC SCHEDULER
# =================================

if __name__ == "__main__":

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        check_prices,
        "interval",
        hours=1
    )

    scheduler.start()

    print()
    print("================================")
    print("🚀 PriceLens Scheduler Started")
    print("================================")
    print("⏰ Price check interval: 1 hour")
    print("Press Ctrl+C to stop.")
    print("================================")

    try:

        # Run one check immediately
        check_prices()

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print("🛑 Scheduler stopped.")

        scheduler.shutdown()