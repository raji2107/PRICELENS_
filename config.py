
import os

# ==============================
# DATABASE CONFIGURATION
# ==============================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "pricelens")


# ==============================
# EMAIL CONFIGURATION
# ==============================

MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True

MAIL_USERNAME = "purplegalaxies07@gmail.com"
MAIL_PASSWORD = "ljvw tpjb ntce zpwj"