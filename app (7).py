import os
import re
import html
from urllib.parse import urlencode
import json
import sqlite3
import uuid
import secrets
import hmac
import random
import requests
from datetime import datetime, timedelta

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string,
    flash,
    send_from_directory,
    jsonify,
    url_for
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


# =========================================================
# Uy77
# =========================================================

app = Flask(__name__)

app.secret_key = "KOSHONA_UZ_SECRET_KEY_2026_CHANGE_THIS"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "koshona.db")
UPLOADS = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOADS, exist_ok=True)


# =========================================================
# ASOSIY SOZLAMALAR
# =========================================================

ADMIN_PHONE = "998901234567"
ADMIN_DEFAULT_PASSWORD = "admin123"

VIP_PRICE = 50000
TOP_PRICE = 30000
UP_PRICE = 20000

OTP_EXPIRE_MINUTES = 5

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}


# =========================================================
# SMS ESKIZ
# =========================================================

ESKIZ_EMAIL = ""
ESKIZ_PASSWORD = ""


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def table_columns(c, table_name):
    return {
        row["name"]
        for row in c.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


# =========================================================
# O'ZBEKISTON: VILOYATLAR VA TUMANLAR
# =========================================================
# Ro'yxatni shu yerda tahrirlash mumkin (yangi tuman qo'shish yoki nomini tuzatish).

UZ_REGIONS = {
    "Toshkent shahri": [
        "Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug'bek", "Olmazor", "Sergeli",
        "Shayxontohur", "Uchtepa", "Yakkasaroy", "Yashnobod", "Yunusobod", "Yangihayot",
    ],
    "Toshkent viloyati": [
        "Angren shahri", "Bekobod shahri", "Chirchiq shahri", "Nurafshon shahri",
        "Ohangaron shahri", "Olmaliq shahri", "Yangiyo'l shahri",
        "Bekobod tumani", "Bo'ka", "Bo'stonliq", "Chinoz", "Ohangaron tumani", "Oqqo'rg'on",
        "Parkent", "Piskent", "Qibray", "Quyichirchiq", "O'rtachirchiq", "Toshkent tumani",
        "Yangiyo'l tumani", "Yuqorichirchiq", "Zangiota",
    ],
    "Andijon viloyati": [
        "Andijon shahri", "Xonobod shahri", "Andijon tumani", "Asaka", "Baliqchi", "Bo'z",
        "Buloqboshi", "Izboskan", "Jalaquduq", "Xo'jaobod", "Qo'rg'ontepa", "Marhamat",
        "Oltinko'l", "Paxtaobod", "Shahrixon", "Ulug'nor",
    ],
    "Buxoro viloyati": [
        "Buxoro shahri", "Kogon shahri", "Buxoro tumani", "G'ijduvon", "Jondor", "Kogon tumani",
        "Olot", "Peshku", "Qorako'l", "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent",
    ],
    "Farg'ona viloyati": [
        "Farg'ona shahri", "Marg'ilon shahri", "Qo'qon shahri", "Quvasoy shahri",
        "Bag'dod", "Beshariq", "Buvayda", "Dang'ara", "Farg'ona tumani", "Furqat", "Oltiariq",
        "O'zbekiston tumani", "Qo'shtepa", "Quva", "Rishton", "So'x", "Toshloq", "Uchko'prik",
        "Yozyovon",
    ],
    "Jizzax viloyati": [
        "Jizzax shahri", "Arnasoy", "Baxmal", "Do'stlik", "Forish", "G'allaorol", "Mirzacho'l",
        "Paxtakor", "Sharof Rashidov", "Yangiobod", "Zafarobod", "Zarbdor", "Zomin",
    ],
    "Xorazm viloyati": [
        "Urganch shahri", "Xiva shahri", "Bog'ot", "Gurlan", "Hazorasp", "Xiva tumani", "Xonqa",
        "Qo'shko'pir", "Shovot", "Tuproqqal'a", "Urganch tumani", "Yangiariq", "Yangibozor",
    ],
    "Namangan viloyati": [
        "Namangan shahri", "Chortoq", "Chust", "Davlatobod", "Kosonsoy", "Mingbuloq",
        "Namangan tumani", "Norin", "Pop", "To'raqo'rg'on", "Uchqo'rg'on", "Uychi", "Yangiqo'rg'on",
    ],
    "Navoiy viloyati": [
        "Navoiy shahri", "Zarafshon shahri", "Karmana", "Konimex", "Navbahor", "Nurota",
        "Qiziltepa", "Tomdi", "Uchquduq", "Xatirchi",
    ],
    "Qashqadaryo viloyati": [
        "Qarshi shahri", "Shahrisabz shahri", "Chiroqchi", "Dehqonobod", "G'uzor", "Kasbi",
        "Kitob", "Koson", "Ko'kdala", "Mirishkor", "Muborak", "Nishon", "Qamashi",
        "Qarshi tumani", "Shahrisabz tumani", "Yakkabog'",
    ],
    "Qoraqalpog'iston Respublikasi": [
        "Nukus shahri", "Taxiatosh shahri", "Amudaryo", "Beruniy", "Bo'zatov", "Chimboy",
        "Ellikqal'a", "Kegeyli", "Mo'ynoq", "Nukus tumani", "Qanliko'l", "Qo'ng'irot",
        "Qorao'zak", "Shumanay", "Taxtako'pir", "To'rtko'l", "Xo'jayli",
    ],
    "Samarqand viloyati": [
        "Samarqand shahri", "Kattaqo'rg'on shahri", "Bulung'ur", "Ishtixon", "Jomboy",
        "Kattaqo'rg'on tumani", "Narpay", "Nurobod", "Oqdaryo", "Pastdarg'om", "Paxtachi",
        "Payariq", "Qo'shrabot", "Samarqand tumani", "Toyloq", "Urgut",
    ],
    "Sirdaryo viloyati": [
        "Guliston shahri", "Shirin shahri", "Yangiyer shahri", "Boyovut", "Guliston tumani",
        "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod", "Sirdaryo tumani", "Xovos",
    ],
    "Surxondaryo viloyati": [
        "Termiz shahri", "Angor", "Bandixon", "Boysun", "Denov", "Jarqo'rg'on", "Muzrabot",
        "Oltinsoy", "Qiziriq", "Qumqo'rg'on", "Sariosiyo", "Sherobod", "Sho'rchi",
        "Termiz tumani", "Uzun",
    ],
}


def geo_norm(text):
    t = (text or "").lower()
    for ch in ("'", "’", "ʻ", "ʼ", "`", "‘", "-", " "):
        t = t.replace(ch, "")
    return t


def geo_valid(region, district):
    return region in UZ_REGIONS and district in UZ_REGIONS[region]


def geo_guess(city, district):
    """Eski (erkin matnli) shahar/tuman qiymatlarini viloyat/tumanga moslaydi."""
    city, district = (city or "").strip(), (district or "").strip()
    region = city if city in UZ_REGIONS else ""

    if not region and city:
        nc = geo_norm(city)
        for name in UZ_REGIONS:
            base = geo_norm(name.replace(" viloyati", "").replace(" shahri", "").replace(" Respublikasi", ""))
            if nc == geo_norm(name) or nc == base or nc == base + "viloyati" or nc == base + "shahri":
                region = name
                break
        if region == "Toshkent viloyati" and geo_norm(city) in ("toshkent", "toshkentshahri", "toshkentshahar"):
            region = "Toshkent shahri"

    if not region and district:
        nd = geo_norm(district)
        found = [r for r, ds in UZ_REGIONS.items() if any(geo_norm(d) == nd for d in ds)]
        if len(found) == 1:
            region = found[0]

    if not region:
        return city, district

    nd = geo_norm(district)
    for d in UZ_REGIONS[region]:
        if geo_norm(d) == nd or geo_norm(d.replace(" shahri", "").replace(" tumani", "")) == nd:
            return region, d
    return region, district


def migrate_geo(c):
    for r in c.execute("SELECT id, city, district FROM listings").fetchall():
        region, district = geo_guess(r["city"], r["district"])
        if (region, district) != ((r["city"] or "").strip(), (r["district"] or "").strip()):
            c.execute("UPDATE listings SET city=?, district=? WHERE id=?", (region, district, r["id"]))


def price_fmt(value, currency):
    try:
        n = f"{int(float(value or 0)):,}".replace(",", " ")
    except Exception:
        n = "0"
    cur = (currency or "USD").upper()
    if cur == "UZS":
        return f"{n} so'm"
    if cur == "EUR":
        return f"{n} €"
    return f"{n} $"


def price_of(row):
    try:
        cur = row["currency"]
    except Exception:
        cur = None
    return price_fmt(row["price"], cur)


def init_db():

    c = db()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT '',
        phone TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        balance INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        blocked INTEGER DEFAULT 0,
        block_reason TEXT DEFAULT '',
        blocked_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        price INTEGER DEFAULT 0,
        property_type TEXT DEFAULT 'Kvartira',
        city TEXT DEFAULT 'Toshkent',
        district TEXT DEFAULT '',
        address TEXT DEFAULT '',
        rooms INTEGER DEFAULT 1,
        area REAL DEFAULT 0,
        image TEXT DEFAULT '',
        images TEXT DEFAULT '',
        latitude REAL,
        longitude REAL,
        category_id INTEGER,
        listing_kind TEXT DEFAULT 'real_estate',
        brand TEXT DEFAULT '',
        model TEXT DEFAULT '',
        production_year INTEGER,
        body_type TEXT DEFAULT '',
        mileage INTEGER DEFAULT 0,
        fuel_type TEXT DEFAULT '',
        transmission TEXT DEFAULT '',
        engine_volume TEXT DEFAULT '',
        color TEXT DEFAULT '',
        currency TEXT DEFAULT 'USD',
        condition TEXT DEFAULT '',
        contact_phone TEXT DEFAULT '',
        vip INTEGER DEFAULT 0,
        top INTEGER DEFAULT 0,
        vip_until TEXT,
        top_until TEXT,
        bumped_at TEXT,
        up_until TEXT,
        hidden INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        listing_id INTEGER,
        service TEXT,
        amount INTEGER DEFAULT 0,
        status TEXT DEFAULT 'paid',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS balance_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        admin_id INTEGER,
        amount INTEGER NOT NULL,
        old_balance INTEGER DEFAULT 0,
        new_balance INTEGER DEFAULT 0,
        reason TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS auth_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        event TEXT NOT NULL,
        is_new INTEGER DEFAULT 0,
        ip TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_auth_events_phone ON auth_events(phone, event, created_at);

    CREATE TABLE IF NOT EXISTS payme_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payme_id TEXT UNIQUE NOT NULL,
        payme_time INTEGER,
        order_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        state INTEGER NOT NULL,
        create_time INTEGER NOT NULL,
        perform_time INTEGER DEFAULT 0,
        cancel_time INTEGER DEFAULT 0,
        reason INTEGER
    );

    CREATE TABLE IF NOT EXISTS click_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT DEFAULT 'new',
        click_trans_id TEXT,
        click_paydoc_id TEXT,
        error_note TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        paid_at TEXT
    );

    CREATE TABLE IF NOT EXISTS topup_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        receipt TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        admin_note TEXT DEFAULT '',
        reviewed_by INTEGER,
        reviewed_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '📂',
        kind TEXT DEFAULT 'real_estate',
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # -----------------------------------------------------
    # Eski database bilan moslashtirish
    # -----------------------------------------------------

    click_columns = table_columns(c, "click_orders")
    for _col, _ddl in (
        ("purpose", "TEXT DEFAULT 'balance'"),
        ("service", "TEXT"),
        ("listing_id", "INTEGER"),
        ("draft", "TEXT"),
        ("provider", "TEXT"),
    ):
        if _col not in click_columns:
            c.execute(f"ALTER TABLE click_orders ADD COLUMN {_col} {_ddl}")

    if not c.execute("SELECT 1 FROM settings WHERE key='geo_migrated'").fetchone():
        migrate_geo(c)
        c.execute(
            "INSERT INTO settings(key, value) VALUES('geo_migrated', '1')"
        )

    c.execute("UPDATE users SET name='Uy77 Admin' WHERE name='KOSHONA Admin'")
    c.execute("UPDATE users SET name='Uy77 foydalanuvchisi' WHERE name='KOSHONA foydalanuvchisi'")

    user_columns = table_columns(c, "users")

    if "blocked" not in user_columns:
        c.execute(
            "ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0"
        )

    if "block_reason" not in user_columns:
        c.execute(
            "ALTER TABLE users ADD COLUMN block_reason TEXT DEFAULT ''"
        )

    if "blocked_at" not in user_columns:
        c.execute(
            "ALTER TABLE users ADD COLUMN blocked_at TEXT"
        )

    listing_columns = table_columns(c, "listings")

    if "images" not in listing_columns:
        c.execute(
            "ALTER TABLE listings ADD COLUMN images TEXT DEFAULT ''"
        )

    if "deal_type" not in listing_columns:
        c.execute(
            "ALTER TABLE listings ADD COLUMN deal_type TEXT DEFAULT 'Sotuv'"
        )

    if "mortgage" not in listing_columns:
        c.execute(
            "ALTER TABLE listings ADD COLUMN mortgage INTEGER DEFAULT 0"
        )

    if "up_until" not in listing_columns:
        c.execute(
            "ALTER TABLE listings ADD COLUMN up_until TEXT"
        )

    if "hidden" not in listing_columns:
        c.execute(
            "ALTER TABLE listings ADD COLUMN hidden INTEGER DEFAULT 0"
        )

    # -----------------------------------------------------
    # Bo'limlar / kategoriyalar
    # -----------------------------------------------------
    c.execute("""
        INSERT OR IGNORE INTO categories
        (id, name, slug, icon, kind, sort_order, is_active)
        VALUES (1, 'Ko''chmas mulk', 'kochmas-mulk', '🏠', 'real_estate', 1, 1)
    """)
    c.execute("""
        INSERT OR IGNORE INTO categories
        (id, name, slug, icon, kind, sort_order, is_active)
        VALUES (2, 'Avto', 'avto', '🚗', 'auto', 2, 1)
    """)

    listing_columns = table_columns(c, "listings")
    listing_migrations = {
        "category_id": "ALTER TABLE listings ADD COLUMN category_id INTEGER",
        "listing_kind": "ALTER TABLE listings ADD COLUMN listing_kind TEXT DEFAULT 'real_estate'",
        "brand": "ALTER TABLE listings ADD COLUMN brand TEXT DEFAULT ''",
        "model": "ALTER TABLE listings ADD COLUMN model TEXT DEFAULT ''",
        "production_year": "ALTER TABLE listings ADD COLUMN production_year INTEGER",
        "body_type": "ALTER TABLE listings ADD COLUMN body_type TEXT DEFAULT ''",
        "mileage": "ALTER TABLE listings ADD COLUMN mileage INTEGER DEFAULT 0",
        "fuel_type": "ALTER TABLE listings ADD COLUMN fuel_type TEXT DEFAULT ''",
        "transmission": "ALTER TABLE listings ADD COLUMN transmission TEXT DEFAULT ''",
        "engine_volume": "ALTER TABLE listings ADD COLUMN engine_volume TEXT DEFAULT ''",
        "color": "ALTER TABLE listings ADD COLUMN color TEXT DEFAULT ''",
        "currency": "ALTER TABLE listings ADD COLUMN currency TEXT DEFAULT 'USD'",
        "condition": "ALTER TABLE listings ADD COLUMN condition TEXT DEFAULT ''",
        "contact_phone": "ALTER TABLE listings ADD COLUMN contact_phone TEXT DEFAULT ''",
    }
    for col, statement in listing_migrations.items():
        if col not in listing_columns:
            c.execute(statement)

    c.execute("""
        UPDATE listings
        SET category_id=1,
            listing_kind='real_estate'
        WHERE category_id IS NULL OR category_id=0
    """)

    payment_columns = table_columns(c, "payments")

    if "status" not in payment_columns:
        c.execute(
            "ALTER TABLE payments ADD COLUMN status TEXT DEFAULT 'paid'"
        )

    # -----------------------------------------------------
    # Settings
    # -----------------------------------------------------

    settings = {
        "vip_price": str(VIP_PRICE),
        "top_price": str(TOP_PRICE),
        "up_price": str(UP_PRICE),
    }

    for key, value in settings.items():

        exists = c.execute(
            "SELECT key FROM settings WHERE key=?",
            (key,)
        ).fetchone()

        if not exists:
            c.execute("""
                INSERT INTO settings
                (key, value)
                VALUES (?, ?)
            """, (key, value))

    # -----------------------------------------------------
    # Admin
    # -----------------------------------------------------

    admin = c.execute(
        "SELECT id FROM users WHERE phone=?",
        (ADMIN_PHONE,)
    ).fetchone()

    if not admin:

        c.execute("""
            INSERT INTO users
            (
                name,
                phone,
                password,
                balance,
                is_admin,
                verified,
                blocked
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "Uy77 Admin",
            ADMIN_PHONE,
            generate_password_hash(ADMIN_DEFAULT_PASSWORD),
            1000000,
            1,
            1,
            0
        ))

    else:

        c.execute("""
            UPDATE users
            SET is_admin=1,
                verified=1,
                blocked=0
            WHERE phone=?
        """, (ADMIN_PHONE,))

    c.commit()
    c.close()


init_db()


# =========================================================
# YORDAMCHI
# =========================================================

def get_setting(key, default=0):

    c = db()

    row = c.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    ).fetchone()

    c.close()

    if not row:
        return int(default)

    try:
        return int(row["value"])
    except:
        return int(default)


def service_prices():

    return {
        "free": 0,
        "vip": get_setting("vip_price", VIP_PRICE),
        "top": get_setting("top_price", TOP_PRICE),
        "up": get_setting("up_price", UP_PRICE)
    }


def money(value):

    try:
        value = int(value or 0)
        return f"{value:,}".replace(",", " ") + " so'm"
    except:
        return "0 so'm"


def money_ye(value):

    try:
        value = int(value or 0)
        return f"{value:,}".replace(",", " ") + " y.e."
    except:
        return "0 y.e."


def esc(value):
    return html.escape(str(value or ""))


def clean_phone(phone):

    phone = phone.strip()
    phone = re.sub(r"\D", "", phone)

    if phone.startswith("8"):
        phone = "998" + phone[1:]

    if phone.startswith("9") and len(phone) == 9:
        phone = "998" + phone

    return phone


def valid_phone(phone):
    return bool(re.fullmatch(r"998\d{9}", phone))


def allowed_file(filename):
    return ("." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS)


def save_uploaded_image(file):
    """Yuklangan rasmni JPG formatida siqib saqlaydi."""
    filename = secure_filename(file.filename or "image.jpg")
    if not filename or not allowed_file(filename):
        raise ValueError("Noto'g'ri rasm formati")
    if Image is None:
        ext = filename.rsplit(".", 1)[-1].lower()
        image_name = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOADS, image_name))
        return image_name
    image_name = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(UPLOADS, image_name)
    try:
        file.stream.seek(0)
        img = Image.open(file.stream)
        img.load()
        if ImageOps is not None:
            img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            if img.mode == "P": img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, "white")
            bg.paste(img, mask=img.getchannel("A"))
            img = bg
        else:
            img = img.convert("RGB")
        img.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        img.save(image_path, "JPEG", quality=82, optimize=True, progressive=True)
        return image_name
    except Exception as exc:
        try:
            if os.path.exists(image_path): os.remove(image_path)
        except Exception: pass
        raise ValueError("Rasm fayli buzilgan yoki o'qib bo'lmadi") from exc


def current_user():

    uid = session.get("user_id")

    if not uid:
        return None

    c = db()

    user = c.execute(
        "SELECT * FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    c.close()

    return user


def login_required():

    user = current_user()

    if not user:
        session.pop("user_id", None)
        session.pop("is_admin", None)
        return False

    if user["blocked"]:
        session.clear()
        return False

    return True


def admin_required():

    user = current_user()

    return bool(
        user
        and user["is_admin"]
        and not user["blocked"]
    )


def admin_log(action, details="", conn=None):

    admin = current_user()

    if not admin:
        return

    own_connection = conn is None
    c = conn or db()

    c.execute("""
        INSERT INTO admin_logs
        (admin_id, action, details)
        VALUES (?, ?, ?)
    """, (
        admin["id"],
        action,
        details
    ))

    if own_connection:
        c.commit()
        c.close()


def generate_otp():
    return str(secrets.randbelow(900000) + 100000)


# =========================================================
# SMS
# =========================================================

def send_sms(phone, message):

    phone = clean_phone(phone)

    if ESKIZ_EMAIL and ESKIZ_PASSWORD:

        try:

            session_req = requests.post(
                "https://notify.eskiz.uz/api/auth/login",
                data={
                    "email": ESKIZ_EMAIL,
                    "password": ESKIZ_PASSWORD
                },
                timeout=15
            )

            session_data = session_req.json()

            token = session_data.get(
                "data",
                {}
            ).get("token")

            if not token:

                print("ESKIZ TOKEN OLISHDA XATO:")
                print(session_data)

                return False

            sms_req = requests.post(
                "https://notify.eskiz.uz/api/message/sms/send",
                headers={
                    "Authorization": f"Bearer {token}"
                },
                data={
                    "mobile_phone": phone,
                    "message": message,
                    "from": "4546"
                },
                timeout=15
            )

            result = sms_req.json()

            print("ESKIZ SMS:", result)

            if sms_req.status_code == 200:
                return True

        except Exception as e:

            print("SMS XATO:", e)

            return False

    print("=" * 60)
    print("SMS TEST REJIMI")
    print("Telefon:", phone)
    print("Xabar:", message)
    print("=" * 60)

    return True


def save_otp(phone, code):

    expires = datetime.now() + timedelta(
        minutes=OTP_EXPIRE_MINUTES
    )

    c = db()

    c.execute(
        "DELETE FROM otp_codes WHERE phone=?",
        (phone,)
    )

    c.execute("""
        INSERT INTO otp_codes
        (phone, code, expires_at)
        VALUES (?, ?, ?)
    """, (
        phone,
        code,
        expires.isoformat()
    ))

    c.commit()
    c.close()


def verify_otp(phone, code):

    c = db()

    row = c.execute("""
        SELECT *
        FROM otp_codes
        WHERE phone=?
        ORDER BY id DESC
        LIMIT 1
    """, (phone,)).fetchone()

    if not row:
        c.close()
        return False

    try:
        expires = datetime.fromisoformat(
            row["expires_at"]
        )
    except:
        c.close()
        return False

    if datetime.now() > expires:

        c.execute(
            "DELETE FROM otp_codes WHERE phone=?",
            (phone,)
        )

        c.commit()
        c.close()

        return False

    if str(row["code"]) != str(code).strip():

        c.close()

        return False

    c.execute(
        "DELETE FROM otp_codes WHERE phone=?",
        (phone,)
    )

    c.commit()
    c.close()

    return True



# =========================================================
# BO'LIMLAR / AVTO YORDAMCHILARI
# =========================================================

def slugify(value):
    value = str(value or "").strip().lower()
    value = value.replace("'", "").replace("’", "")
    value = re.sub(r"[^a-z0-9\u0400-\u04ff\u00d1\u00f1]+", "-", value)
    return value.strip("-") or "bolim"


def get_categories(active_only=True):
    c = db()
    sql = "SELECT * FROM categories"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY sort_order, id"
    rows = c.execute(sql).fetchall()
    c.close()
    return rows


def get_category_by_slug(slug):
    c = db()
    row = c.execute("SELECT * FROM categories WHERE slug=?", (slug,)).fetchone()
    c.close()
    return row


def get_category_by_id(category_id):
    c = db()
    row = c.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    c.close()
    return row


CAR_BRANDS = {
    "Abarth":["500","595","695","124 Spider"], "Acura":["Integra","TLX","RDX","MDX","NSX"],
    "Alfa Romeo":["Giulia","Stelvio","Tonale","4C"], "Aston Martin":["Vantage","DB12","DBX","DBS"],
    "Audi":["A1","A3","A4","A5","A6","A7","A8","Q3","Q5","Q7","Q8","TT","R8"],
    "BAIC":["X3","X5","X7","BJ40","BJ60"], "Bentley":["Bentayga","Continental GT","Flying Spur"],
    "BMW":["1 Series","2 Series","3 Series","4 Series","5 Series","6 Series","7 Series","8 Series","X1","X2","X3","X4","X5","X6","X7","XM","Z4"],
    "BYD":["Dolphin","Atto 3","Seal","Han","Song Plus","Qin Plus","Tang"],
    "Cadillac":["CT4","CT5","XT4","XT5","XT6","Escalade","Lyriq"],
    "Changan":["Alsvin","CS35 Plus","CS55 Plus","CS75 Plus","UNI-T","UNI-K","UNI-V"],
    "Chery":["Tiggo 2","Tiggo 4","Tiggo 7","Tiggo 8","Arrizo 5","Arrizo 6"],
    "Chevrolet":["Cobalt","Nexia","Malibu","Malibu 2","Tracker","Equinox","Traverse","Tahoe","Captiva","Onix","Spark","Damas"],
    "Chrysler":["300","Pacifica","Voyager"], "Citroen":["C3","C4","C5 Aircross","C5 X","Berlingo"],
    "Cupra":["Formentor","Born","Leon","Ateca"], "Daewoo":["Nexia","Matiz","Damas","Tico","Espero"],
    "Daihatsu":["Mira","Terios","Rocky","Hijet"], "Dodge":["Challenger","Charger","Durango","Hornet"],
    "Dongfeng":["Shine","T5 Evo","Huge"], "DS":["DS 3","DS 4","DS 7","DS 9"],
    "FAW":["Bestune B70","Bestune T77","Bestune T99","Hongqi H5"], "Ferrari":["Roma","296 GTB","SF90","Purosangue","812"],
    "Fiat":["500","Panda","Tipo","500X","Doblo","Ducato"], "Ford":["Fiesta","Focus","Fusion","Mondeo","Mustang","Bronco","Escape","Explorer","Expedition","F-150","Ranger","Transit"],
    "Genesis":["G70","G80","G90","GV60","GV70","GV80"], "Geely":["Emgrand","Coolray","Atlas","Monjaro","Tugella","Okavango"],
    "GMC":["Terrain","Acadia","Yukon","Sierra","Canyon","Hummer EV"], "Great Wall":["Poer","Wingle"],
    "Haval":["Jolion","H6","H9","Dargo","F7","F7x"], "Honda":["Civic","Accord","City","CR-V","HR-V","Pilot","Odyssey"],
    "Hongqi":["H5","H6","H9","HS5","HS7","E-HS9"], "Hyundai":["i10","i20","i30","Accent","Elantra","Sonata","Tucson","Santa Fe","Palisade","Kona","Ioniq 5","Ioniq 6","Staria"],
    "Infiniti":["Q30","Q50","QX50","QX55","QX60","QX80"], "Isuzu":["D-Max","MU-X","N-Series","F-Series"],
    "JAC":["J7","JS3","JS4","JS6","T8","T9"], "Jaguar":["XE","XF","F-Pace","E-Pace","F-Type","I-Pace"],
    "Jeep":["Renegade","Compass","Cherokee","Grand Cherokee","Wrangler","Gladiator"], "Jetour":["X50","X70","X90","Dashing","Traveller"],
    "Kia":["Picanto","Rio","Cerato","K5","K8","K9","Seltos","Sportage","Sorento","Telluride","Carnival","EV6","EV9"],
    "Lamborghini":["Huracan","Revuelto","Urus"], "Land Rover":["Defender","Discovery","Discovery Sport","Range Rover","Range Rover Sport","Range Rover Velar","Range Rover Evoque"],
    "Lexus":["IS","ES","LS","UX","NX","RX","GX","LX","LC"], "Lincoln":["Corsair","Nautilus","Aviator","Navigator"],
    "Maserati":["Ghibli","Quattroporte","Levante","Grecale","GranTurismo"], "Mazda":["Mazda2","Mazda3","Mazda6","CX-3","CX-30","CX-5","CX-60","CX-90","MX-5"],
    "McLaren":["570S","720S","750S","Artura","GT"], "Mercedes-Benz":["A-Class","C-Class","E-Class","S-Class","CLA","CLS","GLA","GLB","GLC","GLE","GLS","G-Class","V-Class","Sprinter","AMG GT"],
    "MG":["MG3","MG4","MG5","MG6","ZS","HS","RX5","Marvel R"], "Mini":["Cooper","Clubman","Countryman","Aceman"],
    "Mitsubishi":["Mirage","Lancer","ASX","Outlander","Eclipse Cross","Pajero","Triton"], "Nissan":["Micra","Sunny","Sentra","Altima","Maxima","Juke","Qashqai","X-Trail","Pathfinder","Patrol","Navara"],
    "Opel":["Corsa","Astra","Insignia","Mokka","Grandland","Crossland","Zafira"], "Peugeot":["208","308","408","508","2008","3008","5008","Partner","Boxer"],
    "Porsche":["718 Cayman","718 Boxster","911","Taycan","Macan","Cayenne","Panamera"], "RAM":["1500","2500","3500"],
    "Renault":["Clio","Megane","Logan","Sandero","Duster","Arkana","Kaptur","Koleos","Master"], "Rolls-Royce":["Ghost","Phantom","Cullinan","Spectre"],
    "Seat":["Ibiza","Leon","Arona","Ateca","Tarraco"], "Skoda":["Fabia","Scala","Octavia","Superb","Kamiq","Karoq","Kodiaq","Enyaq"],
    "Smart":["Fortwo","Forfour","#1","#3"], "Subaru":["Impreza","Legacy","Forester","Outback","Crosstrek","WRX","BRZ","Solterra"],
    "Suzuki":["Alto","Swift","Baleno","Ciaz","Vitara","S-Cross","Jimny","Ertiga"], "Tesla":["Model 3","Model S","Model X","Model Y","Cybertruck"],
    "Toyota":["Yaris","Corolla","Camry","Avalon","C-HR","RAV4","Highlander","Land Cruiser","Land Cruiser Prado","Fortuner","Hilux","Tacoma","Tundra","Sienna","Supra"],
    "Volkswagen":["Polo","Golf","Jetta","Passat","Arteon","T-Roc","Tiguan","Touareg","Atlas","ID.3","ID.4","ID.7","Transporter"],
    "Volvo":["S60","S90","XC40","XC60","XC90","EX30","EX90"], "Lada":["Granta","Vesta","Niva Legend","Niva Travel","Largus"],
    "UAZ":["Patriot","Hunter","Pickup","Profi"], "Omoda":["C5","C7","S5"], "Jaecoo":["J7","J8"],
    "Exeed":["LX","TXL","VX"], "Li Auto":["L6","L7","L8","L9","Mega"], "NIO":["ET5","ET7","ES6","ES7","ES8","EC6","EC7"],
    "XPeng":["P5","P7","G6","G9","X9"], "Lynk & Co":["01","02","03","05","06","09"], "Rivian":["R1T","R1S"],
    "Lucid":["Air","Gravity"], "ZEEKR":["001","007","X","009","7X"], "Moskvich":["3","6","3e"]
}

CAR_BODY_TYPES = ["Sedan","Hatchback","Universal","Krossover","SUV","Kupe","Kabriolet","Miniven","Pikap","Furgon","Mikroavtobus","Boshqa"]
CAR_FUEL_TYPES = ["Benzin","Dizel","Gaz","Gibrid","Elektr","Benzin/Gaz"]
CAR_TRANSMISSIONS = ["Mexanika","Avtomat","Robot","Variator"]
CAR_CONDITIONS = ["Yangi","Yaxshi","O'rtacha","Ta'mir talab"]
CAR_COLORS = ["Oq","Qora","Kulrang","Kumush","Ko'k","Qizil","Yashil","Jigarrang","Sariq","Oltin","Binafsha","Boshqa"]


def service_cards(category):
    prices = service_prices()
    slug = esc(category["slug"])
    name = esc(category["name"])
    icon = esc(category["icon"])
    return f"""
    <div class="form-card" style="max-width:1100px">
      <h1>{icon} {name} e'loni</h1>
      <p style="color:#777">Avval xizmatni tanlang, keyin e'lon ma'lumotlarini kiriting.</p>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px">
        <div style="border:2px solid #ddd;border-radius:20px;padding:24px">
          <div style="font-size:38px">🆓</div><h2>TEKIN</h2>
          <div style="font-size:24px;font-weight:900">0 so'm</div><p>Oddiy e'lon.</p>
          <a class="post-btn" href="/add?service=free&category={slug}">Tekin e'lon joylash →</a>
        </div>
        <div style="border:2px solid #f1d35a;border-radius:20px;padding:24px;background:#fffdf0">
          <div style="font-size:38px">👑</div><h2>VIP</h2>
          <div style="font-size:24px;font-weight:900">{money(prices["vip"])}</div><p>E'lon VIP sifatida ajratiladi.</p>
          <a class="post-btn" href="/add?service=vip&category={slug}">VIP e'lon joylash →</a>
        </div>
        <div style="border:2px solid #ffb347;border-radius:20px;padding:24px;background:#fff9f1">
          <div style="font-size:38px">🔥</div><h2>TOP</h2>
          <div style="font-size:24px;font-weight:900">{money(prices["top"])}</div><p>E'lon TOP sifatida ajratiladi.</p>
          <a class="post-btn" href="/add?service=top&category={slug}">TOP e'lon joylash →</a>
        </div>
        <div style="border:2px solid #8fd3ff;border-radius:20px;padding:24px;background:#f7fcff">
          <div style="font-size:38px">🚀</div><h2>TEPAGA KO'TARISH</h2>
          <div style="font-size:24px;font-weight:900">{money(prices["up"])}</div><p>Mavjud e'lonni tepaga ko'taradi.</p>
          <a class="post-btn" href="/profile">Mavjud e'lonni tanlash →</a>
        </div>
      </div>
    </div>
    """


# =========================================================
# PUBLIC HTML
# =========================================================

BASE_HTML = """
<!doctype html>
<html lang="{{ lang }}">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>{{ title or "Uy77" }}</title>
<meta name="theme-color" content="#0B1530">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<link
    rel="preconnect"
    href="https://fonts.googleapis.com"
>

<link
    rel="preconnect"
    href="https://fonts.gstatic.com"
    crossorigin
>

<link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
    rel="stylesheet"
>

<link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
>

<script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>

<style>

:root{
--yellow:#f6c900;
--yellow2:#ffd83d;
--ink:#171717;
--muted:#737373;
--line:#ececec;
--bg:#fafafa;
--card:#fff;
--green:#19a463;
--red:#e34d4d;
--shadow:0 10px 35px rgba(20,20,20,.08)
}

*{
box-sizing:border-box
}

html{
scroll-behavior:smooth
}

body{
margin:0;
font-family:Inter,Arial,sans-serif;
background:var(--bg);
color:var(--ink)
}

a{
text-decoration:none;
color:inherit
}

button,
input,
select,
textarea{
font:inherit
}

button{
cursor:pointer
}

.container{
width:min(1240px,calc(100% - 32px));
margin:0 auto
}

.topbar{
height:76px;
background:#fff;
border-bottom:1px solid #eee;
display:flex;
align-items:center
}

.topbar-inner{
width:min(1240px,calc(100% - 32px));
margin:auto;
display:flex;
align-items:center;
gap:20px
}

.logo{
display:flex;
align-items:center;
gap:10px;
font-size:20px;
font-weight:800;
white-space:nowrap
}

.logo-mark{
width:36px;
height:36px;
border-radius:12px;
background:var(--yellow);
display:grid;
place-items:center;
font-size:19px
}

.lang{
display:flex;
align-items:center;
gap:5px;
color:#555;
font-size:14px
}

.nav-search{
flex:1;
max-width:380px;
position:relative
}

.nav-search input{
width:100%;
height:42px;
border:1px solid transparent;
background:#f6f6f6;
border-radius:22px;
padding:0 18px 0 42px;
outline:none
}

.nav-search input:focus{
background:#fff;
border-color:#ddd
}

.search-icon{
position:absolute;
left:15px;
top:11px;
color:#999
}

.nav-actions{
margin-left:auto;
display:flex;
align-items:center;
gap:8px
}

.icon-btn{
width:40px;
height:40px;
border-radius:50%;
display:grid;
place-items:center;
background:transparent;
border:0;
font-size:19px
}

.icon-btn:hover{
background:#f5f5f5
}

.post-btn,
.btn-yellow{
background:var(--yellow);
color:#151515;
border:0;
border-radius:12px;
padding:12px 18px;
font-weight:800;
display:inline-flex;
align-items:center;
justify-content:center;
gap:7px
}

.post-btn:hover,
.btn-yellow:hover{
background:var(--yellow2)
}

.avatar{
width:38px;
height:38px;
border-radius:50%;
background:#e9e9e9;
display:grid;
place-items:center;
font-weight:800
}

.main{
padding:22px 0 50px
}

.hero{
background:linear-gradient(120deg,#fff8d7,#fff);
border:1px solid #f0e5aa;
border-radius:24px;
padding:32px;
position:relative;
overflow:hidden
}

.hero h1{
font-size:38px;
line-height:1.1;
margin:0 0 10px;
max-width:650px
}

.hero p{
color:#666;
margin:0 0 22px;
max-width:680px
}

.hero-search{
display:flex;
gap:10px;
max-width:760px;
background:#fff;
padding:8px;
border:1px solid #e7e7e7;
border-radius:15px;
box-shadow:var(--shadow);
position:relative;
z-index:2
}

.hero-search input{
flex:1;
border:0;
outline:0;
padding:0 12px;
min-width:0
}

.hero-search button{
border:0;
border-radius:11px;
background:var(--yellow);
padding:12px 20px;
font-weight:800
}

.viewbar{
display:flex;
align-items:center;
gap:10px;
margin:20px 0 14px;
overflow:auto
}

.view-pill{
border:1px solid #eee;
background:#fff;
padding:10px 15px;
border-radius:12px;
white-space:nowrap;
color:#666
}

.view-pill.active{
background:var(--yellow);
border-color:var(--yellow);
color:#111;
font-weight:800
}

.filter-row{
display:flex;
gap:9px;
overflow:auto;
margin-bottom:25px
}

.filter-chip{
background:#fff;
border:1px solid #eee;
border-radius:20px;
padding:9px 14px;
color:#555;
white-space:nowrap
}

.tabs{
display:flex;
background:#f1f1f1;
border-radius:13px;
padding:4px;
margin-bottom:15px
}

.tabs a{
flex:1;
text-align:center;
padding:10px;
border-radius:10px;
color:#777;
font-weight:700
}

.tabs a.active{
background:var(--yellow);
color:#111
}

.section-head{
display:flex;
align-items:end;
justify-content:space-between;
gap:15px;
margin:30px 0 14px
}

.section-head h2{
margin:0;
font-size:24px
}

.section-head p{
margin:4px 0 0;
color:#999;
font-size:13px
}

.section-link{
color:#777;
font-size:14px
}

.listing-strip{
display:grid;
grid-auto-flow:column;
grid-auto-columns:minmax(220px,1fr);
gap:14px;
overflow-x:auto;
padding:2px 2px 10px
}

.property-card{
background:var(--card);
border-radius:17px;
overflow:hidden;
border:1px solid #eee;
box-shadow:0 4px 18px rgba(0,0,0,.05);
transition:.18s
}

.property-card:hover{
transform:translateY(-2px);
box-shadow:var(--shadow)
}

.property-image{
height:205px;
background:#eee;
position:relative;
overflow:hidden
}

.property-image img{
width:100%;
height:100%;
object-fit:cover;
display:block
}

.user-pill{
position:absolute;
top:10px;
left:10px;
z-index:2;
background:rgba(255,255,255,.92);
padding:5px 8px;
border-radius:20px;
font-size:11px;
font-weight:700;
max-width:62%;
overflow:hidden;
text-overflow:ellipsis;
white-space:nowrap
}

.badge-stack{
position:absolute;
top:10px;
right:10px;
z-index:3;
display:flex;
gap:5px
}

.badge{
display:inline-flex;
align-items:center;
gap:4px;
padding:5px 8px;
border-radius:9px;
font-size:10px;
font-weight:900
}

.badge.vip{
background:var(--yellow);
color:#111
}

.badge.top{
background:#ffe57a;
color:#111
}

.property-overlay{
position:absolute;
left:12px;
right:12px;
bottom:10px;
z-index:2;
color:#fff
}

.property-price{
font-size:19px;
font-weight:900;
text-shadow:0 1px 3px rgba(0,0,0,.4)
}

.property-title{
font-size:12px;
font-weight:700;
margin-top:4px;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis
}

.property-body{
padding:13px
}

.meta{
display:flex;
gap:7px;
flex-wrap:wrap;
color:#777;
font-size:12px
}

.meta span{
background:#f7f7f7;
border-radius:8px;
padding:6px 7px
}

.property-bottom{
display:flex;
align-items:center;
justify-content:space-between;
margin-top:10px
}

.small-link{
font-size:12px;
font-weight:800
}

.all-grid{
display:grid;
grid-template-columns:repeat(4,1fr);
gap:16px
}

.all-grid .property-image{
height:190px
}

.empty{
padding:30px;
background:#fff;
border:1px dashed #ddd;
border-radius:15px;
color:#777;
text-align:center
}

.stats{
display:grid;
grid-template-columns:repeat(4,1fr);
gap:12px;
margin:20px 0
}

.stat{
background:#fff;
border:1px solid #eee;
border-radius:15px;
padding:16px
}

.stat strong{
font-size:24px;
display:block
}

.form-card{
max-width:850px;
margin:25px auto;
background:#fff;
border:1px solid #eee;
border-radius:20px;
padding:25px;
box-shadow:var(--shadow)
}

.form-group{
margin-bottom:15px
}

.form-group label,
label{
display:block;
margin-bottom:7px;
font-weight:700;
font-size:14px
}

input,
select,
textarea{
width:100%;
padding:12px 13px;
border:1px solid #ddd;
border-radius:11px;
background:#fff;
outline:none
}

input:focus,
select:focus,
textarea:focus{
border-color:#c7a900;
box-shadow:0 0 0 3px rgba(246,201,0,.13)
}

textarea{
min-height:130px;
resize:vertical
}

.btn{
display:inline-flex;
align-items:center;
justify-content:center;
gap:7px;
border:0;
border-radius:11px;
padding:11px 16px;
background:#191919;
color:#fff;
font-weight:700
}

.btn-green{
background:var(--green)
}

.btn-red{
background:var(--red)
}

.location-box{
background:#f6fff9;
border:1px solid #bde8ce;
padding:14px;
border-radius:12px;
margin-bottom:16px
}

.flash{
margin-bottom:12px
}

.alert{
padding:12px 15px;
background:#fff7cc;
border:1px solid #f0df79;
border-radius:12px
}

.footer{
background:#191919;
color:#fff;
padding:35px 0;
margin-top:30px
}

.footer-inner{
width:min(1240px,calc(100% - 32px));
margin:auto;
display:flex;
justify-content:space-between;
gap:20px;
flex-wrap:wrap;
color:#aaa
}

.footer strong{
color:#fff
}

.table-wrap{
overflow:auto;
background:#fff;
border:1px solid #eee;
border-radius:15px
}

table{
width:100%;
border-collapse:collapse
}

th,
td{
padding:12px;
border-bottom:1px solid #eee;
text-align:left;
white-space:nowrap
}

th{
background:#191919;
color:#fff
}

.price-marker{
background:var(--yellow);
border:2px solid #191919;
color:#111;
font-weight:900;
font-size:13px;
padding:5px 9px;
border-radius:9px;
white-space:nowrap;
box-shadow:0 3px 9px rgba(0,0,0,.25)
}

.map-popup{
width:230px
}

.map-popup img{
width:100%;
height:130px;
object-fit:cover;
border-radius:8px
}

.map-popup h3{
margin:8px 0 5px
}

.map-price{
font-weight:900;
font-size:18px
}

.map-wrap{
background:#fff;
border:1px solid #eee;
border-radius:18px;
padding:10px
}

#map{
width:100%;
height:650px;
border-radius:13px;
overflow:hidden
}

.split-form{
display:grid;
grid-template-columns:1fr 1fr;
gap:14px
}

.full{
grid-column:1/-1
}

.upload-box{
border:2px dashed #ddd;
border-radius:14px;
padding:22px;
text-align:center;
background:#fafafa
}

.preview{
display:none;
width:100%;
height:230px;
object-fit:cover;
border-radius:13px;
margin-top:10px
}

@media(max-width:1000px){

.all-grid{
grid-template-columns:repeat(3,1fr)
}

.nav-search{
max-width:280px
}

.stats{
grid-template-columns:repeat(2,1fr)
}

}

@media(max-width:700px){

.topbar{
height:auto;
padding:10px 0
}

.topbar-inner{
flex-wrap:wrap;
gap:8px
}

.logo{
font-size:18px
}

.nav-search{
order:5;
max-width:none;
flex-basis:100%
}

.nav-actions{
gap:2px
}

.nav-actions .icon-btn{
display:none
}

.post-btn{
padding:10px 12px;
font-size:12px
}

.container{
width:min(100% - 20px,1240px)
}

.hero{
padding:22px 18px;
border-radius:18px
}

.hero h1{
font-size:29px
}

.all-grid{
grid-template-columns:1fr 1fr;
gap:10px
}

.all-grid .property-image{
height:155px
}

.stats{
grid-template-columns:1fr 1fr
}

.split-form{
grid-template-columns:1fr
}

.full{
grid-column:auto
}

.form-card{
padding:17px
}

#map{
height:520px
}

}

@media(max-width:430px){

.all-grid{
grid-template-columns:1fr
}

.all-grid .property-image{
height:200px
}

.stats{
grid-template-columns:1fr 1fr
}

}


/* ===== Uy77 bosh sahifa (Joymee uslubi) ===== */
.kc-nav{display:flex;gap:8px;margin:18px 0 0;flex-wrap:wrap}
.kc-pill{padding:9px 18px;border-radius:999px;background:#f1f1f1;font-weight:700;font-size:14px;color:#555}
.kc-pill.on{background:var(--ink);color:#fff}
.kc-hero{margin:16px 0 8px;border-radius:24px;padding:34px 28px;background:linear-gradient(135deg,#fff6d6,#ffe08a);position:relative;overflow:hidden}
.kc-hero:after{content:"";position:absolute;right:-50px;bottom:-70px;width:240px;height:240px;border-radius:50%;background:rgba(255,255,255,.4)}
.kc-hero h1{margin:0 0 8px;font-size:clamp(26px,4.5vw,40px);letter-spacing:-.8px;position:relative}
.kc-hero p{margin:0 0 20px;color:#555;max-width:540px;position:relative}
.kc-search{display:flex;gap:8px;background:#fff;border-radius:16px;padding:8px;max-width:660px;position:relative;box-shadow:0 10px 26px rgba(0,0,0,.12)}
.kc-search input{flex:1;min-width:0;border:0;outline:0;padding:10px 12px;font-size:14px;background:none}
.kc-search button{background:var(--yellow);border:0;border-radius:11px;padding:10px 18px;font-weight:800;white-space:nowrap}
.kc-bar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:16px 0 10px;flex-wrap:wrap}
.kc-chips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px}
.kc-chip{border:1px solid var(--line);border-radius:999px;padding:8px 15px;font-size:13px;font-weight:600;white-space:nowrap;background:#fff}
.kc-chip.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.kc-chip.y{background:var(--yellow);border-color:var(--yellow)}
.kc-views{display:flex;background:#f1f1f1;border-radius:12px;padding:3px}
.kc-views a{padding:7px 14px;border-radius:9px;font-size:13px;font-weight:700;color:#777}
.kc-views a.on{background:#fff;color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.kc-sec{margin-top:28px}
.kc-head{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;margin-bottom:12px}
.kc-head h2{margin:0;font-size:22px;letter-spacing:-.3px}
.kc-head p{margin:2px 0 0;color:var(--muted);font-size:13px}
.kc-more{font-weight:700;font-size:13px;white-space:nowrap}
.kc-strip{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 14px;scroll-snap-type:x mandatory}
.kc-card{flex:0 0 250px;scroll-snap-align:start;background:#fff;border:1px solid var(--line);border-radius:20px;overflow:hidden;transition:.2s;display:block}
.kc-card:hover{transform:translateY(-4px);box-shadow:var(--shadow)}
.kc-img{height:160px;position:relative;background:#f1f1f1;overflow:hidden}
.kc-img img{width:100%;height:100%;object-fit:cover;display:block}
.kc-ph{height:100%;display:grid;place-items:center;font-size:40px;background:linear-gradient(180deg,#e4eefc,#f6ecd6)}
.kc-b{position:absolute;left:10px;top:10px;font-size:11px;font-weight:800;padding:4px 9px;border-radius:7px;background:var(--yellow);color:#171717}
.kc-b.vip{background:#e53935;color:#fff}
.kc-body{padding:12px 14px 14px}
.kc-price{font-weight:800;font-size:19px}
.kc-title{font-size:14px;font-weight:600;margin:3px 0 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kc-meta{font-size:12px;color:var(--muted)}
.kc-tags{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
.kc-tags span{background:#f1f1f1;padding:3px 9px;border-radius:7px;font-size:11px;font-weight:700}
.kc-empty{padding:26px;color:var(--muted);background:#fff;border:1px dashed var(--line);border-radius:16px;width:100%;text-align:center}
.kc-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:34px 0 10px}
.kc-stats div{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px;text-align:center}
.kc-stats b{display:block;font-size:24px}
.kc-stats span{font-size:12px;color:var(--muted)}
@media(max-width:700px){.kc-hero{padding:24px 18px}.kc-card{flex-basis:220px}}


.kc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.kc-grid .kc-card{flex:none}
.kc-card i,.kc-chip i,.kc-pill i,.kc-views i,.kc-search i,.kd-btn i{font-style:normal}
.kd-wrap{max-width:1100px;margin:18px auto}
.kd-back{display:inline-block;margin-bottom:12px;font-weight:700;color:var(--muted)}
.kd-grid{display:grid;grid-template-columns:1.5fr 1fr;gap:18px;align-items:start}
.kd-photo{height:400px;border-radius:22px;overflow:hidden;background:#f1f1f1}
.kd-photo img{width:100%;height:100%;object-fit:cover;display:block}
.kd-thumbs{display:flex;gap:8px;overflow-x:auto;margin:10px 0}
.kd-thumbs img{width:84px;height:64px;object-fit:cover;border-radius:10px;cursor:pointer;border:1px solid var(--line)}
.kd-box{background:#fff;border:1px solid var(--line);border-radius:20px;padding:18px;margin-bottom:14px}
.kd-box h3{margin:0 0 8px}
.kd-title{margin:4px 0 6px;font-size:24px;letter-spacing:-.4px}
.kd-price{font-size:28px;font-weight:800;margin-bottom:14px}
.kd-btn{display:block;text-align:center;background:var(--yellow);border-radius:14px;padding:14px;font-weight:800;margin-bottom:10px}
.kd-btn.ghost{background:#f1f1f1}
.kd-owner{color:var(--muted);font-size:14px;margin-top:6px}
.kd-specs{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.kd-spec{display:flex;gap:10px;align-items:center}
.kd-spec i{font-style:normal;width:36px;height:36px;border-radius:11px;background:#f6f6f6;display:grid;place-items:center}
.kd-spec small{display:block;color:var(--muted);font-size:11px}
.kd-spec b{font-size:13px}
.kc-tab{display:none}
@media(max-width:820px){
  .kd-grid{grid-template-columns:1fr}.kd-photo{height:260px}
  .kd-left{display:contents}.kd-photo{order:1}.kd-thumbs{order:2}.kd-grid aside{order:3}.kd-desc{order:4}
  body{padding-bottom:78px}
  .kc-tab{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:50;background:#fff;border-top:1px solid var(--line);justify-content:space-around;align-items:flex-end;padding:6px 4px calc(8px + env(safe-area-inset-bottom,0px))}
  .kc-ti{flex:1;text-align:center;font-size:11px;font-weight:600;color:var(--muted)}
  .kc-ti i{display:block;font-style:normal;font-size:22px;line-height:1.2}
  .kc-ti.on{color:var(--ink)}
  .kc-ti.add{color:var(--ink)}
  .kc-ti.add i{width:46px;height:46px;border-radius:50%;background:var(--yellow);display:grid;place-items:center;margin:-22px auto 2px;box-shadow:0 0 0 5px #fff,0 6px 16px rgba(246,201,0,.5);font-weight:800}
  .topbar{height:auto;padding:8px 0}
  .topbar-inner{flex-wrap:wrap;gap:10px}
}


.kc-loc{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;border:1.5px solid var(--yellow);border-radius:16px;padding:12px;background:#fff;margin:10px 0 6px}
.kc-loc>div{flex:1;min-width:150px}
.kc-loc label{display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px}
.kc-loc select{width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;font-size:14px;background:#fff}
.kc-loc select:disabled{background:#f3f3f3;color:#aaa}
.kc-reset{font-size:13px;color:var(--muted);text-decoration:underline;padding:10px 4px}
.kc-tags{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}
.kc-tag{background:#e8f1fb;color:#1c5fa8;font-size:12px;font-weight:700;padding:4px 11px;border-radius:999px}


.logo-img{height:42px;width:auto;display:block}
@media(max-width:700px){.logo-img{height:36px}}
</style>

</head>

<body>

<header class="topbar">

<div class="topbar-inner">

<a href="/" class="logo" aria-label="Uy77"><img src="/uy77-logo.svg" alt="Uy77" class="logo-img"></a>

<div class="lang">
<select id="languageSelect" aria-label="Language" onchange="changeLanguage(this.value)" style="border:0;background:transparent;font-weight:700;cursor:pointer;outline:none">
<option value="uz" {% if lang == 'uz' %}selected{% endif %}>🌐 UZ</option>
<option value="ru" {% if lang == 'ru' %}selected{% endif %}>🌐 RU</option>
<option value="en" {% if lang == 'en' %}selected{% endif %}>🌐 EN</option>
</select>
</div>

<form
class="nav-search"
action="/"
method="get"
>

<span class="search-icon">⌕</span>

<input
name="q"
value="{{ request.args.get('q','') }}"
placeholder="Qidirish..."
>

</form>

<div class="nav-actions">

<a
class="icon-btn"
href="/listings"
title="E'lonlar"
>
⌕
</a>

<a
class="icon-btn"
href="/map"
title="Xarita"
>
♡
</a>

{% if session.get('user_id') %}

<a
class="post-btn"
href="/post-ad"
>
＋ E'lon joylash
</a>

<a
class="avatar"
href="/profile"
>
👤
</a>

{% else %}

<a
class="post-btn"
href="/login"
>
Kirish
</a>

<a
class="avatar"
href="/register"
>
👤
</a>

{% endif %}

</div>

</div>

</header>

<main class="main">

<div class="container">

{% with messages = get_flashed_messages() %}

{% if messages %}

<div class="flash">

{% for message in messages %}

<div class="alert">
{{ message }}
</div>

{% endfor %}

</div>

{% endif %}

{% endwith %}

{{ content|safe }}

</div>

</main>

<footer class="footer">

<div class="footer-inner">

<div>
<img src="/uy77-logo-dark.svg" alt="Uy77" style="height:46px;display:block;margin-bottom:6px">
<p>Uy — sizning orzuyingiz!</p>
</div>

<div>
<p>© 2026 Uy77</p>
<p>Ko'chmas mulk platformasi</p>
</div>

</div>

</footer>

{{ mobile_nav|safe }}

<script>
/* Uy77 — UZ / RU / EN translator */
const KOSHONA_I18N = {
  ru: {
    "Qidirish...":"Поиск...","E'lonlar":"Объявления","Xarita":"Карта","E'lon joylash":"Подать объявление","Kirish":"Войти","Ro'yxatdan o'tish":"Регистрация",
    "O'zingizga mos uyni toping":"Найдите подходящий для себя дом","O'zingizga mos uyni toping.":"Найдите подходящий для себя дом.","Ko'chmas mulk platformasi":"Платформа недвижимости",
    "E'lonlar":"Объявления","E'lon":"Объявление","E'lonlar yo'q.":"Объявлений нет.","E'lon topilmadi.":"Объявление не найдено.","Batafsil →":"Подробнее →","Batafsil":"Подробнее",
    "Profil":"Профиль","Mening e’lonlarim":"Мои объявления","Balans":"Баланс","Balansni o'zgartirish":"Изменить баланс","To'lovlar":"Платежи","To‘lovlar tarixi":"История платежей","Xizmatlar":"Услуги",
    "VIP / TOP xizmatlar":"VIP / TOP услуги","Sevimlilar":"Избранное","Xabarlar":"Сообщения","Sozlamalar":"Настройки","Chiqish":"Выйти",
    "Telefon":"Телефон","Telefon raqam":"Номер телефона","Telefoningizga yuborilgan 6 xonali kodni kiriting.":"Введите 6-значный код, отправленный на ваш телефон.","SMS kod olish":"Получить SMS-код","SMS kodi":"SMS-код","SMS tasdiqlash":"Подтверждение SMS",
    "Parol":"Пароль","Parolni qayta kiriting":"Повторите пароль","Ism":"Имя","Ism:":"Имя:","Telefon:":"Телефон:","Manzil":"Адрес","Shahar":"Город","Tuman":"Район","Mulk turi":"Тип недвижимости","Xona":"Комнаты","Maydon, m²":"Площадь, м²","Narx":"Цена","Narxi":"Цена","Narxi:":"Цена:","Tavsif":"Описание",
    "Kvartira":"Квартира","Hovli":"Дом","Yer":"Земельный участок","Ofis":"Офис","Do'kon":"Магазин","Sotuv":"Продажа","Ijara":"Аренда","Kunlik":"Посуточно",
    "Oddiy":"Обычное","TEKIN":"БЕСПЛАТНО","TOP":"TOP","VIP":"VIP","UP":"UP","Tepaga":"Поднять вверх","Ko'tarilgan":"Поднято",
    "VIP e'lonlar":"VIP объявления","TOP e'lonlar":"TOP объявления","Tepaga ko'tarilgan e'lonlar":"Поднятые объявления","VIP e'lon joylash →":"Разместить VIP объявление →","TOP e'lon joylash →":"Разместить TOP объявление →","Tekin e'lon joylash →":"Разместить бесплатное объявление →",
    "VIP narxi":"Цена VIP","TOP narxi":"Цена TOP","UP narxi":"Цена UP","Joriy VIP narxi:":"Текущая цена VIP:","Joriy TOP narxi:":"Текущая цена TOP:","Joriy UP narxi:":"Текущая цена UP:",
    "7 kun":"7 дней","24 soat":"24 часа","Bir marta":"Один раз","Xizmat":"Услуга","Tanlangan xizmat:":"Выбранная услуга:","To'lov":"Платёж","Summa":"Сумма","Tugash":"Окончание","Sana":"Дата","Status":"Статус","Holat":"Состояние","Amal":"Действие","Amallar":"Действия","Egasi":"Владелец","E'lon egasi":"Владелец объявления",
    "Rasm":"Фото","Rasm (1–10 ta)":"Фото (1–10)","Rasm mavjud emas.":"Фото отсутствует.","10 tagacha rasm tanlang":"Выберите до 10 фотографий","JPG, JPEG, PNG yoki WEBP":"JPG, JPEG, PNG или WEBP",
    "Bosh sahifaga qaytish":"Вернуться на главную","Barchasini ko'rish →":"Смотреть все →","Bekor qilish":"Отмена","Tasdiqlash":"Подтвердить","O'chirish":"Удалить","O‘chirish":"Удалить","Ochish":"Открыть",
    "Admin panelga kirish":"Вход в панель администратора","ADMIN PANEL":"ПАНЕЛЬ АДМИНИСТРАТОРА","Administrator":"Администратор","Dashboard":"Панель управления","Foydalanuvchilar":"Пользователи","Barcha foydalanuvchilarni boshqarish":"Управление пользователями","Barcha e'lonlarni boshqarish":"Управление объявлениями","Barcha e'lonlar":"Все объявления","To'lovlar yo'q.":"Платежей нет.","Tarix yo'q.":"Истории нет.","Tarix hali bo'sh.":"История пока пуста.",
    "FAOL":"АКТИВЕН","BLOKLANGAN":"ЗАБЛОКИРОВАН","Faol":"Активен","Blok":"Блокировка","Blok sababi:":"Причина блокировки:","Bloklangan foydalanuvchilar":"Заблокированные пользователи","Ma'lumot yo'q.":"Нет данных.","Topilmadi.":"Не найдено.","Sahifa topilmadi.":"Страница не найдена.","Serverda xatolik yuz berdi.":"Произошла ошибка сервера.",
    "Balans:":"Баланс:","Joriy balans:":"Текущий баланс:","Hozirgi balans:":"Текущий баланс:","To'lovdan keyingi balans:":"Баланс после платежа:","Balans o'zgarishlari tarixi":"История изменений баланса",
    "© 2026 Uy77":"© 2026 Uy77",
    "Tekin e'lonlar":"Бесплатные объявления","Hozircha VIP e'lonlar mavjud emas.":"Пока нет VIP объявлений.","Hozircha TOP e'lonlar mavjud emas.":"Пока нет TOP объявлений.","Hozircha tekin e'lonlar mavjud emas.":"Пока нет бесплатных объявлений.","Ko'proq ko'rinish uchun ajratilgan e'lonlar":"Объявления с повышенной видимостью","Yuqoriga ko'tarilgan e'lonlar":"Объявления, поднятые вверх","Barchasi":"Все","Yangi":"Новые","Ishlatilgan":"Б/у","Barcha markalar":"Все марки","Barcha turlar":"Все типы","Ro'yxat":"Список","Kartochkalar":"Карточки","Topildi:":"Найдено:","Xavfsiz":"Безопасно","Platforma":"Платформа","Ko'chmas mulk":"Недвижимость","Avto":"Авто","O'zingizga mos avtomobilni toping":"Найдите подходящий автомобиль","Chevrolet, Toyota, BMW, Mercedes va boshqa avtomobillarni Uy77 orqali oson toping.":"Легко находите Chevrolet, Toyota, BMW, Mercedes и другие автомобили на Uy77.","Kvartira, hovli, yer, ofis va boshqa ko'chmas mulklarni Uy77 orqali oson toping.":"Легко находите квартиры, дома, участки, офисы и другую недвижимость на Uy77.","Marka, model yoki shahar...":"Марка, модель или город...","Masalan: Chilonzor 3 xona, yangi uy...":"Например: Чиланзар 3 комнаты, новый дом...","Qidirish":"Найти","Orqaga":"Назад","← Orqaga":"← Назад","Tavsif":"Описание","Marka":"Марка","Model":"Модель","Yili":"Год","Kuzov":"Кузов","Yurgan masofa":"Пробег","Yoqilg'i":"Топливо","Uzatma":"Коробка","Dvigatel":"Двигатель","Rang":"Цвет","Holati":"Состояние","E'lon turi":"Тип объявления","Joylashuv":"Расположение","Xonalar":"Комнаты","Maydon":"Площадь","Ipoteka":"Ипотека","Mumkin":"Возможна","Ko'rsatilmagan":"Не указано","Xaritada ko'rish":"Показать на карте","＋ E'lon joylash":"＋ Подать объявление","Bosh sahifa":"Главная","Qidiruv":"Поиск","Qo'shish":"Добавить","Menyu":"Меню","Uy — sizning orzuyingiz!":"Дом — ваша мечта!","Viloyat":"Область","Tuman / shahar":"Район / город","Viloyatni tanlang":"Выберите область","Avval viloyatni tanlang":"Сначала выберите область","Tumanni tanlang":"Выберите район","Barcha viloyatlar":"Все области","Barcha tumanlar":"Все районы","Tozalash":"Сбросить","Valyuta":"Валюта","🧪 Sinov to'lovi (pul yechilmaydi)":"🧪 Тестовая оплата (деньги не списываются)","To'lovni tasdiqlash":"Подтверждение оплаты","To'lov usulini tanlang":"Выберите способ оплаты","Payme orqali to'lash":"Оплатить через Payme","💳 Karta orqali to'lash":"💳 Оплатить картой","To'lov tekshirilmoqda...":"Платёж проверяется...","Profilga o'tish":"Перейти в профиль","Kodni kiriting":"Введите код","Kodni qayta yuborish":"Отправить код ещё раз","Raqamni o'zgartirish":"Изменить номер","Balansni to'ldirish":"Пополнить баланс","➕ Balansni to'ldirish":"➕ Пополнить баланс","Pulni shu kartaga o'tkazing":"Переведите деньги на эту карту","📋 Karta raqamini nusxalash":"📋 Скопировать номер карты","Qanday to'lanadi?":"Как оплатить?","O'tkazgan summa (so'm)":"Переведённая сумма (сум)","Chek rasmi (skrinshot)":"Фото чека (скриншот)","Yuborish":"Отправить","So'rovlarim":"Мои заявки","Hozircha so'rovlar yo'q.":"Заявок пока нет.","Kutilmoqda":"Ожидает","Tasdiqlandi":"Подтверждено","Rad etildi":"Отклонено","Click orqali to'lash":"Оплатить через Click","To'lov darrov balansga tushadi":"Платёж сразу зачисляется на баланс","yoki kartaga o'tkazib, chek yuboring":"или переведите на карту и отправьте чек"
  },
  en: {
    "Qidirish...":"Search...","E'lonlar":"Listings","Xarita":"Map","E'lon joylash":"Post an ad","Kirish":"Login","Ro'yxatdan o'tish":"Register",
    "O'zingizga mos uyni toping":"Find the right property for you","O'zingizga mos uyni toping.":"Find the right property for you.","Ko'chmas mulk platformasi":"Real estate platform",
    "E'lon":"Listing","E'lonlar yo'q.":"No listings.","E'lon topilmadi.":"Listing not found.","Batafsil →":"View details →","Batafsil":"Details",
    "Profil":"Profile","Mening e’lonlarim":"My listings","Balans":"Balance","Balansni o'zgartirish":"Change balance","To'lovlar":"Payments","To‘lovlar tarixi":"Payment history","Xizmatlar":"Services",
    "VIP / TOP xizmatlar":"VIP / TOP services","Sevimlilar":"Favorites","Xabarlar":"Messages","Sozlamalar":"Settings","Chiqish":"Log out",
    "Telefon":"Phone","Telefon raqam":"Phone number","Telefoningizga yuborilgan 6 xonali kodni kiriting.":"Enter the 6-digit code sent to your phone.","SMS kod olish":"Get SMS code","SMS kodi":"SMS code","SMS tasdiqlash":"SMS verification",
    "Parol":"Password","Parolni qayta kiriting":"Repeat password","Ism":"Name","Ism:":"Name:","Telefon:":"Phone:","Manzil":"Address","Shahar":"City","Tuman":"District","Mulk turi":"Property type","Xona":"Rooms","Maydon, m²":"Area, m²","Narx":"Price","Narxi":"Price","Narxi:":"Price:","Tavsif":"Description",
    "Kvartira":"Apartment","Hovli":"House","Yer":"Land","Ofis":"Office","Do'kon":"Shop","Sotuv":"Sale","Ijara":"Rent","Kunlik":"Daily",
    "Oddiy":"Standard","TEKIN":"FREE","TOP":"TOP","VIP":"VIP","UP":"UP","Tepaga":"Boost","Ko'tarilgan":"Boosted",
    "VIP e'lonlar":"VIP listings","TOP e'lonlar":"TOP listings","Tepaga ko'tarilgan e'lonlar":"Boosted listings","VIP e'lon joylash →":"Post VIP listing →","TOP e'lon joylash →":"Post TOP listing →","Tekin e'lon joylash →":"Post free listing →",
    "VIP narxi":"VIP price","TOP narxi":"TOP price","UP narxi":"UP price","Joriy VIP narxi:":"Current VIP price:","Joriy TOP narxi:":"Current TOP price:","Joriy UP narxi:":"Current UP price:",
    "7 kun":"7 days","24 soat":"24 hours","Bir marta":"One time","Xizmat":"Service","Tanlangan xizmat:":"Selected service:","To'lov":"Payment","Summa":"Amount","Tugash":"Ends","Sana":"Date","Status":"Status","Holat":"Status","Amal":"Action","Amallar":"Actions","Egasi":"Owner","E'lon egasi":"Listing owner",
    "Rasm":"Photo","Rasm (1–10 ta)":"Photos (1–10)","Rasm mavjud emas.":"No photo available.","10 tagacha rasm tanlang":"Choose up to 10 photos","JPG, JPEG, PNG yoki WEBP":"JPG, JPEG, PNG or WEBP",
    "Bosh sahifaga qaytish":"Back to home","Barchasini ko'rish →":"View all →","Bekor qilish":"Cancel","Tasdiqlash":"Confirm","O'chirish":"Delete","O‘chirish":"Delete","Ochish":"Open",
    "Admin panelga kirish":"Admin panel login","ADMIN PANEL":"ADMIN PANEL","Administrator":"Administrator","Dashboard":"Dashboard","Foydalanuvchilar":"Users","Barcha foydalanuvchilarni boshqarish":"Manage users","Barcha e'lonlarni boshqarish":"Manage listings","Barcha e'lonlar":"All listings","To'lovlar yo'q.":"No payments.","Tarix yo'q.":"No history.","Tarix hali bo'sh.":"History is empty.",
    "FAOL":"ACTIVE","BLOKLANGAN":"BLOCKED","Faol":"Active","Blok":"Block","Blok sababi:":"Block reason:","Bloklangan foydalanuvchilar":"Blocked users","Ma'lumot yo'q.":"No data.","Topilmadi.":"Not found.","Sahifa topilmadi.":"Page not found.","Serverda xatolik yuz berdi.":"Server error.",
    "Balans:":"Balance:","Joriy balans:":"Current balance:","Hozirgi balans:":"Current balance:","To'lovdan keyingi balans:":"Balance after payment:","Balans o'zgarishlari tarixi":"Balance change history",
    "© 2026 Uy77":"© 2026 Uy77",
    "Tekin e'lonlar":"Free listings","Hozircha VIP e'lonlar mavjud emas.":"No VIP listings yet.","Hozircha TOP e'lonlar mavjud emas.":"No TOP listings yet.","Hozircha tekin e'lonlar mavjud emas.":"No free listings yet.","Ko'proq ko'rinish uchun ajratilgan e'lonlar":"Listings with extra visibility","Yuqoriga ko'tarilgan e'lonlar":"Boosted listings","Barchasi":"All","Yangi":"New","Ishlatilgan":"Used","Barcha markalar":"All brands","Barcha turlar":"All types","Ro'yxat":"List","Kartochkalar":"Cards","Topildi:":"Found:","Xavfsiz":"Secure","Platforma":"Platform","Ko'chmas mulk":"Real estate","Avto":"Cars","O'zingizga mos avtomobilni toping":"Find the car that suits you","Chevrolet, Toyota, BMW, Mercedes va boshqa avtomobillarni Uy77 orqali oson toping.":"Easily find Chevrolet, Toyota, BMW, Mercedes and other cars on Uy77.","Kvartira, hovli, yer, ofis va boshqa ko'chmas mulklarni Uy77 orqali oson toping.":"Easily find apartments, houses, land, offices and other property on Uy77.","Marka, model yoki shahar...":"Brand, model or city...","Masalan: Chilonzor 3 xona, yangi uy...":"E.g.: Chilanzar 3 rooms, new house...","Qidirish":"Search","Orqaga":"Back","← Orqaga":"← Back","Tavsif":"Description","Marka":"Brand","Model":"Model","Yili":"Year","Kuzov":"Body","Yurgan masofa":"Mileage","Yoqilg'i":"Fuel","Uzatma":"Transmission","Dvigatel":"Engine","Rang":"Color","Holati":"Condition","E'lon turi":"Listing type","Joylashuv":"Location","Xonalar":"Rooms","Maydon":"Area","Ipoteka":"Mortgage","Mumkin":"Available","Ko'rsatilmagan":"Not specified","Xaritada ko'rish":"View on map","＋ E'lon joylash":"＋ Post an ad","Bosh sahifa":"Home","Qidiruv":"Search","Qo'shish":"Add","Menyu":"Menu","Uy — sizning orzuyingiz!":"Home — your dream!","Viloyat":"Region","Tuman / shahar":"District / city","Viloyatni tanlang":"Select region","Avval viloyatni tanlang":"Select region first","Tumanni tanlang":"Select district","Barcha viloyatlar":"All regions","Barcha tumanlar":"All districts","Tozalash":"Reset","Valyuta":"Currency","🧪 Sinov to'lovi (pul yechilmaydi)":"🧪 Test payment (no money is charged)","To'lovni tasdiqlash":"Confirm payment","To'lov usulini tanlang":"Choose a payment method","Payme orqali to'lash":"Pay with Payme","💳 Karta orqali to'lash":"💳 Pay by card","To'lov tekshirilmoqda...":"Checking payment...","Profilga o'tish":"Go to profile","Kodni kiriting":"Enter the code","Kodni qayta yuborish":"Resend code","Raqamni o'zgartirish":"Change number","Balansni to'ldirish":"Top up balance","➕ Balansni to'ldirish":"➕ Top up balance","Pulni shu kartaga o'tkazing":"Transfer the money to this card","📋 Karta raqamini nusxalash":"📋 Copy card number","Qanday to'lanadi?":"How to pay?","O'tkazgan summa (so'm)":"Amount sent (UZS)","Chek rasmi (skrinshot)":"Receipt photo (screenshot)","Yuborish":"Submit","So'rovlarim":"My requests","Hozircha so'rovlar yo'q.":"No requests yet.","Kutilmoqda":"Pending","Tasdiqlandi":"Approved","Rad etildi":"Rejected","Click orqali to'lash":"Pay with Click","To'lov darrov balansga tushadi":"Payment is credited instantly","yoki kartaga o'tkazib, chek yuboring":"or transfer to the card and send the receipt"
  }
};
function changeLanguage(lang){
  fetch('/set-language/'+encodeURIComponent(lang),{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest'}})
    .then(()=>applyKoshonaLanguage(lang))
    .catch(()=>applyKoshonaLanguage(lang));
}
function applyKoshonaLanguage(lang){
  const dict=KOSHONA_I18N[lang]||{};
  document.documentElement.lang=lang;
  document.querySelectorAll('input[placeholder],textarea[placeholder]').forEach(el=>{
    if(dict[el.getAttribute('placeholder')]) el.setAttribute('placeholder',dict[el.getAttribute('placeholder')]);
  });
  document.querySelectorAll('[title]').forEach(el=>{
    const t=el.getAttribute('title'); if(dict[t]) el.setAttribute('title',dict[t]);
  });
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  const nodes=[]; while(walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(n=>{
    const raw=n.nodeValue, key=raw.trim();
    if(dict[key]) n.nodeValue=raw.replace(key,dict[key]);
  });
  const sel=document.getElementById('languageSelect'); if(sel) sel.value=lang;
}
document.addEventListener('DOMContentLoaded',()=>applyKoshonaLanguage('{{ lang }}'));
</script>

</body>

</html>
"""



# =========================================================
# MOBIL MENYU SOZLAMALARI (admin boshqaradi) + KARTA YORDAMCHILARI
# =========================================================

MOBILE_MENU_DEFAULT = {
    "enabled": True,
    "items": [
        {"key": "home", "icon": "🏠", "uz": "Bosh sahifa", "ru": "Главная", "en": "Home", "url": "/", "enabled": True, "center": False},
        {"key": "search", "icon": "🔍", "uz": "Qidiruv", "ru": "Поиск", "en": "Search", "url": "/listings", "enabled": True, "center": False},
        {"key": "add", "icon": "＋", "uz": "Qo'shish", "ru": "Добавить", "en": "Add", "url": "/post-ad", "enabled": True, "center": True},
        {"key": "auto", "icon": "🚗", "uz": "Avto", "ru": "Авто", "en": "Cars", "url": "/?section=avto", "enabled": True, "center": False},
        {"key": "profile", "icon": "👤", "uz": "Profil", "ru": "Профиль", "en": "Profile", "url": "/profile", "enabled": True, "center": False},
    ],
}


def get_setting_text(key, default=""):
    c = db()
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return row["value"] if row else default


def set_setting_text(key, value, conn=None):
    own = conn is None
    c = conn or db()
    c.execute(
        """
        INSERT INTO settings(key, value, updated_at) VALUES(?,?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """,
        (key, value, datetime.now().isoformat())
    )
    if own:
        c.commit()
        c.close()


def get_mobile_menu():
    raw = get_setting_text("mobile_menu", "")
    try:
        data = json.loads(raw) if raw else None
    except Exception:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        data = json.loads(json.dumps(MOBILE_MENU_DEFAULT))
    return data


def safe_menu_url(url):
    url = (url or "").strip()
    if url.startswith("/") and not url.startswith("//"):
        return url
    if url.startswith("https://") or url.startswith("http://"):
        return url
    return "/"


def mobile_nav_html(lang="uz"):
    menu = get_mobile_menu()
    if not menu.get("enabled", True):
        return ""
    items = [i for i in menu["items"] if i.get("enabled")][:6]
    if not items:
        return ""
    path = request.path
    full = request.full_path.rstrip("?")
    out = ""
    for i in items:
        url = safe_menu_url(i.get("url"))
        label = i.get(lang) or i.get("uz") or ""
        on = "on" if (url == full or (url == "/" and full == "/")) else ""
        cls = "kc-ti add" if i.get("center") else f"kc-ti {on}"
        out += (
            f'<a class="{cls}" href="{esc(url)}">'
            f'<i>{esc(i.get("icon") or "•")}</i><span>{esc(label)}</span></a>'
        )
    return f'<nav class="kc-tab" aria-label="Mobil menyu">{out}</nav>'


def kc_price_text(row, is_auto):
    return price_of(row)


def kc_card(row, is_auto):
    if row["image"]:
        media = (
            f'<img src="{url_for("uploaded_file", filename=row["image"])}" '
            f'alt="{esc(row["title"])}" loading="lazy">'
        )
    else:
        media = f'<div class="kc-ph">{"🚗" if is_auto else "🏠"}</div>'

    badge = ""
    if row["vip"]:
        badge = '<span class="kc-b vip">★ VIP</span>'
    elif row["top"]:
        badge = '<span class="kc-b top">↑ TOP</span>'

    place = esc(row["district"] or row["city"])
    if is_auto:
        meta = f"📍 {place}"
        if row["production_year"]:
            meta += f" · {row['production_year']}"
        meta += f" · {int(row['mileage'] or 0):,} km".replace(",", " ")
        tags = [row["body_type"], row["fuel_type"], row["transmission"]]
    else:
        meta = f"📍 {place} · {row['rooms']} xona · {row['area']} m²"
        tags = [row["property_type"], row["deal_type"]]
    tag_html = "".join(f"<span>{esc(t)}</span>" for t in tags if t)

    return f"""
    <a class="kc-card" href="/listing/{row['id']}">
      <div class="kc-img">{media}{badge}</div>
      <div class="kc-body">
        <div class="kc-price">{esc(kc_price_text(row, is_auto))}</div>
        <div class="kc-title">{esc(row['title'])}</div>
        <div class="kc-meta">{meta}</div>
        <div class="kc-tags">{tag_html}</div>
      </div>
    </a>
    """


@app.route("/api/mobile/config")
def api_mobile_config():
    """Mobil ilova (WebView / Flutter / React Native) uchun sozlamalar."""
    lang = (request.args.get("lang") or session.get("lang") or "uz").lower()
    if lang not in {"uz", "ru", "en"}:
        lang = "uz"
    menu = get_mobile_menu()
    items = [
        {
            "key": i.get("key"),
            "icon": i.get("icon"),
            "label": i.get(lang) or i.get("uz"),
            "url": safe_menu_url(i.get("url")),
            "center": bool(i.get("center")),
        }
        for i in menu["items"] if i.get("enabled")
    ]
    cats = [
        {"slug": x["slug"], "name": x["name"], "icon": x["icon"], "kind": x["kind"]}
        for x in get_categories()
    ]
    return jsonify({
        "bottom_menu_enabled": bool(menu.get("enabled", True)),
        "bottom_menu": items,
        "sections": cats,
        "lang": lang,
    })



def geo_form_html(region="", district=""):
    """E'lon joylash formasi uchun: viloyat + tuman (bog'langan ro'yxatlar)."""
    opts = "".join(
        f'<option value="{esc(r)}"{" selected" if r == region else ""}>{esc(r)}</option>'
        for r in UZ_REGIONS
    )
    data = json.dumps(UZ_REGIONS, ensure_ascii=False).replace("</", "<\\/")
    return f"""
    <div><label>Viloyat</label>
      <select name="region" id="geoRegion" required>
        <option value="">Viloyatni tanlang</option>{opts}
      </select>
    </div>
    <div><label>Tuman / shahar</label>
      <select name="district" id="geoDistrict" required>
        <option value="">Avval viloyatni tanlang</option>
      </select>
    </div>
    <script>
    (function(){{
      var G={data}, r=document.getElementById('geoRegion'), d=document.getElementById('geoDistrict');
      var cur={json.dumps(district, ensure_ascii=False)};
      function fill(){{
        var list=G[r.value]||[];
        d.innerHTML=list.length?'<option value="">Tumanni tanlang</option>'+list.map(function(x){{
          return '<option'+(x===cur?' selected':'')+'>'+x+'</option>';}}).join(''):'<option value="">Avval viloyatni tanlang</option>';
        cur='';
      }}
      r.addEventListener('change',fill); fill();
    }})();
    </script>
    """


def geo_filter_html(action, base, region, district):
    """Bosh sahifa / ro'yxat filtri: viloyat va tuman bo'yicha qidirish."""
    hidden = "".join(
        f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">'
        for k, v in base.items() if v not in ("", None)
    )
    ropts = "".join(
        f'<option value="{esc(r)}"{" selected" if r == region else ""}>{esc(r)}</option>'
        for r in UZ_REGIONS
    )
    dlist = UZ_REGIONS.get(region, [])
    dopts = "".join(
        f'<option value="{esc(d)}"{" selected" if d == district else ""}>{esc(d)}</option>'
        for d in dlist
    )
    data = json.dumps(UZ_REGIONS, ensure_ascii=False).replace("</", "<\\/")

    def url(**kw):
        p = {k: v for k, v in base.items() if v not in ("", None)}
        p.update({k: v for k, v in kw.items() if v})
        return esc(action + ("?" + urlencode(p) if p else ""))

    tags = ""
    if region:
        tags += f'<a class="kc-tag" href="{url()}">{esc(region)} ✕</a>'
    if district:
        tags += f'<a class="kc-tag" href="{url(region=region)}">{esc(district)} ✕</a>'
    reset = f'<a class="kc-reset" href="{url()}">Tozalash</a>' if (region or district) else ""

    return f"""
    <form class="kc-loc" id="kcLoc" method="get" action="{esc(action)}">
      {hidden}
      <div><label>Viloyat</label>
        <select name="region" id="kcReg"><option value="">Barcha viloyatlar</option>{ropts}</select></div>
      <div><label>Tuman / shahar</label>
        <select name="district" id="kcDist"{"" if dlist else " disabled"}>
          <option value="">Barcha tumanlar</option>{dopts}</select></div>
      {reset}
    </form>
    <div class="kc-tags">{tags}</div>
    <script>
    (function(){{
      var G={data}, f=document.getElementById('kcLoc'), r=document.getElementById('kcReg'), d=document.getElementById('kcDist');
      r.addEventListener('change',function(){{ d.innerHTML='<option value="">Barcha tumanlar</option>'; d.disabled=true; f.submit(); }});
      d.addEventListener('change',function(){{ f.submit(); }});
    }})();
    </script>
    """



# =========================================================
# UY77 BRENDI: logotip, favicon, ilova belgisi
# =========================================================

UY77_LOGO_LIGHT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="276 128 735 440" role="img" aria-label="Uy77"><defs><linearGradient id="uyl" gradientUnits="userSpaceOnUse" x1="0" y1="300" x2="0" y2="560"><stop offset="0" stop-color="#0B1530"/><stop offset="1" stop-color="#223468"/></linearGradient>\n<linearGradient id="bl" gradientUnits="userSpaceOnUse" x1="285" y1="130" x2="620" y2="395"><stop offset="0" stop-color="#33B6FF"/><stop offset="1" stop-color="#1560F0"/></linearGradient>\n<linearGradient id="ol" gradientUnits="userSpaceOnUse" x1="560" y1="150" x2="880" y2="520"><stop offset="0" stop-color="#FFC81A"/><stop offset="0.55" stop-color="#FFA313"/><stop offset="1" stop-color="#FF761C"/></linearGradient>\n</defs>\n<path d="M617.8 152.8L614.5 149.5L606.0 143.2L598.8 139.5L591.2 137.5L580.2 136.8L569.5 137.2L560.8 139.5L555.5 142.0L550.0 145.5L520.2 168.0L492.8 187.5L479.2 197.8L412.5 245.2L314.5 311.2L291.8 327.8L287.8 331.8L285.0 336.2L283.0 344.8L283.0 389.5L283.5 391.5L284.5 392.2L287.2 392.2L289.0 391.5L377.5 331.5L437.0 293.2L485.2 260.5L494.0 253.8L499.0 250.8L513.8 239.8L532.0 227.2L568.2 200.0L571.5 198.0L577.8 196.0L583.0 196.0L588.0 197.2L592.5 199.8L612.8 214.0L614.5 214.8L617.5 214.5L618.5 213.0L618.2 174.5L617.8 164.0L618.2 154.5Z" fill="url(#bl)" stroke="url(#bl)" stroke-width="0.6" stroke-linejoin="round"/>\n<path d="M999.0 327.8L996.0 326.5L980.0 326.2L860.2 326.5L859.0 326.8L855.8 328.8L854.2 331.0L853.2 334.0L846.5 361.8L846.5 366.5L847.8 368.0L849.2 368.5L924.8 368.5L925.5 368.8L926.5 370.2L918.0 385.2L893.8 425.2L840.2 512.0L839.5 513.8L839.5 518.0L840.5 519.0L843.2 519.5L886.0 519.5L889.8 518.8L891.8 517.2L961.0 404.8L993.2 351.0L997.5 342.8L1000.2 335.8L1000.5 330.8L1000.0 329.0ZM837.8 327.5L834.8 326.5L830.8 326.2L709.2 326.2L704.8 327.8L703.0 329.5L700.8 334.8L692.5 362.0L692.2 365.8L693.5 368.0L695.2 368.5L773.5 368.5L775.2 370.0L759.2 398.0L734.2 439.2L688.2 513.0L687.8 514.2L687.8 517.8L688.5 518.8L692.8 519.5L736.5 519.5L738.8 518.8L741.0 516.8L836.8 360.5L839.0 355.0L840.2 346.0L840.2 332.0L839.2 329.0ZM585.2 288.0L584.2 289.0L583.2 291.5L583.2 316.5L584.2 319.5L585.5 320.8L588.8 322.0L610.2 322.2L613.8 321.8L615.8 320.8L617.0 319.5L618.2 315.8L618.2 292.2L616.8 288.8L614.5 287.2L612.2 286.8L590.0 286.8L586.8 287.2ZM539.0 287.8L537.2 289.5L536.2 292.2L536.2 315.8L537.0 318.5L538.0 320.0L540.5 321.5L544.5 322.2L566.0 322.0L569.5 320.5L571.0 318.2L571.5 316.0L571.5 292.0L570.2 289.0L569.2 288.0L566.8 287.0L541.8 286.8ZM585.2 245.2L584.0 246.8L583.2 249.0L583.2 273.8L584.0 276.0L585.5 277.5L587.5 278.2L613.2 278.2L615.8 277.2L617.2 275.5L618.2 272.2L618.2 250.0L617.5 247.2L616.5 245.8L614.8 244.2L612.2 243.5L589.5 243.5L586.8 244.2ZM539.2 245.2L536.8 248.5L536.2 252.0L536.2 272.2L537.2 275.8L539.0 277.5L542.0 278.5L566.2 278.2L569.0 277.2L570.5 275.8L571.5 273.0L571.5 249.2L570.2 246.2L568.5 244.5L565.8 243.5L544.2 243.2L542.0 243.8ZM618.2 156.5L617.5 159.8L617.5 215.8L618.0 217.2L619.8 219.0L739.8 304.2L752.0 312.5L757.2 313.8L818.8 314.0L822.0 313.2L822.2 309.5L819.5 306.5L766.0 263.0L763.0 260.0L762.2 258.5L762.0 169.5L760.8 165.2L758.5 163.0L755.0 161.8L704.2 161.5L699.8 163.2L697.0 166.2L696.0 169.2L696.2 208.0L695.0 209.8L694.2 209.8L624.0 157.0L622.2 156.0L619.0 156.0Z" fill="url(#ol)" stroke="url(#ol)" stroke-width="0.6" stroke-linejoin="round"/>\n<path d="M674.8 357.2L673.2 356.8L624.2 356.8L620.8 358.2L619.2 360.0L611.2 380.8L590.0 433.5L587.5 439.0L586.2 440.0L584.5 439.8L582.8 437.5L553.0 362.0L551.8 359.5L550.5 358.2L547.2 356.8L518.0 356.5L498.2 356.8L496.2 357.5L495.0 358.8L494.2 361.0L494.5 362.8L499.2 374.0L521.8 423.2L555.2 493.8L556.2 497.0L555.8 500.8L552.2 506.2L547.0 510.8L542.2 513.2L536.5 515.0L531.0 515.8L525.8 515.8L517.0 514.0L513.8 514.0L511.5 515.0L510.0 516.5L497.2 539.8L496.2 542.8L496.2 545.5L497.0 548.0L499.0 551.0L501.8 553.8L504.2 555.5L509.5 558.0L520.2 560.8L526.5 561.5L536.2 561.5L547.0 560.2L554.8 558.5L561.8 556.2L573.8 550.8L583.8 543.8L591.8 536.0L599.8 525.0L606.0 513.5L651.2 418.8L676.0 363.8L676.8 360.5L676.2 358.8ZM482.8 303.2L480.8 303.0L479.0 303.8L437.0 331.2L435.2 333.0L434.2 335.0L433.8 337.0L433.8 434.0L433.0 439.0L430.5 447.2L426.5 454.0L422.8 458.5L419.2 461.8L412.8 466.0L404.2 469.2L399.5 470.2L387.8 470.5L382.5 469.8L375.2 467.5L368.5 463.8L364.0 460.2L358.8 454.0L354.5 445.5L352.5 437.0L352.2 372.0L351.5 370.0L350.5 369.0L347.8 368.8L346.0 369.5L299.8 400.0L298.8 401.5L297.8 405.0L298.0 433.2L298.8 443.2L301.5 457.0L306.0 469.5L308.8 475.0L314.2 483.8L319.0 490.0L326.8 497.8L331.5 501.8L339.8 507.2L348.8 512.0L355.0 514.5L366.0 517.8L381.8 520.0L399.5 520.0L404.5 519.5L422.2 515.8L430.8 512.8L440.2 508.0L449.0 502.2L453.8 498.5L465.2 486.8L472.5 476.0L478.5 463.0L481.5 453.0L483.5 440.5L484.0 429.0L484.0 305.2Z" fill="url(#uyl)" stroke="url(#uyl)" stroke-width="0.6" stroke-linejoin="round"/></svg>'
UY77_LOGO_DARK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="276 128 735 440" role="img" aria-label="Uy77"><defs><linearGradient id="uyd" gradientUnits="userSpaceOnUse" x1="0" y1="300" x2="0" y2="560"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#D3D8E6"/></linearGradient>\n<linearGradient id="bd" gradientUnits="userSpaceOnUse" x1="285" y1="130" x2="620" y2="395"><stop offset="0" stop-color="#33B6FF"/><stop offset="1" stop-color="#1560F0"/></linearGradient>\n<linearGradient id="od" gradientUnits="userSpaceOnUse" x1="560" y1="150" x2="880" y2="520"><stop offset="0" stop-color="#FFC81A"/><stop offset="0.55" stop-color="#FFA313"/><stop offset="1" stop-color="#FF761C"/></linearGradient>\n</defs>\n<path d="M617.8 152.8L614.5 149.5L606.0 143.2L598.8 139.5L591.2 137.5L580.2 136.8L569.5 137.2L560.8 139.5L555.5 142.0L550.0 145.5L520.2 168.0L492.8 187.5L479.2 197.8L412.5 245.2L314.5 311.2L291.8 327.8L287.8 331.8L285.0 336.2L283.0 344.8L283.0 389.5L283.5 391.5L284.5 392.2L287.2 392.2L289.0 391.5L377.5 331.5L437.0 293.2L485.2 260.5L494.0 253.8L499.0 250.8L513.8 239.8L532.0 227.2L568.2 200.0L571.5 198.0L577.8 196.0L583.0 196.0L588.0 197.2L592.5 199.8L612.8 214.0L614.5 214.8L617.5 214.5L618.5 213.0L618.2 174.5L617.8 164.0L618.2 154.5Z" fill="url(#bd)" stroke="url(#bd)" stroke-width="0.6" stroke-linejoin="round"/>\n<path d="M999.0 327.8L996.0 326.5L980.0 326.2L860.2 326.5L859.0 326.8L855.8 328.8L854.2 331.0L853.2 334.0L846.5 361.8L846.5 366.5L847.8 368.0L849.2 368.5L924.8 368.5L925.5 368.8L926.5 370.2L918.0 385.2L893.8 425.2L840.2 512.0L839.5 513.8L839.5 518.0L840.5 519.0L843.2 519.5L886.0 519.5L889.8 518.8L891.8 517.2L961.0 404.8L993.2 351.0L997.5 342.8L1000.2 335.8L1000.5 330.8L1000.0 329.0ZM837.8 327.5L834.8 326.5L830.8 326.2L709.2 326.2L704.8 327.8L703.0 329.5L700.8 334.8L692.5 362.0L692.2 365.8L693.5 368.0L695.2 368.5L773.5 368.5L775.2 370.0L759.2 398.0L734.2 439.2L688.2 513.0L687.8 514.2L687.8 517.8L688.5 518.8L692.8 519.5L736.5 519.5L738.8 518.8L741.0 516.8L836.8 360.5L839.0 355.0L840.2 346.0L840.2 332.0L839.2 329.0ZM585.2 288.0L584.2 289.0L583.2 291.5L583.2 316.5L584.2 319.5L585.5 320.8L588.8 322.0L610.2 322.2L613.8 321.8L615.8 320.8L617.0 319.5L618.2 315.8L618.2 292.2L616.8 288.8L614.5 287.2L612.2 286.8L590.0 286.8L586.8 287.2ZM539.0 287.8L537.2 289.5L536.2 292.2L536.2 315.8L537.0 318.5L538.0 320.0L540.5 321.5L544.5 322.2L566.0 322.0L569.5 320.5L571.0 318.2L571.5 316.0L571.5 292.0L570.2 289.0L569.2 288.0L566.8 287.0L541.8 286.8ZM585.2 245.2L584.0 246.8L583.2 249.0L583.2 273.8L584.0 276.0L585.5 277.5L587.5 278.2L613.2 278.2L615.8 277.2L617.2 275.5L618.2 272.2L618.2 250.0L617.5 247.2L616.5 245.8L614.8 244.2L612.2 243.5L589.5 243.5L586.8 244.2ZM539.2 245.2L536.8 248.5L536.2 252.0L536.2 272.2L537.2 275.8L539.0 277.5L542.0 278.5L566.2 278.2L569.0 277.2L570.5 275.8L571.5 273.0L571.5 249.2L570.2 246.2L568.5 244.5L565.8 243.5L544.2 243.2L542.0 243.8ZM618.2 156.5L617.5 159.8L617.5 215.8L618.0 217.2L619.8 219.0L739.8 304.2L752.0 312.5L757.2 313.8L818.8 314.0L822.0 313.2L822.2 309.5L819.5 306.5L766.0 263.0L763.0 260.0L762.2 258.5L762.0 169.5L760.8 165.2L758.5 163.0L755.0 161.8L704.2 161.5L699.8 163.2L697.0 166.2L696.0 169.2L696.2 208.0L695.0 209.8L694.2 209.8L624.0 157.0L622.2 156.0L619.0 156.0Z" fill="url(#od)" stroke="url(#od)" stroke-width="0.6" stroke-linejoin="round"/>\n<path d="M674.8 357.2L673.2 356.8L624.2 356.8L620.8 358.2L619.2 360.0L611.2 380.8L590.0 433.5L587.5 439.0L586.2 440.0L584.5 439.8L582.8 437.5L553.0 362.0L551.8 359.5L550.5 358.2L547.2 356.8L518.0 356.5L498.2 356.8L496.2 357.5L495.0 358.8L494.2 361.0L494.5 362.8L499.2 374.0L521.8 423.2L555.2 493.8L556.2 497.0L555.8 500.8L552.2 506.2L547.0 510.8L542.2 513.2L536.5 515.0L531.0 515.8L525.8 515.8L517.0 514.0L513.8 514.0L511.5 515.0L510.0 516.5L497.2 539.8L496.2 542.8L496.2 545.5L497.0 548.0L499.0 551.0L501.8 553.8L504.2 555.5L509.5 558.0L520.2 560.8L526.5 561.5L536.2 561.5L547.0 560.2L554.8 558.5L561.8 556.2L573.8 550.8L583.8 543.8L591.8 536.0L599.8 525.0L606.0 513.5L651.2 418.8L676.0 363.8L676.8 360.5L676.2 358.8ZM482.8 303.2L480.8 303.0L479.0 303.8L437.0 331.2L435.2 333.0L434.2 335.0L433.8 337.0L433.8 434.0L433.0 439.0L430.5 447.2L426.5 454.0L422.8 458.5L419.2 461.8L412.8 466.0L404.2 469.2L399.5 470.2L387.8 470.5L382.5 469.8L375.2 467.5L368.5 463.8L364.0 460.2L358.8 454.0L354.5 445.5L352.5 437.0L352.2 372.0L351.5 370.0L350.5 369.0L347.8 368.8L346.0 369.5L299.8 400.0L298.8 401.5L297.8 405.0L298.0 433.2L298.8 443.2L301.5 457.0L306.0 469.5L308.8 475.0L314.2 483.8L319.0 490.0L326.8 497.8L331.5 501.8L339.8 507.2L348.8 512.0L355.0 514.5L366.0 517.8L381.8 520.0L399.5 520.0L404.5 519.5L422.2 515.8L430.8 512.8L440.2 508.0L449.0 502.2L453.8 498.5L465.2 486.8L472.5 476.0L478.5 463.0L481.5 453.0L483.5 440.5L484.0 429.0L484.0 305.2Z" fill="url(#uyd)" stroke="url(#uyd)" stroke-width="0.6" stroke-linejoin="round"/></svg>'
UY77_FAVICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="#0B1530"/><svg x="8" y="23" width="84" height="50" viewBox="276 128 735 440"><defs>\n<linearGradient id="bi" gradientUnits="userSpaceOnUse" x1="285" y1="130" x2="620" y2="395"><stop offset="0" stop-color="#33B6FF"/><stop offset="1" stop-color="#1560F0"/></linearGradient>\n<linearGradient id="oi" gradientUnits="userSpaceOnUse" x1="560" y1="150" x2="880" y2="520"><stop offset="0" stop-color="#FFC81A"/><stop offset="0.55" stop-color="#FFA313"/><stop offset="1" stop-color="#FF761C"/></linearGradient>\n</defs>\n<path d="M617.8 152.8L614.5 149.5L606.0 143.2L598.8 139.5L591.2 137.5L580.2 136.8L569.5 137.2L560.8 139.5L555.5 142.0L550.0 145.5L520.2 168.0L492.8 187.5L479.2 197.8L412.5 245.2L314.5 311.2L291.8 327.8L287.8 331.8L285.0 336.2L283.0 344.8L283.0 389.5L283.5 391.5L284.5 392.2L287.2 392.2L289.0 391.5L377.5 331.5L437.0 293.2L485.2 260.5L494.0 253.8L499.0 250.8L513.8 239.8L532.0 227.2L568.2 200.0L571.5 198.0L577.8 196.0L583.0 196.0L588.0 197.2L592.5 199.8L612.8 214.0L614.5 214.8L617.5 214.5L618.5 213.0L618.2 174.5L617.8 164.0L618.2 154.5Z" fill="url(#bi)" stroke="url(#bi)" stroke-width="0.6" stroke-linejoin="round"/>\n<path d="M999.0 327.8L996.0 326.5L980.0 326.2L860.2 326.5L859.0 326.8L855.8 328.8L854.2 331.0L853.2 334.0L846.5 361.8L846.5 366.5L847.8 368.0L849.2 368.5L924.8 368.5L925.5 368.8L926.5 370.2L918.0 385.2L893.8 425.2L840.2 512.0L839.5 513.8L839.5 518.0L840.5 519.0L843.2 519.5L886.0 519.5L889.8 518.8L891.8 517.2L961.0 404.8L993.2 351.0L997.5 342.8L1000.2 335.8L1000.5 330.8L1000.0 329.0ZM837.8 327.5L834.8 326.5L830.8 326.2L709.2 326.2L704.8 327.8L703.0 329.5L700.8 334.8L692.5 362.0L692.2 365.8L693.5 368.0L695.2 368.5L773.5 368.5L775.2 370.0L759.2 398.0L734.2 439.2L688.2 513.0L687.8 514.2L687.8 517.8L688.5 518.8L692.8 519.5L736.5 519.5L738.8 518.8L741.0 516.8L836.8 360.5L839.0 355.0L840.2 346.0L840.2 332.0L839.2 329.0ZM585.2 288.0L584.2 289.0L583.2 291.5L583.2 316.5L584.2 319.5L585.5 320.8L588.8 322.0L610.2 322.2L613.8 321.8L615.8 320.8L617.0 319.5L618.2 315.8L618.2 292.2L616.8 288.8L614.5 287.2L612.2 286.8L590.0 286.8L586.8 287.2ZM539.0 287.8L537.2 289.5L536.2 292.2L536.2 315.8L537.0 318.5L538.0 320.0L540.5 321.5L544.5 322.2L566.0 322.0L569.5 320.5L571.0 318.2L571.5 316.0L571.5 292.0L570.2 289.0L569.2 288.0L566.8 287.0L541.8 286.8ZM585.2 245.2L584.0 246.8L583.2 249.0L583.2 273.8L584.0 276.0L585.5 277.5L587.5 278.2L613.2 278.2L615.8 277.2L617.2 275.5L618.2 272.2L618.2 250.0L617.5 247.2L616.5 245.8L614.8 244.2L612.2 243.5L589.5 243.5L586.8 244.2ZM539.2 245.2L536.8 248.5L536.2 252.0L536.2 272.2L537.2 275.8L539.0 277.5L542.0 278.5L566.2 278.2L569.0 277.2L570.5 275.8L571.5 273.0L571.5 249.2L570.2 246.2L568.5 244.5L565.8 243.5L544.2 243.2L542.0 243.8ZM618.2 156.5L617.5 159.8L617.5 215.8L618.0 217.2L619.8 219.0L739.8 304.2L752.0 312.5L757.2 313.8L818.8 314.0L822.0 313.2L822.2 309.5L819.5 306.5L766.0 263.0L763.0 260.0L762.2 258.5L762.0 169.5L760.8 165.2L758.5 163.0L755.0 161.8L704.2 161.5L699.8 163.2L697.0 166.2L696.0 169.2L696.2 208.0L695.0 209.8L694.2 209.8L624.0 157.0L622.2 156.0L619.0 156.0Z" fill="url(#oi)" stroke="url(#oi)" stroke-width="0.6" stroke-linejoin="round"/>\n<path d="M674.8 357.2L673.2 356.8L624.2 356.8L620.8 358.2L619.2 360.0L611.2 380.8L590.0 433.5L587.5 439.0L586.2 440.0L584.5 439.8L582.8 437.5L553.0 362.0L551.8 359.5L550.5 358.2L547.2 356.8L518.0 356.5L498.2 356.8L496.2 357.5L495.0 358.8L494.2 361.0L494.5 362.8L499.2 374.0L521.8 423.2L555.2 493.8L556.2 497.0L555.8 500.8L552.2 506.2L547.0 510.8L542.2 513.2L536.5 515.0L531.0 515.8L525.8 515.8L517.0 514.0L513.8 514.0L511.5 515.0L510.0 516.5L497.2 539.8L496.2 542.8L496.2 545.5L497.0 548.0L499.0 551.0L501.8 553.8L504.2 555.5L509.5 558.0L520.2 560.8L526.5 561.5L536.2 561.5L547.0 560.2L554.8 558.5L561.8 556.2L573.8 550.8L583.8 543.8L591.8 536.0L599.8 525.0L606.0 513.5L651.2 418.8L676.0 363.8L676.8 360.5L676.2 358.8ZM482.8 303.2L480.8 303.0L479.0 303.8L437.0 331.2L435.2 333.0L434.2 335.0L433.8 337.0L433.8 434.0L433.0 439.0L430.5 447.2L426.5 454.0L422.8 458.5L419.2 461.8L412.8 466.0L404.2 469.2L399.5 470.2L387.8 470.5L382.5 469.8L375.2 467.5L368.5 463.8L364.0 460.2L358.8 454.0L354.5 445.5L352.5 437.0L352.2 372.0L351.5 370.0L350.5 369.0L347.8 368.8L346.0 369.5L299.8 400.0L298.8 401.5L297.8 405.0L298.0 433.2L298.8 443.2L301.5 457.0L306.0 469.5L308.8 475.0L314.2 483.8L319.0 490.0L326.8 497.8L331.5 501.8L339.8 507.2L348.8 512.0L355.0 514.5L366.0 517.8L381.8 520.0L399.5 520.0L404.5 519.5L422.2 515.8L430.8 512.8L440.2 508.0L449.0 502.2L453.8 498.5L465.2 486.8L472.5 476.0L478.5 463.0L481.5 453.0L483.5 440.5L484.0 429.0L484.0 305.2Z" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="0.6" stroke-linejoin="round"/></svg></svg>'
UY77_FAVICON_PNG = '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'
UY77_APPLE_ICON_PNG = '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'


def _asset(data, mimetype):
    resp = app.response_class(data, mimetype=mimetype)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@app.route("/uy77-logo.svg")
def uy77_logo_light():
    return _asset(UY77_LOGO_LIGHT, "image/svg+xml")


@app.route("/uy77-logo-dark.svg")
def uy77_logo_dark():
    return _asset(UY77_LOGO_DARK, "image/svg+xml")


@app.route("/favicon.svg")
def uy77_favicon_svg():
    return _asset(UY77_FAVICON_SVG, "image/svg+xml")


@app.route("/favicon.ico")
@app.route("/favicon.png")
def uy77_favicon_png():
    import base64 as _b64
    return _asset(_b64.b64decode(UY77_FAVICON_PNG), "image/png")


@app.route("/apple-touch-icon.png")
def uy77_apple_icon():
    import base64 as _b64
    return _asset(_b64.b64decode(UY77_APPLE_ICON_PNG), "image/png")


def render_page(content, title="Uy77"):

    return render_template_string(
        BASE_HTML,
        content=content,
        title=title,
        current_user=current_user(),
        session=session,
        lang=session.get("lang", "uz"),
        mobile_nav=mobile_nav_html(session.get("lang", "uz"))
    )


@app.route("/set-language/<lang>", methods=["POST", "GET"])
def set_language(lang):
    lang = (lang or "uz").lower()
    if lang not in {"uz", "ru", "en"}:
        lang = "uz"
    session["lang"] = lang
    if request.method == "POST" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "lang": lang})
    return redirect(request.referrer or "/")


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    cleanup_expired()

    section = request.args.get("section", "kochmas-mulk").strip().lower()
    category = get_category_by_slug(section)

    if not category or not category["is_active"]:
        category = get_category_by_slug("kochmas-mulk")

    if not category:
        return render_page("<h2>Bo'lim topilmadi.</h2>"), 404

    section = category["slug"]
    is_auto = category["kind"] == "auto"

    q = request.args.get("q", "").strip()
    property_type = request.args.get("property_type", "").strip()
    brand = request.args.get("brand", "").strip()
    cond = request.args.get("cond", "").strip()
    region = request.args.get("region", "").strip()
    district = request.args.get("district", "").strip()
    if region not in UZ_REGIONS:
        region = ""
    if district not in UZ_REGIONS.get(region, []):
        district = ""
    deal_type = request.args.get("deal_type", "Sotuv").strip()

    if deal_type not in {"Sotuv", "Ijara", "Kunlik"}:
        deal_type = "Sotuv"

    if cond not in {"new", "used"}:
        cond = ""

    # ---------------------------------------------------------
    # SQL: umumiy filtr
    # ---------------------------------------------------------

    where = """
        WHERE listings.hidden=0
        AND users.blocked=0
        AND listings.category_id=?
    """
    params = [category["id"]]

    if region:
        where_geo = " AND listings.city=?"
        params.append(region)
        if district:
            where_geo += " AND listings.district=?"
            params.append(district)
    else:
        where_geo = ""

    where += where_geo

    if q:
        where += """
        AND (
            listings.title LIKE ?
            OR listings.description LIKE ?
            OR listings.brand LIKE ?
            OR listings.model LIKE ?
            OR listings.city LIKE ?
            OR listings.district LIKE ?
        )
        """
        v = f"%{q}%"
        params += [v, v, v, v, v, v]

    if is_auto:
        if brand:
            where += " AND listings.brand=?"
            params.append(brand)
        if cond == "new":
            where += " AND listings.condition='Yangi'"
        elif cond == "used":
            where += " AND COALESCE(listings.condition,'')!='Yangi'"
    else:
        where += " AND listings.deal_type=?"
        params.append(deal_type)
        if property_type:
            where += " AND listings.property_type=?"
            params.append(property_type)

    order = """
        ORDER BY
        CASE WHEN listings.bumped_at IS NULL THEN 0 ELSE 1 END DESC,
        listings.bumped_at DESC,
        listings.id DESC
    """

    def fetch(extra, limit):
        return c.execute(
            f"""
            SELECT listings.*, users.name owner
            FROM listings
            JOIN users ON users.id=listings.user_id
            {where}
            {extra}
            {order}
            LIMIT {int(limit)}
            """,
            params
        ).fetchall()

    c = db()

    vip_rows = fetch("AND listings.vip=1", 10)
    top_rows = fetch("AND listings.top=1 AND listings.vip=0", 10)
    free_rows = fetch("AND listings.vip=0 AND listings.top=0", 12)

    found = c.execute(
        f"""
        SELECT COUNT(*)
        FROM listings
        JOIN users ON users.id=listings.user_id
        {where}
        """,
        params
    ).fetchone()[0]

    total_listings = c.execute(
        """
        SELECT COUNT(*)
        FROM listings
        WHERE hidden=0 AND category_id=?
        """,
        (category["id"],)
    ).fetchone()[0]

    total_users = c.execute(
        "SELECT COUNT(*) FROM users WHERE blocked=0"
    ).fetchone()[0]

    c.close()

    # ---------------------------------------------------------
    # Havolalar
    # ---------------------------------------------------------

    def link(**kw):
        p = {"section": section}
        if q:
            p["q"] = q
        if region:
            p["region"] = region
        if district:
            p["district"] = district
        if is_auto:
            if brand:
                p["brand"] = brand
            if cond:
                p["cond"] = cond
        else:
            p["deal_type"] = deal_type
            if property_type:
                p["property_type"] = property_type
        p.update(kw)
        p = {k: v for k, v in p.items() if v not in ("", None)}
        return esc("/?" + urlencode(p))

    def all_link():
        p = {"section": section}
        if q:
            p["q"] = q
        if region:
            p["region"] = region
        if district:
            p["district"] = district
        if not is_auto:
            p["deal_type"] = deal_type
            if property_type:
                p["property_type"] = property_type
        return esc("/listings?" + urlencode(p))

    # ---------------------------------------------------------
    # Karta
    # ---------------------------------------------------------

    def card(row):
        return kc_card(row, is_auto)

    def block(title, sub, rows, empty, more=True, wrap="kc-strip"):
        cards = "".join(card(r) for r in rows) or (
            f'<div class="kc-empty">{empty}</div>'
        )
        more_html = (
            f'<a class="kc-more" href="{all_link()}">Barchasini ko\'rish →</a>'
            if more else ""
        )
        return f"""
        <section class="kc-sec">
          <div class="kc-head">
            <div><h2>{title}</h2><p>{sub}</p></div>
            {more_html}
          </div>
          <div class="{wrap}">{cards}</div>
        </section>
        """

    # ---------------------------------------------------------
    # Filtrlar
    # ---------------------------------------------------------

    section_nav = "".join(
        f'<a class="kc-pill {"on" if cat["slug"] == section else ""}" '
        f'href="/?section={esc(cat["slug"])}">'
        f'<i>{esc(cat["icon"])}</i> {esc(cat["name"])}</a>'
        for cat in get_categories()
    )

    if is_auto:
        row1 = [("Barchasi", "", ""), ("Yangi", "new", ""), ("Ishlatilgan", "used", "")]
        chips1 = "".join(
            f'<a class="kc-chip {"on" if cond == v else ""}" '
            f'href="{link(cond=v)}">{t}</a>'
            for t, v, _ in row1
        )
        brands = ["Chevrolet", "Toyota", "BMW", "Mercedes-Benz", "Kia", "Hyundai"]
        chips2 = (
            f'<a class="kc-chip {"y" if not brand else ""}" '
            f'href="{link(brand="")}">Barcha markalar</a>'
            + "".join(
                f'<a class="kc-chip {"y" if brand == b else ""}" '
                f'href="{link(brand=b)}">{esc(b)}</a>'
                for b in brands
            )
        )
        hero_title = "O'zingizga mos avtomobilni toping"
        hero_text = (
            "Chevrolet, Toyota, BMW, Mercedes va boshqa "
            "avtomobillarni Uy77 orqali oson toping."
        )
        placeholder = "Marka, model yoki shahar..."
        hidden = (
            f'<input type="hidden" name="brand" value="{esc(brand)}">'
            f'<input type="hidden" name="cond" value="{esc(cond)}">'
        )
    else:
        chips1 = "".join(
            f'<a class="kc-chip {"on" if deal_type == t else ""}" '
            f'href="{link(deal_type=t)}">{t}</a>'
            for t in ["Sotuv", "Ijara", "Kunlik"]
        )
        types = ["Kvartira", "Hovli", "Yer", "Ofis", "Do'kon"]
        chips2 = (
            f'<a class="kc-chip {"y" if not property_type else ""}" '
            f'href="{link(property_type="")}">Barcha turlar</a>'
            + "".join(
                f'<a class="kc-chip {"y" if property_type == t else ""}" '
                f'href="{link(property_type=t)}"><i>🏠</i> {esc(t)}</a>'
                for t in types
            )
        )
        hero_title = "O'zingizga mos uyni toping"
        hero_text = (
            "Kvartira, hovli, yer, ofis va boshqa ko'chmas "
            "mulklarni Uy77 orqali oson toping."
        )
        placeholder = "Masalan: Chilonzor 3 xona, yangi uy..."
        hidden = (
            f'<input type="hidden" name="deal_type" value="{esc(deal_type)}">'
            f'<input type="hidden" name="property_type" value="{esc(property_type)}">'
        )

    hidden += (
        f'<input type="hidden" name="region" value="{esc(region)}">'
        f'<input type="hidden" name="district" value="{esc(district)}">'
    )
    filtered = bool(q or brand or cond or property_type or region or district)

    loc_base = {"section": section, "q": q}
    if is_auto:
        loc_base.update({"brand": brand, "cond": cond})
    else:
        loc_base.update({"deal_type": deal_type, "property_type": property_type})
    loc_block = geo_filter_html("/", loc_base, region, district)

    content = f"""
    <div class="kc-nav">{section_nav}</div>

    <section class="kc-hero">
      <h1>{hero_title}</h1>
      <p>{hero_text}</p>
      <form class="kc-search" method="get" action="/">
        <input type="hidden" name="section" value="{esc(section)}">
        {hidden}
        <input name="q" value="{esc(q)}" placeholder="{placeholder}">
        <button><i>🔎</i> Qidirish</button>
      </form>
    </section>

    <div class="kc-bar">
      <div class="kc-chips">{chips1}</div>
      <div class="kc-views">
        <a class="on" href="/?section={esc(section)}"><i>☰</i> Ro'yxat</a>
        <a href="/listings?section={esc(section)}"><i>▦</i> Kartochkalar</a>
      </div>
    </div>

    <div class="kc-chips">{chips2}</div>

    {loc_block}

    {block("VIP e'lonlar", "Ko'proq ko'rinish uchun ajratilgan e'lonlar",
           vip_rows, "Hozircha VIP e'lonlar mavjud emas.")}

    {block("TOP e'lonlar", "Yuqoriga ko'tarilgan e'lonlar",
           top_rows, "Hozircha TOP e'lonlar mavjud emas.")}

    {block("Tekin e'lonlar",
           f"<span>Topildi:</span> {found if filtered else total_listings}",
           free_rows, "Hozircha tekin e'lonlar mavjud emas.")}

    <div class="kc-stats">
      <div><b>{total_listings}</b><span>E'lonlar</span></div>
      <div><b>{total_users}</b><span>Foydalanuvchilar</span></div>
      <div><b>100%</b><span>Xavfsiz</span></div>
      <div><b>24/7</b><span>Platforma</span></div>
    </div>
    """

    return render_page(content, "Uy77")


# =========================================================
# UPLOADS
# =========================================================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOADS,
        filename
    )


# =========================================================
# KIRISH / RO'YXATDAN O'TISH  (faqat telefon raqam + SMS kod, parolsiz)
# =========================================================

AUTH_RESEND_SECONDS = 60      # bir raqamga ketma-ket SMS oralig'i
AUTH_MAX_SMS_PER_HOUR = 5     # bir raqamga soatiga
AUTH_MAX_SMS_PER_IP_HOUR = 20 # bir IP dan soatiga
AUTH_MAX_WRONG = 5            # 10 daqiqada noto'g'ri kod urinishlari


def client_ip():
    return (request.remote_addr or "")[:64]


def auth_event(phone, event, is_new=0, conn=None):
    own = conn is None
    c = conn or db()
    c.execute(
        "INSERT INTO auth_events(phone, event, is_new, ip) VALUES(?,?,?,?)",
        (phone, event, 1 if is_new else 0, client_ip())
    )
    if own:
        c.commit()
        c.close()


def mask_phone(p):
    return f"+998 {p[3:5]} *** ** {p[-2:]}" if len(p) == 12 else p


def sms_cooldown(phone):
    """Keyingi SMS ga necha soniya qolganini qaytaradi (0 = yuborish mumkin)."""
    c = db()
    row = c.execute(
        "SELECT CAST((julianday('now') - julianday(MAX(created_at))) * 86400 AS INTEGER) AS ago "
        "FROM auth_events WHERE phone=? AND event='sms_sent'", (phone,)
    ).fetchone()
    c.close()
    if row is None or row["ago"] is None:
        return 0
    return max(0, AUTH_RESEND_SECONDS - int(row["ago"]))


def send_login_code(phone):
    """Chegaralarni tekshirib, SMS kodni yuboradi. (ok, xabar) qaytaradi."""
    wait = sms_cooldown(phone)
    if wait > 0:
        return False, f"Yangi kod uchun {wait} soniya kuting."

    c = db()
    per_phone = c.execute(
        "SELECT COUNT(*) FROM auth_events WHERE phone=? AND event='sms_sent' AND created_at > datetime('now','-1 hour')",
        (phone,)
    ).fetchone()[0]
    per_ip = c.execute(
        "SELECT COUNT(*) FROM auth_events WHERE ip=? AND event='sms_sent' AND created_at > datetime('now','-1 hour')",
        (client_ip(),)
    ).fetchone()[0]
    exists = c.execute("SELECT id FROM users WHERE phone=?", (phone,)).fetchone()
    c.close()

    if per_phone >= AUTH_MAX_SMS_PER_HOUR or per_ip >= AUTH_MAX_SMS_PER_IP_HOUR:
        auth_event(phone, "rate_limited", 0 if exists else 1)
        return False, "Juda ko'p urinish. Birozdan keyin qayta urinib ko'ring."

    code = generate_otp()
    save_otp(phone, code)

    message = f"{os.environ.get('SMS_BRAND', 'KOSHONA.UZ')} tasdiqlash kodi: {code}. Kod {OTP_EXPIRE_MINUTES} daqiqa amal qiladi."
    # Android Chrome kodni o'zi to'ldirishi uchun (Eskiz shablonida tasdiqlangandan keyin yoqing)
    if os.environ.get("SMS_WEB_OTP") == "1":
        host = (os.environ.get("SITE_URL", "").split("//")[-1].split("/")[0]
                or request.host).split(":")[0]
        message += f"\n\n@{host} #{code}"

    if not send_sms(phone, message):
        c = db()
        c.execute("DELETE FROM otp_codes WHERE phone=?", (phone,))
        c.commit()
        c.close()
        return False, "SMS yuborib bo'lmadi. Birozdan keyin qayta urinib ko'ring."

    auth_event(phone, "sms_sent", 0 if exists else 1)
    return True, ""


@app.route("/register")
def register():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if login_required():
        return redirect("/")

    if request.method == "POST":
        phone = clean_phone(request.form.get("phone", ""))
        if not valid_phone(phone):
            flash("Telefon raqamni to'g'ri kiriting. Masalan: 90 123 45 67")
            return redirect("/login")

        c = db()
        user = c.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        c.close()

        if user and user["blocked"]:
            flash("Sizning akkauntingiz bloklangan.")
            return redirect("/login")
        if user and user["is_admin"]:
            flash("Admin akkaunti uchun admin kirish sahifasidan foydalaning.")
            return redirect("/login")

        ok, msg = send_login_code(phone)
        if not ok:
            # Kod allaqachon yuborilgan bo'lsa, tasdiqlash sahifasiga o'tkazamiz
            if msg.startswith("Yangi kod uchun"):
                session["login_phone"] = phone
                flash(msg)
                return redirect("/verify")
            flash(msg)
            return redirect("/login")

        session["login_phone"] = phone
        return redirect("/verify")

    content = """
    <div class="form-card" style="max-width:420px;margin:30px auto">
      <h2 style="margin:0 0 6px">Kirish</h2>
      <p style="color:var(--muted);margin:0 0 18px">
        Telefon raqamingizni kiriting. Sizga SMS orqali kod yuboriladi.
        Yangi bo'lsangiz, hisob o'zi yaratiladi.
      </p>
      <form method="post">
        <label style="font-weight:700">Telefon raqam</label>
        <div style="display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:14px;padding:4px 12px;margin:6px 0 14px;background:#fff">
          <span style="font-weight:800;color:var(--muted)">+998</span>
          <input name="phone" type="tel" inputmode="numeric" autocomplete="tel-national"
                 placeholder="90 123 45 67" maxlength="17" required autofocus
                 style="flex:1;border:0;outline:0;padding:12px 0;font-size:18px;background:none">
        </div>
        <button class="post-btn" type="submit" style="width:100%">Kirish</button>
      </form>
      <p style="color:var(--muted);font-size:12px;margin:14px 0 0;text-align:center">
        Davom etish orqali siz sayt qoidalariga rozilik bildirasiz.
      </p>
    </div>
    """
    return render_page(content, "Kirish")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    phone = session.get("login_phone")
    if not phone:
        return redirect("/login")

    if request.method == "POST":
        code = re.sub(r"\D", "", request.form.get("code", ""))[:6]

        c = db()
        wrong = c.execute(
            "SELECT COUNT(*) FROM auth_events WHERE phone=? AND event='wrong_code' AND created_at > datetime('now','-10 minutes')",
            (phone,)
        ).fetchone()[0]
        if wrong >= AUTH_MAX_WRONG:
            c.execute("DELETE FROM otp_codes WHERE phone=?", (phone,))
            c.commit()
            c.close()
            flash("Juda ko'p xato urinish. 10 daqiqadan keyin qayta urinib ko'ring.")
            return redirect("/verify")
        c.close()

        if len(code) != 6 or not verify_otp(phone, code):
            auth_event(phone, "wrong_code")
            flash("SMS kodi noto'g'ri yoki muddati o'tgan.")
            return redirect("/verify")

        c = db()
        user = c.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        is_new = 0
        if user:
            if user["blocked"] or user["is_admin"]:
                c.close()
                flash("Bu raqam bilan kirib bo'lmaydi.")
                return redirect("/login")
            if not user["verified"]:
                c.execute("UPDATE users SET verified=1 WHERE id=?", (user["id"],))
            user_id = user["id"]
        else:
            is_new = 1
            # Parol ishlatilmaydi, lekin ustun majburiy: tasodifiy shifrlangan qiymat yoziladi
            cur = c.execute(
                "INSERT INTO users(name, phone, password, verified) VALUES(?,?,?,1)",
                ("Uy77 foydalanuvchisi", phone, generate_password_hash(secrets.token_hex(16)))
            )
            user_id = cur.lastrowid
        auth_event(phone, "verified", is_new, conn=c)
        c.commit()
        c.close()

        session.pop("login_phone", None)
        session["user_id"] = user_id
        flash("Xush kelibsiz!" if is_new else "Tizimga muvaffaqiyatli kirdingiz.")
        return redirect("/profile" if is_new else "/")

    wait = sms_cooldown(phone)
    content = """
    <div class="form-card" style="max-width:420px;margin:30px auto;text-align:center">
      <h2 style="margin:0 0 6px">Kodni kiriting</h2>
      <p style="color:var(--muted);margin:0 0 16px">__MASK__ raqamiga SMS kod yuborildi</p>
      <form method="post" id="vf">
        <input id="code" name="code" type="text" inputmode="numeric" pattern="[0-9]*"
               autocomplete="one-time-code" maxlength="6" placeholder="••••••" required autofocus
               style="width:100%;text-align:center;font-size:32px;letter-spacing:12px;font-weight:800;padding:14px;border:1px solid var(--line);border-radius:14px;margin-bottom:14px;background:#fff">
        <button class="post-btn" type="submit" style="width:100%">Tasdiqlash</button>
      </form>
      <form method="post" action="/verify/resend" style="margin-top:14px">
        <button id="rs" type="submit" disabled
                style="border:0;background:none;color:var(--muted);font-weight:700;cursor:pointer">
          Kodni qayta yuborish
        </button>
      </form>
      <a href="/login" style="font-size:13px;color:var(--muted)">Raqamni o'zgartirish</a>
    </div>
    <script>
    (function(){
      var inp=document.getElementById('code'), f=document.getElementById('vf'), sent=false;
      function go(){ if(!sent && inp.value.replace(/\\D/g,'').length===6){ sent=true; f.submit(); } }
      inp.addEventListener('input', go);
      // Android Chrome: SMS dagi kodni o'zi oladi (SMS oxirida "@sayt #kod" qatori bo'lsa)
      if ('OTPCredential' in window) {
        try {
          navigator.credentials.get({otp:{transport:['sms']}}).then(function(o){
            if(o && o.code){ inp.value=o.code; go(); }
          }).catch(function(){});
        } catch(e) {}
      }
      var left=__WAIT__, b=document.getElementById('rs');
      function tick(){
        if(left>0){ b.disabled=true; b.textContent='Qayta yuborish: '+left+' s'; left--; setTimeout(tick,1000); }
        else { b.disabled=false; b.textContent='Kodni qayta yuborish'; }
      }
      tick();
    })();
    </script>
    """.replace("__MASK__", esc(mask_phone(phone))).replace("__WAIT__", str(wait))
    return render_page(content, "SMS tasdiqlash")


@app.route("/verify/resend", methods=["POST"])
def verify_resend():
    phone = session.get("login_phone")
    if not phone:
        return redirect("/login")
    ok, msg = send_login_code(phone)
    flash("Yangi kod yuborildi." if ok else msg)
    return redirect("/verify")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Tizimdan chiqdingiz."
    )

    return redirect("/")


# =========================================================
# LISTINGS
# =========================================================

@app.route("/listings")
def listings():
    cleanup_expired()
    q = request.args.get("q", "").strip()
    property_type = request.args.get("property_type", "").strip()
    deal_type = request.args.get("deal_type", "").strip()
    brand = request.args.get("brand", "").strip()
    cond = request.args.get("cond", "").strip()
    region = request.args.get("region", "").strip()
    district = request.args.get("district", "").strip()
    if region not in UZ_REGIONS:
        region = ""
    if district not in UZ_REGIONS.get(region, []):
        district = ""
    section = request.args.get("section", "kochmas-mulk").strip().lower()
    category = get_category_by_slug(section)
    if not category or not category["is_active"]:
        category = get_category_by_slug("kochmas-mulk")
        section = "kochmas-mulk"
    if not category:
        return render_page("<h2>Bo'lim topilmadi.</h2>"), 404
    is_auto = category["kind"] == "auto"

    c = db()
    sql = """
        SELECT listings.*, users.name owner, users.phone owner_phone
        FROM listings
        JOIN users ON users.id=listings.user_id
        WHERE listings.hidden=0 AND users.blocked=0 AND listings.category_id=?
    """
    params = [category["id"]]

    if region:
        where_geo = " AND listings.city=?"
        params.append(region)
        if district:
            where_geo += " AND listings.district=?"
            params.append(district)
    else:
        where_geo = ""

    sql += where_geo

    if q:
        sql += " AND (listings.title LIKE ? OR listings.description LIKE ? OR listings.brand LIKE ? OR listings.model LIKE ? OR listings.city LIKE ? OR listings.district LIKE ?)"
        v = f"%{q}%"
        params += [v, v, v, v, v, v]

    if is_auto:
        if brand:
            sql += " AND listings.brand=?"
            params.append(brand)
        if cond == "new":
            sql += " AND listings.condition='Yangi'"
        elif cond == "used":
            sql += " AND COALESCE(listings.condition,'')!='Yangi'"
    else:
        if property_type:
            sql += " AND listings.property_type=?"
            params.append(property_type)
        if deal_type in {"Sotuv", "Ijara", "Kunlik"}:
            sql += " AND listings.deal_type=?"
            params.append(deal_type)

    sql += """ ORDER BY listings.vip DESC, listings.top DESC,
             CASE WHEN listings.bumped_at IS NULL THEN 0 ELSE 1 END DESC,
             listings.bumped_at DESC, listings.id DESC"""
    rows = c.execute(sql, params).fetchall()
    c.close()

    def link(**kw):
        p = {"section": section}
        if q:
            p["q"] = q
        if region:
            p["region"] = region
        if district:
            p["district"] = district
        if is_auto:
            if brand:
                p["brand"] = brand
            if cond:
                p["cond"] = cond
        else:
            if deal_type:
                p["deal_type"] = deal_type
            if property_type:
                p["property_type"] = property_type
        p.update(kw)
        p = {k: v for k, v in p.items() if v not in ("", None)}
        return esc("/listings?" + urlencode(p))

    if is_auto:
        chips1 = "".join(
            f'<a class="kc-chip {"on" if cond == v else ""}" href="{link(cond=v)}">{t}</a>'
            for t, v in [("Barchasi", ""), ("Yangi", "new"), ("Ishlatilgan", "used")]
        )
        brands = ["Chevrolet", "Toyota", "BMW", "Mercedes-Benz", "Kia", "Hyundai"]
        chips2 = (
            f'<a class="kc-chip {"y" if not brand else ""}" href="{link(brand="")}">Barcha markalar</a>'
            + "".join(
                f'<a class="kc-chip {"y" if brand == b else ""}" href="{link(brand=b)}">{esc(b)}</a>'
                for b in brands
            )
        )
        hidden = (
            f'<input type="hidden" name="brand" value="{esc(brand)}">'
            f'<input type="hidden" name="cond" value="{esc(cond)}">'
        )
        placeholder = "Marka, model yoki shahar..."
    else:
        chips1 = (
            f'<a class="kc-chip {"on" if not deal_type else ""}" href="{link(deal_type="")}">Barchasi</a>'
            + "".join(
                f'<a class="kc-chip {"on" if deal_type == t else ""}" href="{link(deal_type=t)}">{t}</a>'
                for t in ["Sotuv", "Ijara", "Kunlik"]
            )
        )
        chips2 = (
            f'<a class="kc-chip {"y" if not property_type else ""}" href="{link(property_type="")}">Barcha turlar</a>'
            + "".join(
                f'<a class="kc-chip {"y" if property_type == t else ""}" href="{link(property_type=t)}"><i>🏠</i> {esc(t)}</a>'
                for t in ["Kvartira", "Hovli", "Yer", "Ofis", "Do'kon"]
            )
        )
        hidden = (
            f'<input type="hidden" name="deal_type" value="{esc(deal_type)}">'
            f'<input type="hidden" name="property_type" value="{esc(property_type)}">'
        )
        placeholder = "Qidirish..."

    hidden += (
        f'<input type="hidden" name="region" value="{esc(region)}">'
        f'<input type="hidden" name="district" value="{esc(district)}">'
    )
    loc_base = {"section": section, "q": q}
    if is_auto:
        loc_base.update({"brand": brand, "cond": cond})
    else:
        loc_base.update({"deal_type": deal_type, "property_type": property_type})
    loc_block = geo_filter_html("/listings", loc_base, region, district)

    cards = "".join(kc_card(r, is_auto) for r in rows) or '<div class="kc-empty">E\'lon topilmadi.</div>'

    content = f"""
    <div class="kc-head" style="margin-top:20px">
      <div><h1 style="margin:0;font-size:26px"><i>{esc(category["icon"])}</i> {esc(category["name"])}</h1>
      <p><span>E'lonlar</span>: {len(rows)}</p></div>
      <a class="kc-more" href="/post-ad?category={esc(category["slug"])}">＋ E'lon joylash</a>
    </div>

    <form class="kc-search" method="get" action="/listings" style="max-width:none;margin:14px 0;box-shadow:none;border:1px solid var(--line)">
      <input type="hidden" name="section" value="{esc(section)}">
      {hidden}
      <input name="q" value="{esc(q)}" placeholder="{placeholder}">
      <button><i>🔎</i> Qidirish</button>
    </form>

    <div class="kc-chips" style="margin-bottom:8px">{chips1}</div>
    <div class="kc-chips">{chips2}</div>

    {loc_block}

    <div class="kc-grid" style="margin-top:16px">{cards}</div>
    """
    return render_page(content, f"{category['name']} — e'lonlar")


@app.route("/avto")
def avto():
    return redirect("/?section=avto")


@app.route("/section/<slug>")
def section_page(slug):
    category=get_category_by_slug(slug)
    if not category or not category["is_active"]:
        return render_page("<h2>Bo'lim topilmadi.</h2>"),404
    return redirect(f"/?section={category['slug']}")


# =========================================================
# SINGLE LISTING
# =========================================================

@app.route(
    "/listing/<int:listing_id>"
)
def listing_detail(listing_id):
    cleanup_expired()
    c = db()
    row = c.execute("""
        SELECT listings.*, users.name owner, users.phone owner_phone,
               categories.name category_name, categories.icon category_icon,
               categories.kind category_kind
        FROM listings
        JOIN users ON users.id=listings.user_id
        LEFT JOIN categories ON categories.id=listings.category_id
        WHERE listings.id=?
    """, (listing_id,)).fetchone()
    c.close()

    if not row:
        return render_page("<h2>E'lon topilmadi.</h2>"), 404

    image_names=[]
    try:
        if row["images"]:
            image_names=json.loads(row["images"])
    except:
        image_names=[]
    if not image_names and row["image"]:
        image_names=[row["image"]]

    is_auto = row["category_kind"] == "auto" or row["listing_kind"] == "auto"
    urls = [url_for("uploaded_file", filename=n) for n in image_names]
    main_img = (
        f'<img id="kd-main" src="{urls[0]}" alt="{esc(row["title"])}">'
        if urls else f'<div class="kc-ph" style="height:100%;font-size:70px">{"🚗" if is_auto else "🏠"}</div>'
    )
    thumbs = "".join(
        f'<img src="{u}" alt="" onclick="document.getElementById(\'kd-main\').src=this.src">'
        for u in urls
    ) if len(urls) > 1 else ""

    badge = ""
    if row["vip"]:
        badge = '<span class="kc-b vip" style="position:static">★ VIP</span>'
    elif row["top"]:
        badge = '<span class="kc-b top" style="position:static">↑ TOP</span>'

    def spec(icon, label, value):
        if value in (None, "", 0):
            return ""
        return f'<div class="kd-spec"><i>{icon}</i><div><small>{label}</small><b>{esc(value)}</b></div></div>'

    if is_auto:
        phone = row["contact_phone"] or row["owner_phone"]
        specs = "".join([
            spec("🚗", "Marka", row["brand"]),
            spec("🚘", "Model", row["model"]),
            spec("📅", "Yili", row["production_year"]),
            spec("🚙", "Kuzov", row["body_type"]),
            spec("🛣", "Yurgan masofa", f"{int(row['mileage'] or 0):,} km".replace(",", " ")),
            spec("⛽", "Yoqilg'i", row["fuel_type"]),
            spec("⚙️", "Uzatma", row["transmission"]),
            spec("🔧", "Dvigatel", row["engine_volume"]),
            spec("🎨", "Rang", row["color"]),
            spec("📋", "Holati", row["condition"]),
        ])
        map_button = ""
        price = kc_price_text(row, True)
    else:
        phone = row["owner_phone"]
        place = row["city"] + (", " + row["district"] if row["district"] else "")
        specs = "".join([
            spec("🏷", "E'lon turi", row["deal_type"]),
            spec("🏠", "Mulk turi", row["property_type"]),
            spec("📍", "Joylashuv", place),
            spec("🛏", "Xonalar", row["rooms"]),
            spec("📐", "Maydon", f"{row['area']} m²"),
            spec("🧭", "Manzil", row["address"]),
            spec("🏦", "Ipoteka", "Mumkin" if row["mortgage"] else "Ko'rsatilmagan"),
        ])
        map_button = f'<a class="kd-btn ghost" href="/map#listing-{row["id"]}"><i>🗺</i> Xaritada ko\'rish</a>'
        price = price_of(row)

    content = f"""
    <div class="kd-wrap">
      <a class="kd-back" href="javascript:history.back()">← Orqaga</a>
      <div class="kd-grid">
        <div class="kd-left">
          <div class="kd-photo">{main_img}</div>
          <div class="kd-thumbs">{thumbs}</div>
          <div class="kd-box kd-desc">
            <h3>Tavsif</h3>
            <p style="white-space:pre-wrap;margin:0">{esc(row["description"])}</p>
          </div>
        </div>
        <aside>
          <div class="kd-box">
            <div>{badge}</div>
            <div class="kc-meta" style="margin-top:8px"><i>{esc(row["category_icon"] or "📂")}</i> {esc(row["category_name"] or "Bo'lim")}</div>
            <h1 class="kd-title">{esc(row["title"])}</h1>
            <div class="kd-price">{esc(price)}</div>
            <a class="kd-btn" href="tel:{esc(phone)}"><i>📞</i> {esc(phone)}</a>
            {map_button}
            <div class="kd-owner"><i>👤</i> {esc(row["owner"])}</div>
          </div>
          <div class="kd-box"><div class="kd-specs">{specs}</div></div>
        </aside>
      </div>
    </div>
    """
    return render_page(content,row["title"])


# =========================================================
# SERVICE
# =========================================================

SERVICE_NAMES = {
    "free": "🆓 Tekin",
    "vip": "👑 VIP",
    "top": "🔥 TOP"
}


@app.route("/post-ad")
def post_ad():
    if not login_required():
        flash("E'lon joylash uchun avval tizimga kiring.")
        return redirect("/login")

    slug = request.args.get("category", "").strip().lower()
    if not slug:
        categories = get_categories()
        cards = ""
        for cat in categories:
            cards += f"""
            <a href="/post-ad?category={esc(cat['slug'])}" style="text-decoration:none">
              <div class="form-card" style="margin:0;max-width:none;height:100%;text-align:center">
                <div style="font-size:58px">{esc(cat['icon'])}</div>
                <h2>{esc(cat['name'])}</h2>
                <p style="color:#777">Faqat shu bo'limga tegishli e'lon joylash</p>
                <span class="post-btn">Bo'limni tanlash →</span>
              </div>
            </a>
            """
        content = f"""
        <div style="max-width:1100px;margin:0 auto">
          <div class="section-head">
            <div><h1>📢 E'lon joylash</h1><p>Avval e'lon bo'limini tanlang.</p></div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px">
            {cards}
          </div>
        </div>
        """
        return render_page(content, "E'lon joylash")

    category = get_category_by_slug(slug)
    if not category or not category["is_active"]:
        flash("Bo'lim topilmadi.")
        return redirect("/post-ad")

    return render_page(
        service_cards(category),
        f"{category['name']} — xizmat tanlash"
    )


# =========================================================
# ADD LISTING
# =========================================================

@app.route(
    "/add",
    methods=["GET", "POST"]
)
def add_listing():
    if not login_required():
        flash("E'lon joylash uchun avval tizimga kiring.")
        return redirect("/login")

    prices = service_prices()
    service = request.args.get("service", "").lower().strip()
    category_slug = request.args.get("category", "").strip().lower()

    if request.method == "POST":
        service = request.form.get("service", service).lower().strip()
        category_slug = request.form.get("category", category_slug).strip().lower()

    category = get_category_by_slug(category_slug)
    if not category or not category["is_active"]:
        flash("Bo'lim topilmadi.")
        return redirect("/post-ad")

    if service not in prices:
        return redirect(f"/post-ad?category={category['slug']}")

    service_price = prices[service]
    is_auto = category["kind"] == "auto"

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "0").replace(" ", "").replace(",", "")
        uploaded_files = request.files.getlist("images")
        uploaded_files = [f for f in uploaded_files if f and f.filename]

        try:
            price = int(price_raw or "0")
        except:
            flash("Narx noto'g'ri kiritildi.")
            return redirect(f"/add?service={service}&category={category['slug']}")

        if price < 0:
            flash("Narx manfiy bo'lishi mumkin emas.")
            return redirect(f"/add?service={service}&category={category['slug']}")

        if not uploaded_files:
            flash("Kamida 1 ta rasm yuklang.")
            return redirect(f"/add?service={service}&category={category['slug']}")

        if len(uploaded_files) > 10:
            flash("Bir e'longa ko'pi bilan 10 ta rasm yuklash mumkin.")
            return redirect(f"/add?service={service}&category={category['slug']}")

        image_names = []
        saved_names = []
        try:
            for file in uploaded_files:
                image_name = save_uploaded_image(file)
                image_names.append(image_name)
                saved_names.append(image_name)
        except Exception:
            for saved_name in saved_names:
                try: os.remove(os.path.join(UPLOADS, saved_name))
                except Exception: pass
            flash("Rasmni saqlashda xatolik. JPG, JPEG, PNG yoki WEBP rasm tanlang.")
            return redirect(f"/add?service={service}&category={category['slug']}")

        if is_auto:
            brand = request.form.get("brand", "").strip()
            model = request.form.get("model", "").strip()
            year_raw = request.form.get("production_year", "").strip()
            body_type = request.form.get("body_type", "").strip()
            mileage_raw = request.form.get("mileage", "0").strip()
            fuel_type = request.form.get("fuel_type", "").strip()
            transmission = request.form.get("transmission", "").strip()
            engine_volume = request.form.get("engine_volume", "").strip()
            color = request.form.get("color", "").strip()
            currency = request.form.get("currency", "USD").strip()
            condition = request.form.get("condition", "").strip()
            contact_phone = clean_phone(request.form.get("contact_phone", "").strip())

            try:
                production_year = int(year_raw) if year_raw else None
            except:
                production_year = None
            try:
                mileage = int(mileage_raw or "0")
            except:
                mileage = 0

            if not brand or not model:
                flash("Avtomobil markasi va modelini tanlang.")
                return redirect(f"/add?service={service}&category={category['slug']}")
            if production_year is not None and not (1886 <= production_year <= datetime.now().year + 1):
                flash("Ishlab chiqarilgan yil noto'g'ri.")
                return redirect(f"/add?service={service}&category={category['slug']}")
            if not valid_phone(contact_phone):
                flash("Telefon raqamni 998XXXXXXXXX formatida kiriting.")
                return redirect(f"/add?service={service}&category={category['slug']}")

            region = request.form.get("region", "").strip()
            district = request.form.get("district", "").strip()
            if not geo_valid(region, district):
                flash("Viloyat va tumanni ro'yxatdan tanlang.")
                return redirect(f"/add?service={service}&category={category['slug']}")
            if currency not in {"USD", "UZS", "EUR"}:
                currency = "USD"
            if not title:
                title = f"{brand} {model}" + (f" {production_year}" if production_year else "")

            draft = {
                "service": service,
                "category_id": category["id"],
                "category_slug": category["slug"],
                "listing_kind": "auto",
                "title": title,
                "description": description,
                "price": price,
                "property_type": "Avto",
                "deal_type": "Sotuv",
                "mortgage": 0,
                "city": region,
                "district": district,
                "address": "",
                "rooms": 0,
                "area": 0,
                "image": image_names[0],
                "images": image_names,
                "latitude": None,
                "longitude": None,
                "brand": brand,
                "model": model,
                "production_year": production_year,
                "body_type": body_type,
                "mileage": mileage,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "engine_volume": engine_volume,
                "color": color,
                "currency": currency,
                "condition": condition,
                "contact_phone": contact_phone
            }
        else:
            deal_type = request.form.get("deal_type", "Sotuv")
            if deal_type not in {"Sotuv", "Ijara", "Kunlik"}:
                deal_type = "Sotuv"

            property_type = request.form.get("property_type", "Kvartira").strip()
            region = request.form.get("region", "").strip()
            district = request.form.get("district", "").strip()
            if not geo_valid(region, district):
                flash("Viloyat va tumanni ro'yxatdan tanlang.")
                return redirect(f"/add?service={service}&category={category['slug']}")
            city = region
            currency_re = request.form.get("currency", "USD").strip().upper()
            if currency_re not in {"USD", "UZS", "EUR"}:
                currency_re = "USD"
            address = request.form.get("address", "").strip()

            try:
                rooms = int(request.form.get("rooms", "1") or "1")
            except:
                rooms = 1
            try:
                area = float(request.form.get("area", "0") or "0")
            except:
                area = 0

            latitude = request.form.get("latitude", "").strip()
            longitude = request.form.get("longitude", "").strip()

            try:
                latitude_value = float(latitude)
                longitude_value = float(longitude)
                if not (-90 <= latitude_value <= 90 and -180 <= longitude_value <= 180):
                    raise ValueError
            except:
                flash("Joylashuv aniqlanmadi. Brauzer GPS ruxsatini yoqing va 'Qayta aniqlash' tugmasini bosing.")
                return redirect(f"/add?service={service}&category={category['slug']}")

            draft = {
                "service": service,
                "category_id": category["id"],
                "category_slug": category["slug"],
                "listing_kind": "real_estate",
                "title": title,
                "description": description,
                "price": price,
                "property_type": property_type,
                "deal_type": deal_type,
                "mortgage": 1 if request.form.get("mortgage") == "1" else 0,
                "city": city,
                "district": district,
                "address": address,
                "rooms": rooms,
                "area": area,
                "image": image_names[0],
                "images": image_names,
                "latitude": latitude_value,
                "longitude": longitude_value,
                "brand": "",
                "model": "",
                "production_year": None,
                "body_type": "",
                "mileage": 0,
                "fuel_type": "",
                "transmission": "",
                "engine_volume": "",
                "color": "",
                "currency": currency_re,
                "condition": "",
                "contact_phone": ""
            }

        if service_price > 0:
            user = current_user()
            if int(user["balance"] or 0) < service_price and not pay_any_ready():
                flash(f"{SERVICE_NAMES[service]} xizmati uchun balans yetarli emas.")
                return redirect("/post-ad")

        session["new_listing_draft"] = draft
        return redirect("/add/payment")

    balance = int(current_user()["balance"] or 0)
    price_text = "0 so'm" if service_price == 0 else money(service_price)

    if is_auto:
        brands_json = json.dumps(CAR_BRANDS, ensure_ascii=False)
        brand_options = "".join(f"<option value=\"{esc(b)}\">{esc(b)}</option>" for b in CAR_BRANDS)
        body_options = "".join(f"<option>{esc(x)}</option>" for x in CAR_BODY_TYPES)
        fuel_options = "".join(f"<option>{esc(x)}</option>" for x in CAR_FUEL_TYPES)
        trans_options = "".join(f"<option>{esc(x)}</option>" for x in CAR_TRANSMISSIONS)
        cond_options = "".join(f"<option>{esc(x)}</option>" for x in CAR_CONDITIONS)
        color_options = "".join(f"<option>{esc(x)}</option>" for x in CAR_COLORS)
        content = f"""
        <div class="form-card" style="max-width:950px">
          <h1>🚗 AVTO E'LONI</h1>
          <p><strong>Bo'lim:</strong> {esc(category['name'])} &nbsp; | &nbsp; <strong>Xizmat:</strong> {SERVICE_NAMES[service]} — {price_text}</p>

          <form method="post" enctype="multipart/form-data">
            <input type="hidden" name="service" value="{esc(service)}">
            <input type="hidden" name="category" value="{esc(category['slug'])}">

            <div class="split-form">
              <div class="full"><h2>📌 Asosiy ma'lumotlar</h2></div>

              <div><label>Marka</label>
                <select name="brand" id="carBrand" required>
                  <option value="">Markani tanlang</option>{brand_options}
                </select>
              </div>
              <div><label>Model</label>
                <select name="model" id="carModel" required>
                  <option value="">Avval markani tanlang</option>
                </select>
              </div>
              <div><label>Ishlab chiqarilgan yili</label>
                <input name="production_year" type="number" min="1886" max="{datetime.now().year+1}" placeholder="{datetime.now().year}" required>
              </div>
              <div><label>Kuzov turi</label><select name="body_type" required>{body_options}</select></div>
              <div><label>Yurgan masofasi (km)</label><input name="mileage" type="number" min="0" value="0" required></div>
              <div><label>Yoqilg'i turi</label><select name="fuel_type" required>{fuel_options}</select></div>
              <div><label>Uzatmalar qutisi</label><select name="transmission" required>{trans_options}</select></div>
              <div><label>Dvigatel hajmi</label><input name="engine_volume" placeholder="1.5 L / 2.0 L / 1500 cc"></div>
              <div><label>Rangi</label><select name="color" required>{color_options}</select></div>

              <div class="full"><h2>📍 Joylashuv</h2></div>
              {geo_form_html()}
              <div class="full"><h2>💰 Narx</h2></div>
              <div><label>Narxi</label><input name="price" type="number" min="0" required></div>
              <div><label>Valyuta</label>
                <select name="currency">
                  <option value="USD">$ — AQSH dollari</option>
                  <option value="UZS">so'm — O'zbekiston so'mi</option>
                  <option value="EUR">€ — Yevro</option>
                </select>
              </div>

              <div class="full"><h2>📝 Qo'shimcha</h2></div>
              <div><label>Holati</label><select name="condition" required>{cond_options}</select></div>
              <div><label>Telefon</label><input name="contact_phone" placeholder="998901234567" required></div>
              <div class="full"><label>Sarlavha (ixtiyoriy)</label><input name="title" placeholder="Masalan: Chevrolet Cobalt 2024"></div>
              <div class="full"><label>Tavsif</label><textarea name="description" placeholder="Avtomobil haqida batafsil ma'lumot..."></textarea></div>

              <div class="full">
                <label>📷 Rasmlar — 10 tagacha</label>
                <div class="upload-box">
                  <strong>1–10 ta rasm tanlang</strong>
                  <div style="color:#888;font-size:12px;margin:6px 0 10px">JPG, JPEG, PNG yoki WEBP</div>
                  <input id="imageInput" name="images" type="file" accept=".jpg,.jpeg,.png,.webp" multiple required>
                  <div id="imageCount" style="font-size:12px;color:#666;margin-top:8px">0 / 10 ta rasm tanlangan</div>
                  <div id="previewGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px;margin-top:12px"></div>
                </div>
              </div>

              <div class="full" style="background:#fff8d8;border:1px solid #f0d96b;border-radius:14px;padding:14px">
                <strong>💳 To'lov:</strong> {price_text}<br>
                Hozirgi balans: <strong>{money(balance)}</strong>
              </div>
              <div class="full"><button class="post-btn" type="submit" style="width:100%;padding:14px">➡️ Keyingi qadam: To'lov</button></div>
            </div>
          </form>
        </div>

        <script>
        const CAR_BRANDS = {brands_json};
        const brandSelect = document.getElementById('carBrand');
        const modelSelect = document.getElementById('carModel');
        brandSelect.addEventListener('change', function(){{
          const models = CAR_BRANDS[this.value] || [];
          modelSelect.innerHTML = '<option value="">Modelni tanlang</option>';
          models.forEach(function(model){{
            const option = document.createElement('option');
            option.value = model; option.textContent = model;
            modelSelect.appendChild(option);
          }});
        }});
        const imageInput=document.getElementById('imageInput');
        const previewGrid=document.getElementById('previewGrid');
        let selectedImages=[];
        function syncImageFiles(){{
          const dt=new DataTransfer();
          selectedImages.slice(0,10).forEach(function(file){{ dt.items.add(file); }});
          imageInput.files=dt.files;
        }}
        function renderImagePreviews(){{
          previewGrid.innerHTML='';
          selectedImages.slice(0,10).forEach(function(file,index){{
            const box=document.createElement('div'); box.style.position='relative';
            const img=document.createElement('img');
            img.src=URL.createObjectURL(file); img.style.width='100%'; img.style.height='100px';
            img.style.objectFit='cover'; img.style.borderRadius='10px'; img.style.border='1px solid #ddd';
            box.appendChild(img);
            const label=document.createElement('div'); label.textContent=(index+1)+' / 10';
            label.style.cssText='font-size:11px;color:#666;margin-top:3px;text-align:center'; box.appendChild(label);
            const remove=document.createElement('button'); remove.type='button'; remove.textContent='×';
            remove.style.cssText='position:absolute;right:4px;top:4px;width:26px;height:26px;border:0;border-radius:50%;background:#e53935;color:#fff;font-size:18px;line-height:26px;cursor:pointer;padding:0';
            remove.onclick=function(){{ selectedImages.splice(index,1); syncImageFiles(); renderImagePreviews(); }};
            box.appendChild(remove); previewGrid.appendChild(box);
          }});
          const info=document.getElementById('imageCount');
          if(info) info.textContent=selectedImages.length+' / 10 ta rasm tanlangan';
        }}
        imageInput.addEventListener('change', function(){{
          const incoming=[...this.files];
          for(const file of incoming){{
            const duplicate=selectedImages.some(function(old){{ return old.name===file.name && old.size===file.size && old.lastModified===file.lastModified; }});
            if(!duplicate && selectedImages.length<10) selectedImages.push(file);
          }}
          syncImageFiles(); renderImagePreviews();
        }});
        </script>
        """
    else:
        content = f"""
        <div class="form-card" style="max-width:900px">
          <h1>🏠 Yangi e'lon joylash</h1>
          <p>Bo'lim: <strong>{esc(category['name'])}</strong> — Xizmat: <strong>{SERVICE_NAMES[service]}</strong> — {price_text}</p>

          <div class="location-box">
            <strong>📍 Joylashuv avtomatik aniqlanadi</strong>
            <div id="locationStatus" style="margin-top:5px;color:#777">GPS aniqlanmoqda...</div>
            <button type="button" class="btn-yellow" style="margin-top:10px" onclick="getLocation()">📍 Qayta aniqlash</button>
            <div style="margin-top:8px;color:#777;font-size:12px">Brauzerda Uy77 uchun joylashuvga ruxsat bering. Sayt HTTPS bo'lsa GPS yanada ishonchli ishlaydi.</div>
          </div>

          <form method="post" enctype="multipart/form-data" onsubmit="return checkLocation();">
            <input type="hidden" name="service" value="{esc(service)}">
            <input type="hidden" name="category" value="{esc(category['slug'])}">
            <input type="hidden" id="latitude" name="latitude">
            <input type="hidden" id="longitude" name="longitude">

            <div class="split-form">
              <div class="full"><label>E'lon nomi</label><input name="title" placeholder="Masalan: Chilonzorda 3 xonali kvartira" required></div>
              <div><label>Bo'lim turi</label><select name="deal_type"><option>Sotuv</option><option>Ijara</option><option>Kunlik</option></select></div>
              <div><label>Mulk turi</label><select name="property_type"><option>Kvartira</option><option>Hovli</option><option>Yer</option><option>Ofis</option><option>Do'kon</option></select></div>
              <div><label>Narxi</label><input name="price" type="number" min="0" required></div>
              <div><label>Valyuta</label>
                <select name="currency">
                  <option value="USD">$ — AQSH dollari</option>
                  <option value="UZS">so'm — O'zbekiston so'mi</option>
                  <option value="EUR">€ — Yevro</option>
                </select>
              </div>
              {geo_form_html()}
              <div><label>Xonalar soni</label><input name="rooms" type="number" min="1" value="1"></div>
              <div><label>Maydon, m²</label><input name="area" type="number" step="0.1" value="0"></div>
              <div class="full"><label>Manzil</label><input name="address" placeholder="Ko'cha, uy, mo'ljal..."></div>

              <div class="full">
                <label>📷 Rasm — 10 tagacha</label>
                <div class="upload-box">
                  <strong>10 tagacha rasm tanlang</strong>
                  <div style="color:#888;font-size:12px;margin:6px 0 10px">JPG, JPEG, PNG yoki WEBP</div>
                  <input id="imageInput" name="images" type="file" accept=".jpg,.jpeg,.png,.webp" multiple required>
                  <div id="imageCount" style="font-size:12px;color:#666;margin-top:8px">0 / 10 ta rasm tanlangan</div>
                  <div id="previewGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px;margin-top:12px"></div>
                </div>
              </div>

              <div class="full"><label>Tavsif</label><textarea name="description" placeholder="Uy haqida batafsil ma'lumot..."></textarea></div>
              <div class="full"><label><input type="checkbox" name="mortgage" value="1" style="width:auto"> 🏦 Ipotekaga mumkin</label></div>
              <div class="full" style="background:#fff8d8;border:1px solid #f0d96b;border-radius:14px;padding:14px">
                <strong>💳 To'lov:</strong> {price_text}<br>Hozirgi balans: <strong>{money(balance)}</strong>
              </div>
              <div class="full"><button class="post-btn" type="submit" style="width:100%;padding:14px">➡️ Keyingi qadam: To'lov</button></div>
            </div>
          </form>
        </div>

        <script>
        let locationReady=false;
        function getLocation(){{
          const status=document.getElementById('locationStatus');
          if(!navigator.geolocation){{
            status.innerHTML='❌ Brauzer GPS-ni qo\\'llab-quvvatlamaydi.'; return;
          }}
          status.innerHTML='⏳ Joylashuv aniqlanmoqda...';
          navigator.geolocation.getCurrentPosition(
            function(position){{
              document.getElementById('latitude').value=position.coords.latitude;
              document.getElementById('longitude').value=position.coords.longitude;
              locationReady=true;
              status.innerHTML='✅ Joylashuv aniqlandi: '+position.coords.latitude.toFixed(6)+', '+position.coords.longitude.toFixed(6);
            }},
            function(error){{
              locationReady=false;
              let msg='❌ Joylashuv aniqlanmadi.';
              if(error && error.code===1) msg='❌ Joylashuv ruxsati berilmadi. Brauzer sozlamasidan Uy77 uchun Location/GPS ruxsatini yoqing.';
              else if(error && error.code===2) msg='❌ Joylashuvni aniqlab bo‘lmadi. GPS/Wi-Fi ni yoqing va qayta urinib ko‘ring.';
              else if(error && error.code===3) msg='⏱ GPS vaqtida javob bermadi. Qayta aniqlash tugmasini bosing.';
              status.innerHTML=msg;
            }},
            {{enableHighAccuracy:false, timeout:30000, maximumAge:60000}}
          );
        }}
        function checkLocation(){{
          if(!locationReady){{
            alert('Avval joylashuv aniqlanishini kuting yoki GPS ruxsatini yoqing.');
            return false;
          }}
          return true;
        }}
        const imageInput=document.getElementById('imageInput');
        imageInput.addEventListener('change', function(){{
          const files=[...this.files], grid=document.getElementById('previewGrid');
          grid.innerHTML='';
          if(files.length>10){{ alert('Ko\\'pi bilan 10 ta rasm tanlang.'); this.value=''; return; }}
          files.forEach(function(file){{
            const img=document.createElement('img');
            img.src=URL.createObjectURL(file); img.style.width='100%'; img.style.height='100px';
            img.style.objectFit='cover'; img.style.borderRadius='10px'; img.style.border='1px solid #ddd';
            grid.appendChild(img);
          }});
        }});
        window.addEventListener('load', getLocation);
        </script>
        """

    return render_page(content, "Yangi e'lon")


# =========================================================
# ADD PAYMENT
# =========================================================

@app.route(
    "/add/payment",
    methods=["GET", "POST"]
)
def add_payment():

    if not login_required():
        return redirect("/login")

    draft = session.get(
        "new_listing_draft"
    )

    if not draft:

        flash(
            "E'lon ma'lumotlari topilmadi."
        )

        return redirect("/post-ad")

    prices = service_prices()

    service = draft.get(
        "service",
        "free"
    )

    if service not in prices:

        session.pop(
            "new_listing_draft",
            None
        )

        return redirect("/post-ad")

    amount = prices[service]

    service_title = SERVICE_NAMES[service]

    if request.method == "GET":

        user = current_user()

        balance = int(
            user["balance"] or 0
        )

        remaining = balance - amount

        enough = remaining >= 0

        content = f"""

        <div
            class="form-card"
            style="max-width:850px"
        >

        <h1>
        💳 To'lovni tasdiqlash
        </h1>

        <div
            style="
            border:1px solid #eee;
            border-radius:18px;
            padding:20px
            "
        >

        <div>
        Xizmat:
        <strong>
        {service_title}
        </strong>
        </div>

        <div>
        Narxi:
        <strong>
        {money(amount)}
        </strong>
        </div>

        <hr>

        <div>
        Joriy balans:
        <strong>
        {money(balance)}
        </strong>
        </div>

        <div>
        To'lovdan keyingi balans:
        <strong>
        {money(max(remaining,0))}
        </strong>
        </div>

        </div>

        <div
            style="
            margin-top:18px;
            padding:16px;
            border-radius:14px;
            background:{
                '#eafaf0'
                if enough
                else
                '#fff0f0'
            }
            "
        >

        {
            '✅ Balans yetarli. Tasdiqlasangiz, pul yechiladi va e’lon joylanadi.'
            if enough
            else
            '❌ Balans yetarli emas. Pul yechilmaydi va e’lon joylanmaydi.'
        }

        </div>

        <div
            style="
            margin-top:20px;
            display:flex;
            gap:12px;
            flex-wrap:wrap
            "
        >

        <a
            class="view-pill"
            href="/add?service={service}&category={draft['category_slug']}"
        >
        ← O'zgartirish
        </a>

        {
            f'''
            <form method="post">
            <button class="post-btn" type="submit">
            💳 To'lash va e'lonni joylash
            </button>
            </form>
            '''
            if enough
            else
            '''
            <a class="post-btn" href="/profile">
            💰 Balansni to'ldirish
            </a>
            '''
        }

        </div>

        </div>

        """

        if pay_any_ready() and amount > 0:
            click_form = (
                '<form method="post" action="/pay/click/listing">'
                '<button class="post-btn" type="submit">💳 Karta orqali to\'lash</button>'
                '</form>'
            )
            _i = content.rfind("</div>")
            _j = content.rfind("</div>", 0, _i)
            content = content[:_j] + click_form + content[_j:]
            content = content.replace(
                "❌ Balans yetarli emas. Pul yechilmaydi va e’lon joylanmaydi.",
                "💳 Balans yetarli emas. Karta orqali to'lang: to'lov avtomatik o'tadi va e'lon darrov joylanadi."
            )
        return render_page(
            content,
            "To'lov"
        )

    c = db()

    try:

        c.execute(
            "BEGIN IMMEDIATE"
        )

        user = c.execute(
            """
            SELECT id,balance
            FROM users
            WHERE id=?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

        if not user:

            c.rollback()
            c.close()

            flash(
                "Foydalanuvchi topilmadi."
            )

            return redirect("/login")

        if amount > 0:

            cur = c.execute(
                """
                UPDATE users
                SET balance=balance-?
                WHERE id=?
                AND balance>=?
                """,
                (
                    amount,
                    session["user_id"],
                    amount
                )
            )

            if cur.rowcount != 1:

                c.rollback()
                c.close()

                flash(
                    "Balans yetarli emas."
                )

                return redirect(
                    "/post-ad"
                )

        now = datetime.now()

        vip_value = (
            1
            if service == "vip"
            else 0
        )

        top_value = (
            1
            if service == "top"
            else 0
        )

        vip_until = (
            (
                now +
                timedelta(days=7)
            ).isoformat()
            if service == "vip"
            else None
        )

        top_until = (
            (
                now +
                timedelta(days=7)
            ).isoformat()
            if service == "top"
            else None
        )

        c.execute(
            """
            INSERT INTO listings
            (
                user_id,
                title,
                description,
                price,
                property_type,
                deal_type,
                mortgage,
                city,
                district,
                address,
                rooms,
                area,
                image,
                images,
                latitude,
                longitude,
                category_id,
                listing_kind,
                brand,
                model,
                production_year,
                body_type,
                mileage,
                fuel_type,
                transmission,
                engine_volume,
                color,
                currency,
                condition,
                contact_phone,
                vip,
                top,
                vip_until,
                top_until,
                hidden
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                session["user_id"],
                draft["title"],
                draft["description"],
                draft["price"],
                draft["property_type"],
                draft["deal_type"],
                draft["mortgage"],
                draft["city"],
                draft["district"],
                draft["address"],
                draft["rooms"],
                draft["area"],
                draft["image"],
                json.dumps(draft.get("images", [draft["image"]]), ensure_ascii=False),
                draft["latitude"],
                draft["longitude"],
                draft["category_id"],
                draft.get("listing_kind", "real_estate"),
                draft.get("brand", ""),
                draft.get("model", ""),
                draft.get("production_year"),
                draft.get("body_type", ""),
                draft.get("mileage", 0),
                draft.get("fuel_type", ""),
                draft.get("transmission", ""),
                draft.get("engine_volume", ""),
                draft.get("color", ""),
                draft.get("currency", "USD"),
                draft.get("condition", ""),
                draft.get("contact_phone", ""),
                vip_value,
                top_value,
                vip_until,
                top_until
            )
        )

        listing_id = c.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        if amount > 0:

            c.execute(
                """
                INSERT INTO payments
                (
                    user_id,
                    listing_id,
                    service,
                    amount,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    listing_id,
                    service.upper(),
                    amount,
                    "paid"
                )
            )

        c.commit()
        c.close()

    except Exception as e:

        try:
            c.rollback()
        except:
            pass

        c.close()

        print(
            "ADD PAYMENT ERROR:",
            e
        )

        flash(
            "To'lov vaqtida xatolik yuz berdi."
        )

        return redirect(
            "/add/payment"
        )

    session.pop(
        "new_listing_draft",
        None
    )

    flash(
        f"{service_title} xizmati uchun "
        f"to'lov qabul qilindi va e'lon joylandi!"
    )

    return redirect(
        f"/listing/{listing_id}"
    )


# =========================================================
# MAP
# =========================================================

@app.route("/map")
def map_page():

    cleanup_expired()

    c = db()

    rows = c.execute("""
        SELECT
            listings.*,
            users.name owner,
            users.phone owner_phone
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE listings.latitude IS NOT NULL
        AND listings.longitude IS NOT NULL
        AND listings.hidden=0
        AND users.blocked=0
        AND listings.listing_kind='real_estate' 
        ORDER BY
            listings.vip DESC,
            listings.top DESC,
            listings.bumped_at DESC,
            listings.id DESC
    """).fetchall()

    c.close()

    markers = []

    for row in rows:

        image = ""

        if row["image"]:

            image = url_for(
                "uploaded_file",
                filename=row["image"]
            )

        markers.append({

            "id": row["id"],

            "title": row["title"],

            "price": money(
                row["price"]
            ),

            "raw_price": row["price"],

            "lat": row["latitude"],

            "lng": row["longitude"],

            "image": image,

            "city": row["city"],

            "district": row["district"],

            "property_type": row["property_type"],

            "deal_type": row["deal_type"],

            "mortgage": row["mortgage"],

            "rooms": row["rooms"],

            "owner": row["owner"],

            "phone": row["owner_phone"]

        })

    marker_json = json.dumps(
        markers,
        ensure_ascii=False
    )

    content = f"""

    <h1>
    🗺 Uy77 xaritasi
    </h1>

    <p>
    Har bir sariq belgi — e'lon narxini ko'rsatadi.
    </p>

    <div class="map-wrap">

    <div id="map"></div>

    </div>

    <script>

    const listings =
    {marker_json};

    const map =
    L.map("map").setView(
        [41.2995,69.2401],
        11
    );

    L.tileLayer(
        "https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
        {{
            maxZoom:19,
            attribution:"&copy; OpenStreetMap"
        }}
    ).addTo(map);

    const bounds=[];

    listings.forEach(function(item){{

        const position=[
            Number(item.lat),
            Number(item.lng)
        ];

        bounds.push(position);

        const priceIcon =
        L.divIcon({{
            className:"",
            html:
            '<div class="price-marker">'
            +
            escapeHtml(item.price)
            +
            '</div>',
            iconSize:null,
            iconAnchor:[0,20]
        }});

        const marker =
        L.marker(
            position,
            {{
                icon:priceIcon
            }}
        ).addTo(map);

        let imageHtml="";

        if(item.image){{

            imageHtml =
            '<img src="'
            +
            item.image
            +
            '">';

        }}else{{

            imageHtml =
            '<div style="height:100px;background:#eee;display:flex;align-items:center;justify-content:center;">'
            +
            '📷 Rasm yo‘q'
            +
            '</div>';

        }}

        const popup =
        '<div class="map-popup">'
        +
        imageHtml
        +
        '<h3>'
        +
        escapeHtml(item.title)
        +
        '</h3>'
        +
        '<div class="map-price">'
        +
        escapeHtml(item.price)
        +
        '</div>'
        +
        '<p>📍 '
        +
        escapeHtml(item.city)
        +
        ', '
        +
        escapeHtml(item.district)
        +
        '</p>'
        +
        '<p>🏠 '
        +
        escapeHtml(item.property_type)
        +
        ' | '
        +
        escapeHtml(item.deal_type)
        +
        ' | 🛏 '
        +
        item.rooms
        +
        ' xona</p>'
        +
        (
            item.mortgage
            ?
            '<p>🏦 Ipotekaga mumkin</p>'
            :
            ''
        )
        +
        '<p>👤 '
        +
        escapeHtml(item.owner)
        +
        '</p>'
        +
        '<a class="btn" href="/listing/'
        +
        item.id
        +
        '">'
        +
        'Batafsil'
        +
        '</a>'
        +
        '</div>';

        marker.bindPopup(
            popup
        );

    }});

    if(bounds.length>0){{

        map.fitBounds(
            bounds,
            {{
                padding:[40,40]
            }}
        );

    }}

    function escapeHtml(value){{

        return String(value ?? "")
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");

    }}

    </script>

    """

    return render_page(
        content,
        "Xarita"
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    if not login_required():

        return redirect("/login")

    user = current_user()

    if not user:

        session.clear()

        return redirect("/login")

    cleanup_expired()

    prices = service_prices()

    c = db()

    rows = c.execute("""
        SELECT *
        FROM listings
        WHERE user_id=?
        AND hidden=0
        ORDER BY
            vip DESC,
            top DESC,
            bumped_at DESC,
            id DESC
    """, (
        user["id"],
    )).fetchall()

    payments = c.execute("""
        SELECT
            payments.*,
            listings.title
        FROM payments
        LEFT JOIN listings
        ON listings.id=payments.listing_id
        WHERE payments.user_id=?
        ORDER BY payments.id DESC
        LIMIT 20
    """, (
        user["id"],
    )).fetchall()

    c.close()

    initials = "".join(
        x[:1].upper()
        for x in str(
            user["name"] or "K"
        ).split()
        if x
    )[:2] or "K"

    listing_cards = ""

    for row in rows:

        image = (
            f"""
            <img
                src="/uploads/{esc(row['image'])}"
                alt="{esc(row['title'])}"
            >
            """
            if row["image"]
            else
            """
            <div
                style="
                height:100%;
                display:grid;
                place-items:center;
                font-size:35px
                "
            >
            🏠
            </div>
            """
        )

        if row["vip"]:

            badge = """
            <span class="badge vip">
            👑 VIP
            </span>
            """

        elif row["top"]:

            badge = """
            <span class="badge top">
            🔥 TOP
            </span>
            """

        else:

            badge = """
            <span
                style="
                background:#eee;
                padding:5px 8px;
                border-radius:8px;
                font-size:10px
                "
            >
            Oddiy
            </span>
            """

        listing_cards += f"""

        <article class="property-card">

        <div class="property-image">

        {image}

        <div class="badge-stack">
        {badge}
        </div>

        <div class="property-overlay">

        <div class="property-price">
        {price_of(row)}
        </div>

        </div>

        </div>

        <div class="property-body">

        <strong>
        {esc(row['title'])}
        </strong>

        <div class="meta">

        <span>
        📍 {esc(row['district'])}
        </span>

        <span>
        🛏 {row['rooms']}
        </span>

        </div>

        <div
            style="
            display:flex;
            gap:5px;
            margin-top:10px;
            flex-wrap:wrap
            "
        >

        <form
            method="post"
            action="/service/{row['id']}/vip"
        >

        <button
            class="btn-yellow"
            type="submit"
        >
        VIP
        </button>

        </form>

        <form
            method="post"
            action="/service/{row['id']}/top"
        >

        <button
            class="btn-yellow"
            type="submit"
        >
        TOP
        </button>

        </form>

        <form
            method="post"
            action="/service/{row['id']}/up"
        >

        <button
            class="btn-yellow"
            type="submit"
        >
        Tepaga
        </button>

        </form>

        </div>

        <div
            style="
            display:flex;
            justify-content:space-between;
            margin-top:10px
            "
        >

        <a
            href="/listing/{row['id']}"
            class="small-link"
        >
        Batafsil →
        </a>

        <form
            method="post"
            action="/delete-listing/{row['id']}"
            onsubmit="return confirm('E’lon o‘chirilsinmi?')"
        >

        <button
            style="
            border:0;
            background:none;
            color:#d44
            "
        >
        O‘chirish
        </button>

        </form>

        </div>

        </div>

        </article>

        """

    if not listing_cards:

        listing_cards = """

        <div class="empty">

        <div style="font-size:40px">
        🏠
        </div>

        <h3>
        Hozircha e’lonlaringiz yo‘q
        </h3>

        <p>
        Birinchi e’loningizni joylashtiring.
        </p>

        <a
            href="/post-ad"
            class="post-btn"
        >
        ＋ E’lon joylash
        </a>

        </div>

        """

    service_names = {

        "VIP":
        "👑 VIP",

        "TOP":
        "🔥 TOP",

        "UP":
        "🚀 Tepaga"

    }

    payment_rows = ""

    for p in payments:

        payment_rows += f"""

        <tr>

        <td>
        {esc(str(p["created_at"])[:16])}
        </td>

        <td>
        {service_names.get(
            str(p["service"]).upper(),
            esc(p["service"])
        )}
        </td>

        <td>
        <strong>
        -{money(p["amount"])}
        </strong>
        </td>

        <td>
        <span
            style="
            background:#dcf8e4;
            color:#249b4d;
            padding:5px 8px;
            border-radius:10px;
            font-size:9px
            "
        >
        ✓ To‘langan
        </span>
        </td>

        </tr>

        """

    if not payment_rows:

        payment_rows = """
        <tr>
        <td colspan="4" style="text-align:center">
        Hozircha to‘lovlar tarixi yo‘q.
        </td>
        </tr>
        """

    content = f"""

    <div
        style="
        display:grid;
        grid-template-columns:250px 1fr;
        gap:20px
        "
    >

    <aside
        style="
        background:#fff;
        border:1px solid #eee;
        border-radius:15px;
        padding:20px;
        height:max-content
        "
    >

    <div
        style="
        display:flex;
        gap:10px;
        align-items:center;
        margin-bottom:20px
        "
    >

    <div
        style="
        width:48px;
        height:48px;
        border-radius:50%;
        background:#263548;
        color:#fff;
        display:grid;
        place-items:center;
        font-weight:800
        "
    >
    {esc(initials)}
    </div>

    <div>

    <strong>
    {esc(user["name"])}
    </strong>

    <div
        style="
        color:#777;
        font-size:11px
        "
    >
    +{esc(user["phone"])}
    </div>

    </div>

    </div>

    <div style="display:grid;gap:5px">

    <a
        class="view-pill active"
        href="/profile"
    >
    ◉ Profil
    </a>

    <a
        class="view-pill"
        href="#my-listings"
    >
    ▣ Mening e’lonlarim
    </a>

    <a
        class="view-pill"
        href="#services"
    >
    ☆ VIP / TOP / UP
    </a>

    <a
        class="view-pill"
        href="#payments"
    >
    ▤ To‘lovlar tarixi
    </a>

    <a
        class="view-pill"
        href="/logout"
    >
    ⇥ Chiqish
    </a>

    </div>

    </aside>


    <section>

    <h1>
    Profil
    </h1>

    <div
        style="
        display:grid;
        grid-template-columns:1fr 300px;
        gap:15px
        "
    >

    <div class="form-card" style="margin:0">

    <h2>
    {esc(user["name"])}
    </h2>

    <p>
    📱 +{esc(user["phone"])}
    </p>

    <p>
    ✓ Telefon tasdiqlangan
    </p>

    </div>


    <div
        class="form-card"
        style="
        margin:0;
        background:#fff9df
        "
    >

    <strong>
    💰 Balans
    </strong>

    <div
        style="
        font-size:25px;
        font-weight:900;
        margin:10px 0
        "
    >
    {money(user["balance"])}
    </div>

    <p>
    VIP, TOP va UP xizmatlaridan foydalanishingiz mumkin.
    </p>

    <a class="kd-btn" style="display:inline-block;margin-top:10px;padding:10px 18px" href="/balance/topup">➕ Balansni to'ldirish</a>

    </div>

    </div>


    <div
        id="services"
        class="section-head"
    >

    <div>
    <h2>
    Xizmatlar
    </h2>
    </div>

    </div>

    <div
        style="
        display:grid;
        grid-template-columns:repeat(3,1fr);
        gap:12px
        "
    >

    <div class="form-card" style="margin:0">

    <div style="font-size:30px">
    👑
    </div>

    <h3>
    VIP
    </h3>

    <strong>
    {money(prices["vip"])}
    </strong>

    <p>
    7 kun
    </p>

    </div>


    <div class="form-card" style="margin:0">

    <div style="font-size:30px">
    🔥
    </div>

    <h3>
    TOP
    </h3>

    <strong>
    {money(prices["top"])}
    </strong>

    <p>
    7 kun
    </p>

    </div>


    <div class="form-card" style="margin:0">

    <div style="font-size:30px">
    🚀
    </div>

    <h3>
    Tepaga
    </h3>

    <strong>
    {money(prices["up"])}
    </strong>

    <p>
    Bir marta
    </p>

    </div>

    </div>


    <div
        id="my-listings"
        class="section-head"
    >

    <h2>
    Mening e’lonlarim
    </h2>

    </div>

    <div class="all-grid">

    {listing_cards}

    </div>


    <div
        id="payments"
        class="section-head"
    >

    <h2>
    To‘lovlar tarixi
    </h2>

    </div>

    <div class="table-wrap">

    <table>

    <thead>

    <tr>

    <th>
    Sana
    </th>

    <th>
    Xizmat
    </th>

    <th>
    Summa
    </th>

    <th>
    Holat
    </th>

    </tr>

    </thead>

    <tbody>

    {payment_rows}

    </tbody>

    </table>

    </div>

    </section>

    </div>

    """

    return render_page(
        content,
        "Profil — Uy77"
    )


# =========================================================
# DELETE LISTING
# =========================================================

@app.route(
    "/delete-listing/<int:listing_id>",
    methods=["POST"]
)
def delete_listing(listing_id):

    if not login_required():
        return redirect("/login")

    c = db()

    row = c.execute("""
        SELECT *
        FROM listings
        WHERE id=?
        AND user_id=?
    """, (
        listing_id,
        session["user_id"]
    )).fetchone()

    if not row:

        c.close()

        flash(
            "E'lon topilmadi."
        )

        return redirect("/profile")

    if row["image"]:

        image_path = os.path.join(
            UPLOADS,
            row["image"]
        )

        if os.path.exists(
            image_path
        ):

            try:
                os.remove(
                    image_path
                )
            except:
                pass

    c.execute(
        "DELETE FROM listings WHERE id=?",
        (listing_id,)
    )

    c.commit()
    c.close()

    flash(
        "E'lon o'chirildi."
    )

    return redirect("/profile")


# =========================================================
# BUY SERVICE
# =========================================================

@app.route(
    "/service/<int:listing_id>/<service>",
    methods=["POST"]
)
def buy_service(
    listing_id,
    service
):

    if not login_required():
        return redirect("/login")

    prices = service_prices()

    if service not in {
        "vip",
        "top",
        "up"
    }:

        flash(
            "Noto'g'ri xizmat."
        )

        return redirect(
            f"/listing/{listing_id}"
        )

    amount = prices[service]

    c = db()

    try:

        c.execute(
            "BEGIN IMMEDIATE"
        )

        listing = c.execute(
            """
            SELECT *
            FROM listings
            WHERE id=?
            """,
            (listing_id,)
        ).fetchone()

        user = c.execute(
            """
            SELECT *
            FROM users
            WHERE id=?
            """,
            (session["user_id"],)
        ).fetchone()

        if not listing:

            c.rollback()
            c.close()

            flash(
                "E'lon topilmadi."
            )

            return redirect("/")

        if listing["user_id"] != session["user_id"]:

            c.rollback()
            c.close()

            flash(
                "Bu e'lon sizga tegishli emas."
            )

            return redirect(
                f"/listing/{listing_id}"
            )

        if user["balance"] < amount:

            c.rollback()
            c.close()
            if pay_any_ready():
                return click_order_redirect(
                    session["user_id"], int(amount), "service", service, listing_id
                )

            flash(
                f"Balans yetarli emas. "
                f"Kerak: {money(amount)}"
            )

            return redirect("/profile")

        now = datetime.now()

        if service == "vip":

            until = (
                now +
                timedelta(days=7)
            )

            c.execute(
                """
                UPDATE listings
                SET vip=1,
                    vip_until=?
                WHERE id=?
                """,
                (
                    until.isoformat(),
                    listing_id
                )
            )

        elif service == "top":

            until = (
                now +
                timedelta(days=7)
            )

            c.execute(
                """
                UPDATE listings
                SET top=1,
                    top_until=?
                WHERE id=?
                """,
                (
                    until.isoformat(),
                    listing_id
                )
            )

        elif service == "up":

            until = (
                now +
                timedelta(hours=24)
            )

            c.execute(
                """
                UPDATE listings
                SET bumped_at=?,
                    up_until=?
                WHERE id=?
                """,
                (
                    now.isoformat(),
                    until.isoformat(),
                    listing_id
                )
            )

        cur = c.execute(
            """
            UPDATE users
            SET balance=balance-?
            WHERE id=?
            AND balance>=?
            """,
            (
                amount,
                session["user_id"],
                amount
            )
        )

        if cur.rowcount != 1:

            c.rollback()
            c.close()

            flash(
                "Balans yetarli emas. "
                "Pul yechilmadi."
            )

            return redirect(
                f"/listing/{listing_id}"
            )

        c.execute(
            """
            INSERT INTO payments
            (
                user_id,
                listing_id,
                service,
                amount,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                listing_id,
                service.upper(),
                amount,
                "paid"
            )
        )

        c.commit()
        c.close()

    except Exception as e:

        try:
            c.rollback()
        except:
            pass

        c.close()

        print(
            "SERVICE ERROR:",
            e
        )

        flash(
            "Xizmatni faollashtirishda xatolik."
        )

        return redirect(
            f"/listing/{listing_id}"
        )

    flash(
        f"{service.upper()} xizmati muvaffaqiyatli faollashtirildi."
    )

    return redirect(
        f"/listing/{listing_id}"
    )


# =========================================================
# =========================================================
#                    ADMIN PANEL
# =========================================================
# =========================================================


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    if admin_required():

        return redirect("/admin")

    if request.method == "POST":

        phone = clean_phone(
            request.form.get(
                "phone",
                ""
            )
        )

        password = request.form.get(
            "password",
            ""
        )

        c = db()

        user = c.execute(
            """
            SELECT *
            FROM users
            WHERE phone=?
            AND is_admin=1
            """,
            (phone,)
        ).fetchone()

        c.close()

        if not user:

            flash(
                "Admin telefon raqami yoki parol noto'g'ri."
            )

            return redirect(
                "/admin-login"
            )

        if user["blocked"]:

            flash(
                "Admin akkaunti bloklangan."
            )

            return redirect(
                "/admin-login"
            )

        if not check_password_hash(
            user["password"],
            password
        ):

            flash(
                "Admin telefon raqami yoki parol noto'g'ri."
            )

            return redirect(
                "/admin-login"
            )

        session.clear()

        session["user_id"] = user["id"]
        session["admin_logged"] = True

        admin_log(
            "ADMIN_LOGIN",
            "Admin panelga kirdi."
        )

        return redirect(
            "/admin"
        )

    content = """

    <style>

    .admin-login{
        max-width:450px;
        margin:50px auto;
        background:#fff;
        border:1px solid #e5e7eb;
        border-radius:22px;
        padding:35px;
        box-shadow:0 15px 50px rgba(0,0,0,.08)
    }

    .admin-login-logo{
        width:60px;
        height:60px;
        border-radius:18px;
        background:#f6c900;
        display:grid;
        place-items:center;
        font-size:30px;
        margin-bottom:18px
    }

    .admin-login button{
        width:100%;
        margin-top:8px
    }

    </style>

    <div class="admin-login">

    <img src="/uy77-logo.svg" alt="Uy77" style="height:64px;width:auto;display:block;margin:0 auto 10px">

    <h1>
    Uy77 ADMIN
    </h1>

    <p style="color:#777">
    Admin panelga kirish
    </p>

    <form method="post">

    <div class="form-group">

    <label>
    Telefon raqam
    </label>

    <input
        name="phone"
        placeholder="998901234567"
        required
    >

    </div>

    <div class="form-group">

    <label>
    Parol
    </label>

    <input
        type="password"
        name="password"
        required
    >

    </div>

    <button
        class="post-btn"
        type="submit"
    >
    🔐 Admin panelga kirish
    </button>

    </form>

    <div
        style="
        margin-top:18px;
        color:#888;
        font-size:12px
        "
    >
    Bu sahifa faqat administratorlar uchun.
    </div>

    </div>

    """

    return render_page(
        content,
        "Admin Login"
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin-logout")
def admin_logout():

    if admin_required():

        admin_log(
            "ADMIN_LOGOUT",
            "Admin paneldan chiqdi."
        )

    session.clear()

    return redirect(
        "/admin-login"
    )


# =========================================================
# ADMIN LAYOUT
# =========================================================

ADMIN_CSS = """

<style>

.admin-shell{
display:flex;
min-height:calc(100vh - 120px);
background:#f5f7fa;
border-radius:18px;
overflow:hidden;
border:1px solid #e4e8ee
}

.admin-sidebar{
width:245px;
background:#182332;
color:#fff;
padding:18px 13px;
flex-shrink:0
}

.admin-brand{
display:flex;
align-items:center;
gap:10px;
padding:10px 11px 20px;
border-bottom:1px solid rgba(255,255,255,.08);
margin-bottom:12px
}

.admin-brand-icon{
width:38px;
height:38px;
border-radius:11px;
background:#f6c900;
display:grid;
place-items:center;
color:#111
}

.admin-brand strong{
font-size:14px
}

.admin-brand span{
display:block;
font-size:9px;
color:#94a3b8;
margin-top:3px
}

.admin-menu{
display:flex;
flex-direction:column;
gap:3px
}

.admin-menu a{
display:flex;
align-items:center;
gap:9px;
padding:10px 11px;
border-radius:9px;
color:#b7c3d2;
font-size:11px;
font-weight:600
}

.admin-menu a:hover{
background:rgba(255,255,255,.07);
color:#fff
}

.admin-menu a.active{
background:#f6c900;
color:#111
}

.admin-menu .logout{
margin-top:12px;
border-top:1px solid rgba(255,255,255,.08);
padding-top:18px
}

.admin-content{
flex:1;
min-width:0;
background:#f7f8fa
}

.admin-topbar{
height:65px;
background:#fff;
border-bottom:1px solid #e4e8ee;
display:flex;
align-items:center;
justify-content:space-between;
padding:0 22px;
gap:15px
}

.admin-top-title{
font-weight:800;
font-size:15px;
color:#172333
}

.admin-top-right{
display:flex;
align-items:center;
gap:15px
}

.admin-search{
width:240px
}

.admin-search input{
height:35px;
font-size:11px;
background:#f5f6f8
}

.admin-user{
display:flex;
align-items:center;
gap:9px
}

.admin-avatar{
width:34px;
height:34px;
border-radius:50%;
background:#f6c900;
display:grid;
place-items:center;
font-size:14px;
font-weight:800
}

.admin-page{
padding:22px
}

.admin-page-title{
font-size:24px;
font-weight:800;
color:#172333;
margin:0 0 5px
}

.admin-page-subtitle{
font-size:11px;
color:#8090a3;
margin-bottom:20px
}

.admin-cards{
display:grid;
grid-template-columns:repeat(4,1fr);
gap:12px;
margin-bottom:18px
}

.admin-card{
background:#fff;
border:1px solid #e4e8ee;
border-radius:13px;
padding:16px;
box-shadow:0 2px 8px rgba(30,50,70,.03)
}

.admin-card-head{
display:flex;
justify-content:space-between;
align-items:center;
color:#74849a;
font-size:10px
}

.admin-card-icon{
width:34px;
height:34px;
border-radius:10px;
background:#fff4b8;
display:grid;
place-items:center;
font-size:17px
}

.admin-card-number{
font-size:24px;
font-weight:900;
margin-top:8px;
color:#172333
}

.admin-card-small{
font-size:9px;
color:#7d8c9f;
margin-top:4px
}

.admin-grid{
display:grid;
grid-template-columns:1.3fr .7fr;
gap:15px;
margin-bottom:18px
}

.admin-panel{
background:#fff;
border:1px solid #e4e8ee;
border-radius:13px;
padding:16px;
box-shadow:0 2px 8px rgba(30,50,70,.03)
}

.admin-panel-title{
font-size:14px;
font-weight:800;
color:#172333;
margin:0 0 14px
}

.admin-table-wrap{
overflow:auto;
border:1px solid #e6eaf0;
border-radius:11px
}

.admin-table{
width:100%;
border-collapse:collapse;
min-width:700px
}

.admin-table th{
background:#f7f8fa;
color:#738297;
font-size:9px;
font-weight:700;
padding:10px;
border-bottom:1px solid #e5e9ee;
text-align:left
}

.admin-table td{
padding:10px;
font-size:10px;
color:#415269;
border-bottom:1px solid #eef1f4;
vertical-align:middle
}

.admin-table tr:last-child td{
border-bottom:0
}

.admin-badge{
display:inline-flex;
align-items:center;
padding:4px 7px;
border-radius:7px;
font-size:8px;
font-weight:800
}

.admin-badge.green{
background:#dcf8e4;
color:#22994b
}

.admin-badge.red{
background:#ffe3e3;
color:#cf4444
}

.admin-badge.yellow{
background:#fff0a7;
color:#6f5b00
}

.admin-badge.blue{
background:#e0f1ff;
color:#2473ae
}

.admin-actions{
display:flex;
gap:5px;
flex-wrap:wrap
}

.admin-btn{
display:inline-flex;
align-items:center;
justify-content:center;
border:0;
border-radius:7px;
padding:7px 9px;
font-size:9px;
font-weight:800;
background:#edf1f5;
color:#34465d;
text-decoration:none
}

.admin-btn:hover{
background:#e2e7ed
}

.admin-btn.yellow{
background:#f6c900;
color:#111
}

.admin-btn.red{
background:#ffe1e1;
color:#c43d3d
}

.admin-btn.green{
background:#dcf8e4;
color:#228b45
}

.admin-btn.dark{
background:#1d2938;
color:#fff
}

.admin-form-grid{
display:grid;
grid-template-columns:repeat(2,1fr);
gap:13px
}

.admin-form-group{
margin-bottom:12px
}

.admin-form-group label{
font-size:10px;
color:#53657b;
margin-bottom:5px
}

.admin-form-group input,
.admin-form-group select,
.admin-form-group textarea{
font-size:11px;
padding:10px
}

.admin-stat-grid{
display:grid;
grid-template-columns:repeat(3,1fr);
gap:10px
}

.admin-mini-stat{
background:#f7f8fa;
border-radius:10px;
padding:12px
}

.admin-mini-stat strong{
display:block;
font-size:18px;
color:#172333
}

.admin-mini-stat span{
font-size:9px;
color:#7a8a9d
}

.admin-price-grid{
display:grid;
grid-template-columns:repeat(3,1fr);
gap:15px
}

.admin-price-card{
background:#fff;
border:1px solid #e4e8ee;
border-radius:13px;
padding:18px
}

.admin-price-card h3{
margin:0 0 8px;
font-size:14px
}

.admin-price{
font-size:25px;
font-weight:900;
margin-bottom:12px
}

.admin-empty{
padding:30px;
text-align:center;
color:#8491a1;
background:#fff;
border:1px dashed #d8dfe7;
border-radius:12px
}

.admin-chart{
display:flex;
align-items:flex-end;
height:220px;
gap:7px;
padding-top:15px
}

.admin-bar{
flex:1;
background:#f6c900;
border-radius:5px 5px 0 0;
min-width:8px;
position:relative
}

.admin-bar span{
position:absolute;
bottom:-20px;
left:50%;
transform:translateX(-50%);
font-size:7px;
color:#8390a1
}

.admin-mobile-menu{
display:none
}

@media(max-width:1100px){

.admin-cards{
grid-template-columns:repeat(2,1fr)
}

.admin-grid{
grid-template-columns:1fr
}

.admin-sidebar{
width:215px
}

}

@media(max-width:800px){

.admin-shell{
display:block
}

.admin-sidebar{
width:100%;
padding:10px
}

.admin-brand{
margin-bottom:5px;
padding-bottom:10px
}

.admin-menu{
display:grid;
grid-template-columns:repeat(3,1fr)
}

.admin-menu .logout{
margin-top:0;
padding-top:10px
}

.admin-topbar{
height:auto;
padding:12px
}

.admin-search{
display:none
}

.admin-page{
padding:12px
}

.admin-price-grid{
grid-template-columns:1fr
}

}

@media(max-width:550px){

.admin-menu{
grid-template-columns:repeat(2,1fr)
}

.admin-cards{
grid-template-columns:1fr 1fr
}

.admin-stat-grid{
grid-template-columns:1fr 1fr
}

.admin-form-grid{
grid-template-columns:1fr
}

}

</style>
"""


def admin_layout(
    content,
    title="Dashboard",
    active="dashboard"
):

    user = current_user()

    menu = [

        (
            "dashboard",
            "🏠",
            "Dashboard",
            "/admin"
        ),

        (
            "users",
            "👥",
            "Foydalanuvchilar",
            "/admin/users"
        ),

        (
            "listings",
            "🏡",
            "E'lonlar",
            "/admin/listings"
        ),

        (
            "balance",
            "💰",
            "Balans",
            "/admin/balance"
        ),

        (
            "payments",
            "💳",
            "To'lovlar",
            "/admin/payments"
        ),

        (
            "vip",
            "⭐",
            "VIP",
            "/admin/vip"
        ),

        (
            "top",
            "🔝",
            "TOP",
            "/admin/top"
        ),

        (
            "up",
            "⬆️",
            "UP",
            "/admin/up"
        ),

        (
            "blocked",
            "🚫",
            "Bloklanganlar",
            "/admin/blocked"
        ),

        (
            "stats",
            "📊",
            "Statistika",
            "/admin/statistics"
        ),

        (
            "logs",
            "📜",
            "Harakatlar tarixi",
            "/admin/logs"
        ),

        (
            "settings",
            "⚙️",
            "Sozlamalar",
            "/admin/settings"
        ),
        (
            "categories",
            "📂",
            "Bo'limlar",
            "/admin/categories"
        ),
        (
            "mobile",
            "📱",
            "Mobil menyu",
            "/admin/mobile-menu"
        ),
        (
            "regs",
            "👥",
            "Ro'yxatdan o'tish",
            "/admin/registrations"
        ),
        (
            "click",
            "🟦",
            "Onlayn to'lovlar",
            "/admin/click"
        ),
        (
            "topups",
            "💳",
            "To'lov so'rovlari",
            "/admin/topups"
        ),
        (
            "payset",
            "🏦",
            "To'lov sozlamalari",
            "/admin/payment-settings"
        )

    ]

    menu_html = ""

    for key, icon, name, href in menu:

        menu_html += f"""

        <a
            class="{'active' if active == key else ''}"
            href="{href}"
        >

        <span>
        {icon}
        </span>

        {name}

        </a>

        """

    initials = "".join(
        x[:1].upper()
        for x in str(
            user["name"] if user else "A"
        ).split()
        if x
    )[:2] or "A"

    return f"""

    {ADMIN_CSS}

    <div class="admin-shell">

    <aside class="admin-sidebar">

    <div class="admin-brand">

    <img src="/uy77-logo-dark.svg" alt="Uy77" style="height:44px;width:auto;margin-right:8px">

    <div>

    <strong style="display:none">Uy77</strong>

    <span>
    ADMIN PANEL
    </span>

    </div>

    </div>

    <nav class="admin-menu">

    {menu_html}

    <a
        class="logout"
        href="/admin-logout"
    >

    🚪

    Chiqish

    </a>

    </nav>

    </aside>


    <section class="admin-content">

    <header class="admin-topbar">

    <div class="admin-top-title">
    {esc(title)}
    </div>

    <div class="admin-top-right">

    <form
        class="admin-search"
        action="/admin/search"
        method="get"
    >

    <input
        name="q"
        placeholder="Admin qidiruvi..."
    >

    </form>

    <div class="admin-user">

    <div class="admin-avatar">
    {esc(initials)}
    </div>

    <div>

    <strong
        style="
        font-size:10px;
        display:block
        "
    >
    {esc(user["name"] if user else "Admin")}
    </strong>

    <span
        style="
        color:#8795a7;
        font-size:8px
        "
    >
    Administrator
    </span>

    </div>

    </div>

    </div>

    </header>

    <main class="admin-page">

    {content}

    </main>

    </section>

    </div>

    """


def render_admin(
    content,
    title="Dashboard",
    active="dashboard"
):

    from flask import get_flashed_messages
    msgs = get_flashed_messages()
    if msgs:
        content = (
            '<div style="background:#fff8d6;border:1px solid #f2d36b;color:#5a4500;'
            'padding:12px 16px;border-radius:12px;margin-bottom:14px;font-weight:700">'
            + "<br>".join(esc(m) for m in msgs) + "</div>"
        ) + content

    return render_template_string(
        admin_layout(
            content,
            title,
            active
        )
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    if not admin_required():

        return redirect(
            "/admin-login"
        )

    cleanup_expired()

    c = db()

    total_users = c.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE is_admin=0
        """
    ).fetchone()[0]

    total_listings = c.execute(
        """
        SELECT COUNT(*)
        FROM listings
        """
    ).fetchone()[0]

    active_vip = c.execute(
        """
        SELECT COUNT(*)
        FROM listings
        WHERE vip=1
        """
    ).fetchone()[0]

    active_top = c.execute(
        """
        SELECT COUNT(*)
        FROM listings
        WHERE top=1
        """
    ).fetchone()[0]

    active_up = c.execute(
        """
        SELECT COUNT(*)
        FROM listings
        WHERE bumped_at IS NOT NULL
        AND (
            up_until IS NULL
            OR up_until > ?
        )
        """,
        (
            datetime.now().isoformat(),
        )
    ).fetchone()[0]

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    month = datetime.now().strftime(
        "%Y-%m"
    )

    today_revenue = c.execute(
        """
        SELECT COALESCE(SUM(amount),0)
        FROM payments
        WHERE status='paid'
        AND substr(created_at,1,10)=?
        """,
        (today,)
    ).fetchone()[0]

    month_revenue = c.execute(
        """
        SELECT COALESCE(SUM(amount),0)
        FROM payments
        WHERE status='paid'
        AND substr(created_at,1,7)=?
        """,
        (month,)
    ).fetchone()[0]

    total_revenue = c.execute(
        """
        SELECT COALESCE(SUM(amount),0)
        FROM payments
        WHERE status='paid'
        """
    ).fetchone()[0]

    new_users = c.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE substr(created_at,1,10)=?
        """,
        (today,)
    ).fetchone()[0]

    new_listings = c.execute(
        """
        SELECT COUNT(*)
        FROM listings
        WHERE substr(created_at,1,10)=?
        """,
        (today,)
    ).fetchone()[0]

    recent_payments = c.execute("""
        SELECT
            payments.*,
            users.phone,
            users.name,
            listings.title
        FROM payments
        JOIN users
        ON users.id=payments.user_id
        LEFT JOIN listings
        ON listings.id=payments.listing_id
        ORDER BY payments.id DESC
        LIMIT 8
    """).fetchall()

    recent_listings = c.execute("""
        SELECT
            listings.*,
            users.name owner
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        ORDER BY listings.id DESC
        LIMIT 8
    """).fetchall()

    c.close()

    payment_rows = ""

    for p in recent_payments:

        payment_rows += f"""

        <tr>

        <td>
        {esc(p["phone"])}
        </td>

        <td>
        {esc(p["service"])}
        </td>

        <td>
        {money(p["amount"])}
        </td>

        <td>
        {esc(str(p["created_at"])[:16])}
        </td>

        </tr>

        """

    listing_rows = ""

    for l in recent_listings:

        badges = ""

        if l["vip"]:
            badges += """
            <span class="admin-badge yellow">
            VIP
            </span>
            """

        if l["top"]:
            badges += """
            <span class="admin-badge blue">
            TOP
            </span>
            """

        if l["bumped_at"]:
            badges += """
            <span class="admin-badge green">
            UP
            </span>
            """

        listing_rows += f"""

        <tr>

        <td>
        #{l["id"]}
        </td>

        <td>
        {esc(l["title"])}
        </td>

        <td>
        {esc(l["owner"])}
        </td>

        <td>
        {price_of(l)}
        </td>

        <td>
        {badges or '-'}
        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    Dashboard
    </h1>

    <div class="admin-page-subtitle">
    Uy77 platformasining umumiy holati
    </div>


    <div class="admin-cards">

    <div class="admin-card">

    <div class="admin-card-head">
    Foydalanuvchilar
    <div class="admin-card-icon">
    👥
    </div>
    </div>

    <div class="admin-card-number">
    {total_users}
    </div>

    <div class="admin-card-small">
    Bugun +{new_users}
    </div>

    </div>


    <div class="admin-card">

    <div class="admin-card-head">
    E'lonlar
    <div class="admin-card-icon">
    🏡
    </div>
    </div>

    <div class="admin-card-number">
    {total_listings}
    </div>

    <div class="admin-card-small">
    Bugun +{new_listings}
    </div>

    </div>


    <div class="admin-card">

    <div class="admin-card-head">
    VIP
    <div class="admin-card-icon">
    ⭐
    </div>
    </div>

    <div class="admin-card-number">
    {active_vip}
    </div>

    <div class="admin-card-small">
    Faol VIP e'lonlar
    </div>

    </div>


    <div class="admin-card">

    <div class="admin-card-head">
    TOP
    <div class="admin-card-icon">
    🔝
    </div>
    </div>

    <div class="admin-card-number">
    {active_top}
    </div>

    <div class="admin-card-small">
    Faol TOP e'lonlar
    </div>

    </div>

    </div>


    <div class="admin-cards">

    <div class="admin-card">

    <div class="admin-card-head">
    UP
    <div class="admin-card-icon">
    ⬆️
    </div>
    </div>

    <div class="admin-card-number">
    {active_up}
    </div>

    <div class="admin-card-small">
    Faol UP
    </div>

    </div>


    <div class="admin-card">

    <div class="admin-card-head">
    Bugungi daromad
    <div class="admin-card-icon">
    💰
    </div>
    </div>

    <div class="admin-card-number">
    {money(today_revenue)}
    </div>

    </div>


    <div class="admin-card">

    <div class="admin-card-head">
    Oylik daromad
    <div class="admin-card-icon">
    📈
    </div>
    </div>

    <div class="admin-card-number">
    {money(month_revenue)}
    </div>

    </div>


    <div class="admin-card">

    <div class="admin-card-head">
    Jami daromad
    <div class="admin-card-icon">
    💳
    </div>
    </div>

    <div class="admin-card-number">
    {money(total_revenue)}
    </div>

    </div>

    </div>


    <div class="admin-grid">

    <div class="admin-panel">

    <h2 class="admin-panel-title">
    So'nggi to'lovlar
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>
    Telefon
    </th>

    <th>
    Xizmat
    </th>

    <th>
    Summa
    </th>

    <th>
    Sana
    </th>

    </tr>

    </thead>

    <tbody>

    {
        payment_rows
        or
        '<tr><td colspan="4">To\'lovlar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Xizmatlar holati
    </h2>

    <div class="admin-stat-grid">

    <div class="admin-mini-stat">
    <strong>{active_vip}</strong>
    <span>VIP</span>
    </div>

    <div class="admin-mini-stat">
    <strong>{active_top}</strong>
    <span>TOP</span>
    </div>

    <div class="admin-mini-stat">
    <strong>{active_up}</strong>
    <span>UP</span>
    </div>

    </div>

    <br>

    <a
        class="admin-btn yellow"
        href="/admin/settings"
    >
    ⚙ Narxlarni boshqarish
    </a>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    So'nggi e'lonlar
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>
    ID
    </th>

    <th>
    E'lon
    </th>

    <th>
    Egasi
    </th>

    <th>
    Narx
    </th>

    <th>
    Xizmat
    </th>

    </tr>

    </thead>

    <tbody>

    {
        listing_rows
        or
        '<tr><td colspan="5">E\'lonlar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Dashboard",
        "dashboard"
    )


# =========================================================
# ADMIN USERS
# =========================================================

@app.route("/admin/users")
def admin_users():

    if not admin_required():
        return redirect("/admin-login")

    q = request.args.get(
        "q",
        ""
    ).strip()

    c = db()

    sql = """
        SELECT
            users.*,
            (
                SELECT COUNT(*)
                FROM listings
                WHERE listings.user_id=users.id
            ) listing_count
        FROM users
        WHERE 1=1
    """

    params = []

    if q:

        sql += """
        AND (
            users.name LIKE ?
            OR users.phone LIKE ?
        )
        """

        v = f"%{q}%"

        params += [
            v,
            v
        ]

    sql += """
        ORDER BY users.id DESC
    """

    users = c.execute(
        sql,
        params
    ).fetchall()

    c.close()

    rows = ""

    for user in users:

        if user["is_admin"]:

            role = """
            <span class="admin-badge yellow">
            ADMIN
            </span>
            """

        else:

            role = """
            <span class="admin-badge blue">
            USER
            </span>
            """

        status = (
            """
            <span class="admin-badge red">
            BLOKLANGAN
            </span>
            """
            if user["blocked"]
            else
            """
            <span class="admin-badge green">
            FAOL
            </span>
            """
        )

        rows += f"""

        <tr>

        <td>
        #{user["id"]}
        </td>

        <td>
        <strong>
        {esc(user["name"])}
        </strong>
        </td>

        <td>
        {esc(user["phone"])}
        </td>

        <td>
        {money(user["balance"])}
        </td>

        <td>
        {user["listing_count"]}
        </td>

        <td>
        {esc(str(user["created_at"])[:10])}
        </td>

        <td>
        {role}
        </td>

        <td>
        {status}
        </td>

        <td>

        <div class="admin-actions">

        <a
            class="admin-btn"
            href="/admin/user/{user['id']}"
        >
        Ko'rish
        </a>

        <a
            class="admin-btn yellow"
            href="/admin/balance?user_id={user['id']}"
        >
        Balans
        </a>

        {
            (
                f'''
                <form
                    method="post"
                    action="/admin/user/{user["id"]}/unblock"
                >
                <button class="admin-btn green">
                Ochish
                </button>
                </form>
                '''
                if user["blocked"]
                else
                f'''
                <form
                    method="post"
                    action="/admin/user/{user["id"]}/block"
                >
                <button class="admin-btn red">
                Blok
                </button>
                </form>
                '''
            )
            if not user["is_admin"]
            else
            ""
        }

        {
            (
                f'''
                <form
                    method="post"
                    action="/admin/user/{user["id"]}/delete"
                    onsubmit="return confirm('Foydalanuvchini o‘chirishni tasdiqlaysizmi?')"
                >
                <button class="admin-btn red">
                O'chirish
                </button>
                </form>
                '''
            )
            if not user["is_admin"]
            else
            ""
        }

        </div>

        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    Foydalanuvchilar
    </h1>

    <div class="admin-page-subtitle">
    Barcha foydalanuvchilarni boshqarish
    </div>

    <form
        class="admin-panel"
        method="get"
        style="
        display:flex;
        gap:8px;
        margin-bottom:15px
        "
    >

    <input
        name="q"
        value="{esc(q)}"
        placeholder="Ism yoki telefon..."
    >

    <button
        class="admin-btn yellow"
        type="submit"
    >
    🔎 Qidirish
    </button>

    </form>

    <div class="admin-panel">

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>Foydalanuvchi</th>
    <th>Telefon</th>
    <th>Balans</th>
    <th>E'lonlar</th>
    <th>Ro'yxat</th>
    <th>Rol</th>
    <th>Holat</th>
    <th>Amallar</th>

    </tr>

    </thead>

    <tbody>

    {rows}

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Foydalanuvchilar",
        "users"
    )


# =========================================================
# ADMIN USER DETAIL
# =========================================================

@app.route(
    "/admin/user/<int:user_id>"
)
def admin_user_detail(user_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    user = c.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    listings_user = c.execute(
        """
        SELECT *
        FROM listings
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    payments_user = c.execute(
        """
        SELECT *
        FROM payments
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    ).fetchall()

    c.close()

    if not user:

        flash(
            "Foydalanuvchi topilmadi."
        )

        return redirect(
            "/admin/users"
        )

    listing_rows = ""

    for l in listings_user:

        listing_rows += f"""

        <tr>

        <td>
        #{l["id"]}
        </td>

        <td>
        {esc(l["title"])}
        </td>

        <td>
        {price_of(l)}
        </td>

        <td>
        {esc(l["city"])}
        </td>

        <td>

        {
            '<span class="admin-badge yellow">VIP</span>'
            if l["vip"]
            else ""
        }

        {
            '<span class="admin-badge blue">TOP</span>'
            if l["top"]
            else ""
        }

        </td>

        <td>

        <a
            class="admin-btn"
            href="/listing/{l['id']}"
            target="_blank"
        >
        Ko'rish
        </a>

        </td>

        </tr>

        """

    payment_rows = ""

    for p in payments_user:

        payment_rows += f"""

        <tr>

        <td>
        {esc(str(p["created_at"])[:16])}
        </td>

        <td>
        {esc(p["service"])}
        </td>

        <td>
        {money(p["amount"])}
        </td>

        <td>
        {esc(p["status"])}
        </td>

        </tr>

        """

    content = f"""

    <div
        style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:18px
        "
    >

    <div>

    <h1 class="admin-page-title">
    Foydalanuvchi #{user["id"]}
    </h1>

    <div class="admin-page-subtitle">
    Foydalanuvchi ma'lumotlari
    </div>

    </div>

    <a
        class="admin-btn"
        href="/admin/users"
    >
    ← Orqaga
    </a>

    </div>


    <div class="admin-grid">

    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Profil
    </h2>

    <p>
    <strong>
    Ism:
    </strong>
    {esc(user["name"])}
    </p>

    <p>
    <strong>
    Telefon:
    </strong>
    {esc(user["phone"])}
    </p>

    <p>
    <strong>
    Balans:
    </strong>
    {money(user["balance"])}
    </p>

    <p>
    <strong>
    Ro'yxatdan o'tgan:
    </strong>
    {esc(str(user["created_at"])[:16])}
    </p>

    <p>
    <strong>
    Holat:
    </strong>

    {
        '<span class="admin-badge red">BLOKLANGAN</span>'
        if user["blocked"]
        else
        '<span class="admin-badge green">FAOL</span>'
    }

    </p>

    {
        f'''
        <p>
        <strong>Blok sababi:</strong>
        {esc(user["block_reason"])}
        </p>
        '''
        if user["blocked"]
        else
        ""
    }

    <div class="admin-actions">

    <a
        class="admin-btn yellow"
        href="/admin/balance?user_id={user['id']}"
    >
    💰 Balans
    </a>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Qisqa statistika
    </h2>

    <div class="admin-stat-grid">

    <div class="admin-mini-stat">

    <strong>
    {len(listings_user)}
    </strong>

    <span>
    E'lon
    </span>

    </div>

    <div class="admin-mini-stat">

    <strong>
    {len(payments_user)}
    </strong>

    <span>
    To'lov
    </span>

    </div>

    <div class="admin-mini-stat">

    <strong>
    {money(
        sum(
            int(x["amount"] or 0)
            for x in payments_user
        )
    )}
    </strong>

    <span>
    Xarajat
    </span>

    </div>

    </div>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Foydalanuvchi e'lonlari
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>E'lon</th>
    <th>Narx</th>
    <th>Shahar</th>
    <th>Xizmat</th>
    <th></th>

    </tr>

    </thead>

    <tbody>

    {
        listing_rows
        or
        '<tr><td colspan="6">E\'lonlar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    To'lovlar
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>Sana</th>
    <th>Xizmat</th>
    <th>Summa</th>
    <th>Holat</th>

    </tr>

    </thead>

    <tbody>

    {
        payment_rows
        or
        '<tr><td colspan="4">To\'lovlar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Foydalanuvchi",
        "users"
    )


# =========================================================
# ADMIN BLOCK / UNBLOCK
# =========================================================

@app.route(
    "/admin/user/<int:user_id>/block",
    methods=["POST"]
)
def admin_block_user(user_id):

    if not admin_required():
        return redirect("/admin-login")

    reason = request.form.get(
        "reason",
        "Admin tomonidan bloklandi"
    ).strip()

    c = db()

    user = c.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if user and not user["is_admin"]:

        c.execute("""
            UPDATE users
            SET blocked=1,
                block_reason=?,
                blocked_at=?
            WHERE id=?
        """, (
            reason,
            datetime.now().isoformat(),
            user_id
        ))

        c.commit()

        admin_log(
            "USER_BLOCK",
            f"User #{user_id} bloklandi. Sabab: {reason}"
        )

    c.close()

    flash(
        "Foydalanuvchi bloklandi."
    )

    return redirect(
        "/admin/users"
    )


@app.route(
    "/admin/user/<int:user_id>/unblock",
    methods=["POST"]
)
def admin_unblock_user(user_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    c.execute("""
        UPDATE users
        SET blocked=0,
            block_reason='',
            blocked_at=NULL
        WHERE id=?
    """, (
        user_id,
    ))

    c.commit()
    c.close()

    admin_log(
        "USER_UNBLOCK",
        f"User #{user_id} blokdan chiqarildi."
    )

    flash(
        "Foydalanuvchi blokdan chiqarildi."
    )

    return redirect(
        "/admin/users"
    )


# =========================================================
# ADMIN DELETE USER
# =========================================================

@app.route(
    "/admin/user/<int:user_id>/delete",
    methods=["POST"]
)
def admin_delete_user(user_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    user = c.execute(
        "SELECT * FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    if not user:

        c.close()

        flash(
            "Foydalanuvchi topilmadi."
        )

        return redirect(
            "/admin/users"
        )

    if user["is_admin"]:

        c.close()

        flash(
            "Admin foydalanuvchini o'chirib bo'lmaydi."
        )

        return redirect(
            "/admin/users"
        )

    listings = c.execute(
        """
        SELECT image
        FROM listings
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchall()

    for l in listings:

        if l["image"]:

            path = os.path.join(
                UPLOADS,
                l["image"]
            )

            if os.path.exists(path):

                try:
                    os.remove(path)
                except:
                    pass

    c.execute(
        "DELETE FROM payments WHERE user_id=?",
        (user_id,)
    )

    c.execute(
        "DELETE FROM listings WHERE user_id=?",
        (user_id,)
    )

    c.execute(
        "DELETE FROM balance_history WHERE user_id=?",
        (user_id,)
    )

    c.execute(
        "DELETE FROM users WHERE id=?",
        (user_id,)
    )

    c.commit()
    c.close()

    admin_log(
        "USER_DELETE",
        f"User #{user_id} o'chirildi."
    )

    flash(
        "Foydalanuvchi o'chirildi."
    )

    return redirect(
        "/admin/users"
    )


# =========================================================
# ADMIN BALANCE
# =========================================================

@app.route(
    "/admin/balance",
    methods=["GET", "POST"]
)
def admin_balance():

    if not admin_required():
        return redirect("/admin-login")

    if request.method == "POST":

        phone = clean_phone(
            request.form.get(
                "phone",
                ""
            )
        )

        amount_raw = request.form.get(
            "amount",
            "0"
        )

        operation = request.form.get(
            "operation",
            "add"
        )

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        try:

            amount = abs(
                int(amount_raw)
            )

        except:

            amount = 0

        if amount <= 0:

            flash(
                "Summa noto'g'ri."
            )

            return redirect(
                "/admin/balance"
            )

        c = db()

        user = c.execute(
            """
            SELECT *
            FROM users
            WHERE phone=?
            """,
            (phone,)
        ).fetchone()

        if not user:

            c.close()

            flash(
                "Foydalanuvchi topilmadi."
            )

            return redirect(
                "/admin/balance"
            )

        old_balance = int(
            user["balance"] or 0
        )

        if operation == "subtract":

            if old_balance < amount:

                c.close()

                flash(
                    "Foydalanuvchi balansida yetarli mablag' yo'q."
                )

                return redirect(
                    "/admin/balance"
                )

            change = -amount

        else:

            change = amount

        new_balance = (
            old_balance +
            change
        )

        c.execute(
            """
            UPDATE users
            SET balance=?
            WHERE id=?
            """,
            (
                new_balance,
                user["id"]
            )
        )

        c.execute(
            """
            INSERT INTO balance_history
            (
                user_id,
                admin_id,
                amount,
                old_balance,
                new_balance,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                current_user()["id"],
                change,
                old_balance,
                new_balance,
                reason
            )
        )

        c.commit()
        c.close()

        admin_log(
            "BALANCE_CHANGE",
            f"User #{user['id']}: "
            f"{old_balance} -> {new_balance}. "
            f"Sabab: {reason}"
        )

        flash(
            f"{phone} balans yangilandi: "
            f"{money(new_balance)}"
        )

        return redirect(
            "/admin/balance"
        )

    c = db()

    history = c.execute("""
        SELECT
            balance_history.*,
            users.phone,
            users.name
        FROM balance_history
        JOIN users
        ON users.id=balance_history.user_id
        ORDER BY balance_history.id DESC
        LIMIT 50
    """).fetchall()

    c.close()

    rows = ""

    for h in history:

        cls = (
            "green"
            if h["amount"] >= 0
            else
            "red"
        )

        sign = (
            "+"
            if h["amount"] >= 0
            else
            ""
        )

        rows += f"""

        <tr>

        <td>
        {esc(h["phone"])}
        </td>

        <td>
        {sign}{money(h["amount"])}
        </td>

        <td>
        {money(h["old_balance"])}
        </td>

        <td>
        {money(h["new_balance"])}
        </td>

        <td>
        {esc(h["reason"] or "-")}
        </td>

        <td>
        {esc(str(h["created_at"])[:16])}
        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    Balans
    </h1>

    <div class="admin-page-subtitle">
    Foydalanuvchi balansini qo'shish yoki ayirish
    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Balansni o'zgartirish
    </h2>

    <form
        method="post"
        class="admin-form-grid"
    >

    <div class="admin-form-group">

    <label>
    Telefon
    </label>

    <input
        name="phone"
        placeholder="998901234567"
        required
    >

    </div>

    <div class="admin-form-group">

    <label>
    Summa
    </label>

    <input
        name="amount"
        type="number"
        min="1"
        placeholder="100000"
        required
    >

    </div>

    <div class="admin-form-group">

    <label>
    Amal
    </label>

    <select name="operation">

    <option value="add">
    ➕ Balans qo'shish
    </option>

    <option value="subtract">
    ➖ Balans ayirish
    </option>

    </select>

    </div>

    <div class="admin-form-group">

    <label>
    Sabab
    </label>

    <input
        name="reason"
        placeholder="Masalan: To'lov / bonus / tuzatish"
    >

    </div>

    <div>

    <button
        class="admin-btn yellow"
        type="submit"
    >
    💰 Saqlash
    </button>

    </div>

    </form>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Balans o'zgarishlari tarixi
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>
    Foydalanuvchi
    </th>

    <th>
    O'zgarish
    </th>

    <th>
    Eski
    </th>

    <th>
    Yangi
    </th>

    <th>
    Sabab
    </th>

    <th>
    Sana
    </th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="6">Tarix yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Balans",
        "balance"
    )


# =========================================================
# ADMIN PAYMENTS
# =========================================================

@app.route("/admin/payments")
def admin_payments():

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    payments = c.execute("""
        SELECT
            payments.*,
            users.name,
            users.phone,
            listings.title
        FROM payments
        JOIN users
        ON users.id=payments.user_id
        LEFT JOIN listings
        ON listings.id=payments.listing_id
        ORDER BY payments.id DESC
        LIMIT 200
    """).fetchall()

    c.close()

    rows = ""

    for p in payments:

        rows += f"""

        <tr>

        <td>
        #{p["id"]}
        </td>

        <td>
        {esc(p["name"])}
        </td>

        <td>
        {esc(p["phone"])}
        </td>

        <td>
        {esc(p["service"])}
        </td>

        <td>
        {esc(p["title"] or "-")}
        </td>

        <td>
        {money(p["amount"])}
        </td>

        <td>
        <span class="admin-badge green">
        {esc(p["status"])}
        </span>
        </td>

        <td>
        {esc(str(p["created_at"])[:16])}
        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    To'lovlar
    </h1>

    <div class="admin-page-subtitle">
    Barcha xizmat to'lovlari
    </div>

    <div class="admin-panel">

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>Foydalanuvchi</th>
    <th>Telefon</th>
    <th>Xizmat</th>
    <th>E'lon</th>
    <th>Summa</th>
    <th>Status</th>
    <th>Sana</th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="8">To\'lovlar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "To'lovlar",
        "payments"
    )


# =========================================================
# ADMIN LISTINGS
# =========================================================

@app.route("/admin/listings")
def admin_listings():

    if not admin_required():
        return redirect("/admin-login")

    q = request.args.get(
        "q",
        ""
    ).strip()

    c = db()

    sql = """
        SELECT
            listings.*,
            users.name owner,
            users.phone owner_phone
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE 1=1
    """

    params = []

    if q:

        sql += """
        AND (
            listings.title LIKE ?
            OR users.name LIKE ?
            OR users.phone LIKE ?
            OR listings.address LIKE ?
        )
        """

        v = f"%{q}%"

        params += [
            v,
            v,
            v,
            v
        ]

    sql += """
        ORDER BY
        listings.id DESC
    """

    rows_data = c.execute(
        sql,
        params
    ).fetchall()

    c.close()

    rows = ""

    for row in rows_data:

        services = ""

        if row["vip"]:
            services += """
            <span class="admin-badge yellow">
            VIP
            </span>
            """

        if row["top"]:
            services += """
            <span class="admin-badge blue">
            TOP
            </span>
            """

        if row["bumped_at"]:
            services += """
            <span class="admin-badge green">
            UP
            </span>
            """

        if row["hidden"]:
            services += """
            <span class="admin-badge red">
            YASHIRILGAN
            </span>
            """

        image = (
            f"""
            <img
                src="/uploads/{esc(row['image'])}"
                style="
                width:45px;
                height:38px;
                object-fit:cover;
                border-radius:7px
                "
            >
            """
            if row["image"]
            else
            "🏠"
        )

        rows += f"""

        <tr>

        <td>
        #{row["id"]}
        </td>

        <td>
        {image}
        </td>

        <td>
        <strong>
        {esc(row["title"])}
        </strong>
        </td>

        <td>
        {esc(row["owner"])}
        </td>

        <td>
        {price_of(row)}
        </td>

        <td>
        {esc(row["city"])}
        {", " + esc(row["district"]) if row["district"] else ""}
        </td>

        <td>
        {esc(row["property_type"])}
        </td>

        <td>
        {row["rooms"]}
        </td>

        <td>
        {services or "-"}
        </td>

        <td>

        <div class="admin-actions">

        <a
            class="admin-btn"
            href="/listing/{row['id']}"
            target="_blank"
        >
        Ko'rish
        </a>

        <form
            method="post"
            action="/admin/listing/{row['id']}/vip"
        >
        <button class="admin-btn yellow">
        VIP
        </button>
        </form>

        <form
            method="post"
            action="/admin/listing/{row['id']}/top"
        >
        <button class="admin-btn yellow">
        TOP
        </button>
        </form>

        <form
            method="post"
            action="/admin/listing/{row['id']}/up"
        >
        <button class="admin-btn green">
        UP
        </button>
        </form>

        <form
            method="post"
            action="/admin/listing/{row['id']}/toggle"
        >
        <button class="admin-btn">
        {
            "Ko'rsatish"
            if row["hidden"]
            else
            "Yashirish"
        }
        </button>
        </form>

        <form
            method="post"
            action="/admin/listing/{row['id']}/delete"
            onsubmit="return confirm('E’lon o‘chirilsinmi?')"
        >
        <button class="admin-btn red">
        O'chirish
        </button>
        </form>

        </div>

        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    E'lonlar
    </h1>

    <div class="admin-page-subtitle">
    Barcha e'lonlarni boshqarish
    </div>

    <form
        class="admin-panel"
        method="get"
        style="
        display:flex;
        gap:8px;
        margin-bottom:15px
        "
    >

    <input
        name="q"
        value="{esc(q)}"
        placeholder="E'lon, egasi, telefon yoki manzil..."
    >

    <button
        class="admin-btn yellow"
        type="submit"
    >
    🔎 Qidirish
    </button>

    </form>

    <div class="admin-panel">

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>Rasm</th>
    <th>E'lon</th>
    <th>Egasi</th>
    <th>Narx</th>
    <th>Manzil</th>
    <th>Turi</th>
    <th>Xona</th>
    <th>Xizmatlar</th>
    <th>Amallar</th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="10">E\'lonlar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "E'lonlar",
        "listings"
    )


# =========================================================
# ADMIN LISTING SERVICES
# =========================================================

def admin_listing_service(
    listing_id,
    service
):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    listing = c.execute(
        "SELECT * FROM listings WHERE id=?",
        (listing_id,)
    ).fetchone()

    if not listing:

        c.close()

        flash(
            "E'lon topilmadi."
        )

        return redirect(
            "/admin/listings"
        )

    now = datetime.now()

    if service == "vip":

        until = now + timedelta(
            days=7
        )

        c.execute(
            """
            UPDATE listings
            SET vip=1,
                vip_until=?
            WHERE id=?
            """,
            (
                until.isoformat(),
                listing_id
            )
        )

        action = "ADMIN_VIP"
        details = f"E'lon #{listing_id} VIP qilindi."

    elif service == "top":

        until = now + timedelta(
            days=7
        )

        c.execute(
            """
            UPDATE listings
            SET top=1,
                top_until=?
            WHERE id=?
            """,
            (
                until.isoformat(),
                listing_id
            )
        )

        action = "ADMIN_TOP"
        details = f"E'lon #{listing_id} TOP qilindi."

    else:

        until = now + timedelta(
            hours=24
        )

        c.execute(
            """
            UPDATE listings
            SET bumped_at=?,
                up_until=?
            WHERE id=?
            """,
            (
                now.isoformat(),
                until.isoformat(),
                listing_id
            )
        )

        action = "ADMIN_UP"
        details = f"E'lon #{listing_id} UP qilindi."

    c.commit()
    c.close()

    admin_log(
        action,
        details
    )

    flash(
        "Xizmat faollashtirildi."
    )

    return redirect(
        "/admin/listings"
    )


@app.route(
    "/admin/listing/<int:listing_id>/vip",
    methods=["POST"]
)
def admin_listing_vip(listing_id):

    return admin_listing_service(
        listing_id,
        "vip"
    )


@app.route(
    "/admin/listing/<int:listing_id>/top",
    methods=["POST"]
)
def admin_listing_top(listing_id):

    return admin_listing_service(
        listing_id,
        "top"
    )


@app.route(
    "/admin/listing/<int:listing_id>/up",
    methods=["POST"]
)
def admin_listing_up(listing_id):

    return admin_listing_service(
        listing_id,
        "up"
    )


# =========================================================
# ADMIN HIDE / SHOW LISTING
# =========================================================

@app.route(
    "/admin/listing/<int:listing_id>/toggle",
    methods=["POST"]
)
def admin_listing_toggle(listing_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    row = c.execute(
        "SELECT hidden FROM listings WHERE id=?",
        (listing_id,)
    ).fetchone()

    if row:

        new_value = (
            0
            if row["hidden"]
            else 1
        )

        c.execute(
            """
            UPDATE listings
            SET hidden=?
            WHERE id=?
            """,
            (
                new_value,
                listing_id
            )
        )

        c.commit()

        admin_log(
            "LISTING_VISIBILITY",
            f"E'lon #{listing_id}: hidden={new_value}"
        )

    c.close()

    return redirect(
        "/admin/listings"
    )


# =========================================================
# ADMIN DELETE LISTING
# =========================================================

@app.route(
    "/admin/listing/<int:listing_id>/delete",
    methods=["POST"]
)
def admin_listing_delete(listing_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    row = c.execute(
        "SELECT * FROM listings WHERE id=?",
        (listing_id,)
    ).fetchone()

    if not row:

        c.close()

        flash(
            "E'lon topilmadi."
        )

        return redirect(
            "/admin/listings"
        )

    if row["image"]:

        path = os.path.join(
            UPLOADS,
            row["image"]
        )

        if os.path.exists(path):

            try:
                os.remove(path)
            except:
                pass

    c.execute(
        "DELETE FROM payments WHERE listing_id=?",
        (listing_id,)
    )

    c.execute(
        "DELETE FROM listings WHERE id=?",
        (listing_id,)
    )

    c.commit()
    c.close()

    admin_log(
        "LISTING_DELETE",
        f"E'lon #{listing_id} o'chirildi."
    )

    flash(
        "E'lon o'chirildi."
    )

    return redirect(
        "/admin/listings"
    )


# =========================================================
# ADMIN VIP
# =========================================================

@app.route("/admin/vip")
def admin_vip():

    if not admin_required():
        return redirect("/admin-login")

    cleanup_expired()

    c = db()

    rows_data = c.execute("""
        SELECT
            listings.*,
            users.name owner,
            users.phone owner_phone
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE listings.vip=1
        ORDER BY listings.vip_until ASC
    """).fetchall()

    c.close()

    rows = ""

    for row in rows_data:

        rows += f"""

        <tr>

        <td>
        #{row["id"]}
        </td>

        <td>
        {esc(row["title"])}
        </td>

        <td>
        {esc(row["owner"])}
        </td>

        <td>
        {esc(row["owner_phone"])}
        </td>

        <td>
        {price_of(row)}
        </td>

        <td>
        {esc(str(row["vip_until"])[:16])}
        </td>

        <td>

        <form
            method="post"
            action="/admin/vip/{row['id']}/cancel"
        >

        <button
            class="admin-btn red"
        >
        Bekor qilish
        </button>

        </form>

        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    ⭐ VIP
    </h1>

    <div class="admin-page-subtitle">
    Faol VIP e'lonlar va tugash sanalari
    </div>

    <div class="admin-panel">

    <div
        style="
        margin-bottom:15px;
        font-size:12px
        "
    >
    Joriy VIP narxi:
    <strong>
    {money(get_setting("vip_price", VIP_PRICE))}
    </strong>
    </div>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>E'lon</th>
    <th>Egasi</th>
    <th>Telefon</th>
    <th>Narx</th>
    <th>Tugash</th>
    <th></th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="7">Faol VIP yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "VIP",
        "vip"
    )


@app.route(
    "/admin/vip/<int:listing_id>/cancel",
    methods=["POST"]
)
def admin_vip_cancel(listing_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    c.execute(
        """
        UPDATE listings
        SET vip=0,
            vip_until=NULL
        WHERE id=?
        """,
        (listing_id,)
    )

    c.commit()
    c.close()

    admin_log(
        "VIP_CANCEL",
        f"E'lon #{listing_id} VIP bekor qilindi."
    )

    return redirect(
        "/admin/vip"
    )


# =========================================================
# ADMIN TOP
# =========================================================

@app.route("/admin/top")
def admin_top():

    if not admin_required():
        return redirect("/admin-login")

    cleanup_expired()

    c = db()

    rows_data = c.execute("""
        SELECT
            listings.*,
            users.name owner,
            users.phone owner_phone
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE listings.top=1
        ORDER BY listings.top_until ASC
    """).fetchall()

    c.close()

    rows = ""

    for row in rows_data:

        rows += f"""

        <tr>

        <td>
        #{row["id"]}
        </td>

        <td>
        {esc(row["title"])}
        </td>

        <td>
        {esc(row["owner"])}
        </td>

        <td>
        {esc(row["owner_phone"])}
        </td>

        <td>
        {price_of(row)}
        </td>

        <td>
        {esc(str(row["top_until"])[:16])}
        </td>

        <td>

        <form
            method="post"
            action="/admin/top/{row['id']}/cancel"
        >

        <button
            class="admin-btn red"
        >
        Bekor qilish
        </button>

        </form>

        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    🔝 TOP
    </h1>

    <div class="admin-page-subtitle">
    Faol TOP e'lonlar
    </div>

    <div class="admin-panel">

    <div
        style="
        margin-bottom:15px;
        font-size:12px
        "
    >
    Joriy TOP narxi:
    <strong>
    {money(get_setting("top_price", TOP_PRICE))}
    </strong>
    </div>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>E'lon</th>
    <th>Egasi</th>
    <th>Telefon</th>
    <th>Narx</th>
    <th>Tugash</th>
    <th></th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="7">Faol TOP yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "TOP",
        "top"
    )


@app.route(
    "/admin/top/<int:listing_id>/cancel",
    methods=["POST"]
)
def admin_top_cancel(listing_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    c.execute(
        """
        UPDATE listings
        SET top=0,
            top_until=NULL
        WHERE id=?
        """,
        (listing_id,)
    )

    c.commit()
    c.close()

    admin_log(
        "TOP_CANCEL",
        f"E'lon #{listing_id} TOP bekor qilindi."
    )

    return redirect(
        "/admin/top"
    )


# =========================================================
# ADMIN UP
# =========================================================

@app.route("/admin/up")
def admin_up():

    if not admin_required():
        return redirect("/admin-login")

    cleanup_expired()

    c = db()

    rows_data = c.execute("""
        SELECT
            listings.*,
            users.name owner,
            users.phone owner_phone
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE listings.bumped_at IS NOT NULL
        AND (
            listings.up_until IS NULL
            OR listings.up_until > ?
        )
        ORDER BY listings.bumped_at DESC
    """, (
        datetime.now().isoformat(),
    )).fetchall()

    c.close()

    rows = ""

    for row in rows_data:

        rows += f"""

        <tr>

        <td>
        #{row["id"]}
        </td>

        <td>
        {esc(row["title"])}
        </td>

        <td>
        {esc(row["owner"])}
        </td>

        <td>
        {esc(row["owner_phone"])}
        </td>

        <td>
        {esc(str(row["bumped_at"])[:16])}
        </td>

        <td>
        {esc(str(row["up_until"])[:16])}
        </td>

        <td>

        <form
            method="post"
            action="/admin/up/{row['id']}/cancel"
        >

        <button
            class="admin-btn red"
        >
        Bekor qilish
        </button>

        </form>

        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    ⬆️ UP
    </h1>

    <div class="admin-page-subtitle">
    Tepaga ko'tarilgan e'lonlar
    </div>

    <div class="admin-panel">

    <div
        style="
        margin-bottom:15px;
        font-size:12px
        "
    >
    Joriy UP narxi:
    <strong>
    {money(get_setting("up_price", UP_PRICE))}
    </strong>
    </div>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>E'lon</th>
    <th>Egasi</th>
    <th>Telefon</th>
    <th>Ko'tarilgan</th>
    <th>Tugash</th>
    <th></th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="7">Faol UP yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "UP",
        "up"
    )


@app.route(
    "/admin/up/<int:listing_id>/cancel",
    methods=["POST"]
)
def admin_up_cancel(listing_id):

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    c.execute(
        """
        UPDATE listings
        SET bumped_at=NULL,
            up_until=NULL
        WHERE id=?
        """,
        (listing_id,)
    )

    c.commit()
    c.close()

    admin_log(
        "UP_CANCEL",
        f"E'lon #{listing_id} UP bekor qilindi."
    )

    return redirect(
        "/admin/up"
    )


# =========================================================
# ADMIN BLOCKED
# =========================================================

@app.route("/admin/blocked")
def admin_blocked():

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    users = c.execute("""
        SELECT *
        FROM users
        WHERE blocked=1
        ORDER BY blocked_at DESC
    """).fetchall()

    c.close()

    rows = ""

    for user in users:

        rows += f"""

        <tr>

        <td>
        #{user["id"]}
        </td>

        <td>
        {esc(user["name"])}
        </td>

        <td>
        {esc(user["phone"])}
        </td>

        <td>
        {esc(user["block_reason"] or "-")}
        </td>

        <td>
        {esc(str(user["blocked_at"] or "")[:16])}
        </td>

        <td>

        <form
            method="post"
            action="/admin/user/{user['id']}/unblock"
        >

        <button class="admin-btn green">
        Ochish
        </button>

        </form>

        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    🚫 Bloklanganlar
    </h1>

    <div class="admin-page-subtitle">
    Bloklangan foydalanuvchilar
    </div>

    <div class="admin-panel">

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>Ism</th>
    <th>Telefon</th>
    <th>Sabab</th>
    <th>Sana</th>
    <th></th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="6">Bloklangan foydalanuvchilar yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Bloklanganlar",
        "blocked"
    )


# =========================================================
# ADMIN STATISTICS
# =========================================================

@app.route("/admin/statistics")
def admin_statistics():

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    daily_users = c.execute("""
        SELECT
            substr(created_at,1,10) day,
            COUNT(*) count
        FROM users
        WHERE is_admin=0
        GROUP BY substr(created_at,1,10)
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()

    monthly_users = c.execute("""
        SELECT
            substr(created_at,1,7) month,
            COUNT(*) count
        FROM users
        WHERE is_admin=0
        GROUP BY substr(created_at,1,7)
        ORDER BY month DESC
        LIMIT 12
    """).fetchall()

    listing_growth = c.execute("""
        SELECT
            substr(created_at,1,10) day,
            COUNT(*) count
        FROM listings
        GROUP BY substr(created_at,1,10)
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()

    service_stats = c.execute("""
        SELECT
            service,
            COUNT(*) count,
            COALESCE(SUM(amount),0) revenue
        FROM payments
        WHERE status='paid'
        GROUP BY service
    """).fetchall()

    c.close()

    max_users = max(
        [x["count"] for x in daily_users] or [1]
    )

    bars = ""

    for x in reversed(
        daily_users
    ):

        height = max(
            5,
            int(
                x["count"] /
                max_users *
                100
            )
        )

        bars += f"""

        <div
            class="admin-bar"
            style="height:{height}%"
        >

        <span>
        {esc(x["day"][-5:])}
        </span>

        </div>

        """

    service_cards = ""

    for s in service_stats:

        service_cards += f"""

        <div class="admin-mini-stat">

        <strong>
        {s["count"]}
        </strong>

        <span>
        {esc(s["service"])}
        — {money(s["revenue"])}
        </span>

        </div>

        """

    listing_total = sum(
        int(x["count"])
        for x in listing_growth
    )

    user_total = sum(
        int(x["count"])
        for x in monthly_users
    )

    content = f"""

    <h1 class="admin-page-title">
    📊 Statistika
    </h1>

    <div class="admin-page-subtitle">
    Foydalanuvchilar, e'lonlar va daromadlar statistikasi
    </div>


    <div class="admin-stat-grid">

    <div class="admin-mini-stat">

    <strong>
    {user_total}
    </strong>

    <span>
    So'nggi davr foydalanuvchilari
    </span>

    </div>

    <div class="admin-mini-stat">

    <strong>
    {listing_total}
    </strong>

    <span>
    So'nggi e'lonlar
    </span>

    </div>

    <div class="admin-mini-stat">

    <strong>
    {len(service_stats)}
    </strong>

    <span>
    Xizmat turlari
    </span>

    </div>

    </div>

    <br>


    <div class="admin-grid">

    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Kundalik foydalanuvchilar
    </h2>

    <div class="admin-chart">

    {bars}

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Xizmatlar
    </h2>

    <div class="admin-stat-grid">

    {
        service_cards
        or
        '<div class="admin-empty">Ma\'lumot yo\'q.</div>'
    }

    </div>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Oylik foydalanuvchilar
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>
    <th>Oy</th>
    <th>Yangi foydalanuvchilar</th>
    </tr>

    </thead>

    <tbody>

    {
        ''.join(
            f'''
            <tr>
            <td>{esc(x["month"])}</td>
            <td>{x["count"]}</td>
            </tr>
            '''
            for x in monthly_users
        )
        or
        '<tr><td colspan="2">Ma\'lumot yo\'q.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Statistika",
        "stats"
    )


# =========================================================
# ADMIN LOGS
# =========================================================

@app.route("/admin/logs")
def admin_logs():

    if not admin_required():
        return redirect("/admin-login")

    c = db()

    logs = c.execute("""
        SELECT
            admin_logs.*,
            users.name admin_name
        FROM admin_logs
        LEFT JOIN users
        ON users.id=admin_logs.admin_id
        ORDER BY admin_logs.id DESC
        LIMIT 300
    """).fetchall()

    c.close()

    rows = ""

    for log in logs:

        rows += f"""

        <tr>

        <td>
        #{log["id"]}
        </td>

        <td>
        {esc(log["admin_name"] or "Admin")}
        </td>

        <td>
        {esc(log["action"])}
        </td>

        <td>
        {esc(log["details"])}
        </td>

        <td>
        {esc(str(log["created_at"])[:16])}
        </td>

        </tr>

        """

    content = f"""

    <h1 class="admin-page-title">
    📜 Harakatlar tarixi
    </h1>

    <div class="admin-page-subtitle">
    Admin tomonidan bajarilgan o'zgarishlar
    </div>

    <div class="admin-panel">

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>

    <th>ID</th>
    <th>Admin</th>
    <th>Amal</th>
    <th>Tafsilot</th>
    <th>Sana</th>

    </tr>

    </thead>

    <tbody>

    {
        rows
        or
        '<tr><td colspan="5">Tarix hali bo\'sh.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Harakatlar tarixi",
        "logs"
    )





# =========================================================
# BALANSNI TO'LDIRISH (karta orqali, admin tasdiqlaydi)
# =========================================================

RECEIPTS = os.path.join(UPLOADS, "receipts")
os.makedirs(RECEIPTS, exist_ok=True)

TOPUP_STATUS = {
    "pending": ("Kutilmoqda", "yellow"),
    "approved": ("Tasdiqlandi", "green"),
    "rejected": ("Rad etildi", "red"),
}


def pay_settings():
    def num(key, default):
        try:
            return int(get_setting_text(key, str(default)) or default)
        except Exception:
            return default

    return {
        "card": get_setting_text("pay_card", ""),
        "owner": get_setting_text("pay_owner", ""),
        "note": get_setting_text("pay_note", ""),
        "min": num("pay_min", 5000),
        "max": num("pay_max", 10000000),
    }


def format_card(card):
    digits = re.sub(r"\D", "", card or "")
    return " ".join(digits[i:i + 4] for i in range(0, len(digits), 4))


@app.route("/receipt/<name>")
def receipt_file(name):
    """Chek rasmi: faqat egasi va admin ko'ra oladi."""
    user = current_user()
    if not user:
        return redirect("/login")
    name = secure_filename(name)
    c = db()
    row = c.execute(
        "SELECT user_id FROM topup_requests WHERE receipt=?", (name,)
    ).fetchone()
    c.close()
    if not row or not (user["is_admin"] or row["user_id"] == user["id"]):
        return "Topilmadi", 404
    return send_from_directory(RECEIPTS, name)


@app.route("/balance/topup", methods=["GET", "POST"])
def balance_topup():

    if not login_required():
        return redirect("/login")

    user = current_user()
    ps = pay_settings()

    if request.method == "POST":
        if not ps["card"]:
            flash("To'lov usuli hali sozlanmagan. Keyinroq urinib ko'ring.")
            return redirect("/balance/topup")

        try:
            amount = int(re.sub(r"\D", "", request.form.get("amount", "")) or 0)
        except Exception:
            amount = 0

        if amount < ps["min"] or amount > ps["max"]:
            flash(f"Summa {money(ps['min'])} dan {money(ps['max'])} gacha bo'lishi kerak.")
            return redirect("/balance/topup")

        file = request.files.get("receipt")
        if not file or not file.filename:
            flash("To'lov chekining rasmini yuklang.")
            return redirect("/balance/topup")

        c = db()
        pending = c.execute(
            "SELECT COUNT(*) FROM topup_requests WHERE user_id=? AND status='pending'",
            (user["id"],)
        ).fetchone()[0]
        if pending >= 3:
            c.close()
            flash("Sizda 3 ta kutilayotgan so'rov bor. Tasdiqlanishini kuting.")
            return redirect("/balance/topup")

        try:
            name = save_uploaded_image(file)
            os.replace(os.path.join(UPLOADS, name), os.path.join(RECEIPTS, name))
        except Exception:
            c.close()
            flash("Rasm formati noto'g'ri. JPG yoki PNG yuklang.")
            return redirect("/balance/topup")

        c.execute(
            "INSERT INTO topup_requests(user_id, amount, receipt) VALUES(?,?,?)",
            (user["id"], amount, name)
        )
        c.commit()
        c.close()
        flash("So'rov yuborildi. Admin tekshirib, balansingizni to'ldiradi.")
        return redirect("/balance/topup")

    c = db()
    mine = c.execute(
        "SELECT * FROM topup_requests WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (user["id"],)
    ).fetchall()
    c.close()

    rows = ""
    for r in mine:
        label, color = TOPUP_STATUS.get(r["status"], (r["status"], "blue"))
        note = f'<div class="kc-meta">{esc(r["admin_note"])}</div>' if r["admin_note"] else ""
        rows += f"""
        <div class="kd-box" style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:10px">
          <div><b>{esc(money(r["amount"]))}</b>
          <div class="kc-meta">{esc(str(r["created_at"])[:16])}</div>{note}</div>
          <span class="kc-tags"><span>{esc(label)}</span></span>
        </div>"""
    if not rows:
        rows = '<div class="kc-empty">Hozircha so\'rovlar yo\'q.</div>'

    if ps["card"]:
        pay_box = f"""
        <div class="kd-box">
          <div class="kc-meta">Pulni shu kartaga o'tkazing</div>
          <div style="font-size:26px;font-weight:800;letter-spacing:1px;margin:6px 0" id="card-num">{esc(format_card(ps["card"]))}</div>
          <div style="color:var(--muted)">{esc(ps["owner"])}</div>
          <button type="button" class="kd-btn ghost" style="border:0;width:100%;margin-top:12px;cursor:pointer"
            onclick="navigator.clipboard.writeText('{esc(re.sub(r"\D", "", ps["card"]))}');this.textContent='Nusxalandi ✓'">📋 Karta raqamini nusxalash</button>
          {f'<p style="color:var(--muted);font-size:13px;margin:10px 0 0">{esc(ps["note"])}</p>' if ps["note"] else ""}
        </div>"""
    else:
        pay_box = '<div class="kc-empty">To\'lov usuli hali sozlanmagan.</div>'

    ck = click_cfg()
    if ck["ready"]:
        click_box = f"""
      <form method="post" action="/balance/click" class="kd-box">
        <b>Click orqali to'lash</b>
        <div class="kc-meta" style="margin:4px 0 10px">To'lov darrov balansga tushadi</div>
        <input name="amount" inputmode="numeric" placeholder="Summa (so'm), masalan: 50000" required style="width:100%;padding:12px;border:1px solid var(--line);border-radius:12px;margin-bottom:10px">
        <button class="kd-btn" style="border:0;width:100%;cursor:pointer">Click orqali to'lash</button>
      </form>
      <div class="kc-meta" style="text-align:center;margin:6px 0 12px">yoki kartaga o'tkazib, chek yuboring</div>"""
    else:
        click_box = ""

    content = f"""
    <div class="kd-wrap" style="max-width:640px">
      <a class="kd-back" href="/profile">← Orqaga</a>
      <h1 style="margin:0 0 4px">Balansni to'ldirish</h1>
      <p style="color:var(--muted);margin:0 0 16px">Joriy balans: <b>{esc(money(user["balance"]))}</b></p>
      {click_box}

      <div class="kd-box"><b>Qanday to'lanadi?</b>
        <ol style="margin:8px 0 0;padding-left:20px;color:var(--muted);line-height:1.7">
          <li>Pulni quyidagi kartaga bank ilovasi orqali o'tkazing.</li>
          <li>To'lov chekining rasmini va summani pastdagi formaga kiriting.</li>
          <li>Admin tekshiradi va balansingiz to'ldiriladi.</li>
        </ol>
      </div>

      {pay_box}

      <form method="post" enctype="multipart/form-data" class="kd-box">
        <label><b>O'tkazgan summa (so'm)</b></label>
        <input name="amount" inputmode="numeric" placeholder="Masalan: 50000" required style="width:100%;padding:12px;border:1px solid var(--line);border-radius:12px;margin:6px 0 12px">
        <label><b>Chek rasmi (skrinshot)</b></label>
        <input type="file" name="receipt" accept="image/*" required style="width:100%;margin:6px 0 14px">
        <button class="kd-btn" style="border:0;width:100%;cursor:pointer">Yuborish</button>
      </form>

      <h3>So'rovlarim</h3>
      {rows}
    </div>
    """
    return render_page(content, "Balansni to'ldirish")


# ---------------- ADMIN: to'lov so'rovlari ----------------

@app.route("/admin/topups")
def admin_topups():
    if not admin_required():
        return redirect("/admin-login")

    status = request.args.get("status", "pending")
    if status not in TOPUP_STATUS:
        status = "pending"

    c = db()
    rows = c.execute(
        """
        SELECT topup_requests.*, users.name uname, users.phone uphone, users.balance ubalance
        FROM topup_requests JOIN users ON users.id=topup_requests.user_id
        WHERE topup_requests.status=?
        ORDER BY topup_requests.id DESC LIMIT 200
        """, (status,)
    ).fetchall()
    counts = {k: c.execute("SELECT COUNT(*) FROM topup_requests WHERE status=?", (k,)).fetchone()[0] for k in TOPUP_STATUS}
    c.close()

    tabs = "".join(
        f'<a class="admin-btn {"yellow" if k == status else "dark"}" href="/admin/topups?status={k}">{TOPUP_STATUS[k][0]} ({counts[k]})</a> '
        for k in TOPUP_STATUS
    )

    body = ""
    for r in rows:
        if r["status"] == "pending":
            actions = f"""
            <form method="post" action="/admin/topups/{r['id']}/approve" style="display:flex;gap:6px;align-items:center;margin-bottom:6px">
              <input name="amount" value="{r['amount']}" style="width:110px">
              <button class="admin-btn green">✔ Tasdiqlash</button>
            </form>
            <form method="post" action="/admin/topups/{r['id']}/reject" style="display:flex;gap:6px;align-items:center">
              <input name="note" placeholder="Sabab" style="width:110px">
              <button class="admin-btn red">✖ Rad etish</button>
            </form>"""
        else:
            actions = esc(r["admin_note"] or "")
        label, color = TOPUP_STATUS[r["status"]]
        body += f"""
        <tr>
          <td>#{r['id']}</td>
          <td>{esc(r['uname'])}<br><small>{esc(r['uphone'])}</small></td>
          <td><b>{esc(money(r['amount']))}</b><br><small>Balans: {esc(money(r['ubalance']))}</small></td>
          <td><a href="/receipt/{esc(r['receipt'])}" target="_blank"><img src="/receipt/{esc(r['receipt'])}" style="width:90px;height:90px;object-fit:cover;border-radius:10px"></a></td>
          <td>{esc(str(r['created_at'])[:16])}</td>
          <td><span class="admin-badge {color}">{label}</span></td>
          <td>{actions}</td>
        </tr>"""
    if not body:
        body = '<tr><td colspan="7">So\'rovlar yo\'q.</td></tr>'

    content = f"""
    <h1 class="admin-page-title">💳 To'lov so'rovlari</h1>
    <div class="admin-page-subtitle">Mijozlar yuborgan cheklarni tekshiring. Pul kartangizga tushganini ko'rgach tasdiqlang.</div>
    <div style="margin-bottom:14px">{tabs}</div>
    <div class="admin-panel"><div class="admin-table-wrap"><table class="admin-table">
      <thead><tr><th>ID</th><th>Foydalanuvchi</th><th>Summa</th><th>Chek</th><th>Vaqt</th><th>Holat</th><th>Amal</th></tr></thead>
      <tbody>{body}</tbody></table></div></div>
    """
    return render_admin(content, "To'lov so'rovlari", "topups")


@app.route("/admin/topups/<int:rid>/approve", methods=["POST"])
def admin_topup_approve(rid):
    if not admin_required():
        return redirect("/admin-login")
    try:
        amount = int(re.sub(r"\D", "", request.form.get("amount", "")) or 0)
    except Exception:
        amount = 0
    if amount <= 0 or amount > 100000000:
        flash("Summa noto'g'ri.")
        return redirect("/admin/topups")

    admin = current_user()
    c = db()
    # Bir so'rovni ikki marta tasdiqlashdan himoya: faqat 'pending' bo'lsa o'tadi
    cur = c.execute(
        "UPDATE topup_requests SET status='approved', amount=?, reviewed_by=?, reviewed_at=? WHERE id=? AND status='pending'",
        (amount, admin["id"], datetime.now().isoformat(timespec="seconds"), rid)
    )
    if cur.rowcount != 1:
        c.rollback(); c.close()
        flash("Bu so'rov allaqachon ko'rib chiqilgan.")
        return redirect("/admin/topups")

    req = c.execute("SELECT user_id FROM topup_requests WHERE id=?", (rid,)).fetchone()
    u = c.execute("SELECT balance FROM users WHERE id=?", (req["user_id"],)).fetchone()
    old = int(u["balance"] or 0)
    new = old + amount
    c.execute("UPDATE users SET balance=? WHERE id=?", (new, req["user_id"]))
    c.execute(
        "INSERT INTO balance_history(user_id, admin_id, amount, old_balance, new_balance, reason) VALUES (?,?,?,?,?,?)",
        (req["user_id"], admin["id"], amount, old, new, f"Karta orqali to'lov #{rid}")
    )
    admin_log("TOPUP_APPROVE", f"So'rov #{rid}: user #{req['user_id']} +{amount}", conn=c)
    c.commit(); c.close()
    flash(f"Tasdiqlandi: +{money(amount)}")
    return redirect("/admin/topups")


@app.route("/admin/topups/<int:rid>/reject", methods=["POST"])
def admin_topup_reject(rid):
    if not admin_required():
        return redirect("/admin-login")
    note = request.form.get("note", "").strip()[:200] or "Rad etildi"
    admin = current_user()
    c = db()
    cur = c.execute(
        "UPDATE topup_requests SET status='rejected', admin_note=?, reviewed_by=?, reviewed_at=? WHERE id=? AND status='pending'",
        (note, admin["id"], datetime.now().isoformat(timespec="seconds"), rid)
    )
    if cur.rowcount == 1:
        admin_log("TOPUP_REJECT", f"So'rov #{rid}: {note}", conn=c)
        flash("Rad etildi.")
    else:
        flash("Bu so'rov allaqachon ko'rib chiqilgan.")
    c.commit(); c.close()
    return redirect("/admin/topups")


@app.route("/admin/payment-settings", methods=["GET", "POST"])
def admin_payment_settings():
    if not admin_required():
        return redirect("/admin-login")

    if request.method == "POST":
        card = re.sub(r"\D", "", request.form.get("card", ""))
        if card and len(card) != 16:
            flash("Karta raqami 16 ta raqam bo'lishi kerak.")
            return redirect("/admin/payment-settings")
        c = db()
        set_setting_text("pay_card", card, conn=c)
        set_setting_text("pay_owner", request.form.get("owner", "").strip()[:60], conn=c)
        set_setting_text("pay_note", request.form.get("note", "").strip()[:300], conn=c)
        for k in ("pay_min", "pay_max"):
            v = re.sub(r"\D", "", request.form.get(k, ""))
            if v:
                set_setting_text(k, v, conn=c)
        admin_log("PAYMENT_SETTINGS", "To'lov sozlamalari yangilandi", conn=c)
        c.commit(); c.close()
        flash("Saqlandi.")
        return redirect("/admin/payment-settings")

    ps = pay_settings()
    content = f"""
    <h1 class="admin-page-title">🏦 To'lov sozlamalari</h1>
    <div class="admin-page-subtitle">Mijozlarga ko'rsatiladigan karta ma'lumotlari</div>
    <div class="admin-panel">
      <form method="post">
        <div class="admin-form-grid">
          <div class="admin-form-group"><label>Karta raqami (16 xona)</label>
            <input name="card" value="{esc(format_card(ps['card']))}" placeholder="8600 0000 0000 0000" inputmode="numeric"></div>
          <div class="admin-form-group"><label>Karta egasi</label>
            <input name="owner" value="{esc(ps['owner'])}" placeholder="ISM FAMILIYA"></div>
          <div class="admin-form-group"><label>Eng kam summa (so'm)</label>
            <input name="pay_min" value="{ps['min']}"></div>
          <div class="admin-form-group"><label>Eng ko'p summa (so'm)</label>
            <input name="pay_max" value="{ps['max']}"></div>
        </div>
        <div class="admin-form-group"><label>Qo'shimcha izoh (mijozga ko'rinadi)</label>
          <input name="note" value="{esc(ps['note'])}" placeholder="Masalan: To'lovdan keyin chekni yuklang"></div>
        <p style="color:#8090a3;font-size:13px">Faqat 16 xonali karta raqamini yozing. Amal qilish muddati va CVV kodni hech qachon kiritmang.</p>
        <button class="admin-btn yellow" type="submit">💾 Saqlash</button>
      </form>
    </div>
    """
    return render_admin(content, "To'lov sozlamalari", "payset")



# =========================================================
# CLICK MERCHANT (avtomatik to'lov)  —  Shop API: Prepare / Complete
# =========================================================
# Sozlamalar serverdagi muhit o'zgaruvchilarida (kodga yozilmaydi):
#   CLICK_MERCHANT_ID, CLICK_SERVICE_ID, CLICK_SECRET_KEY,
#   CLICK_MERCHANT_USER_ID, SITE_URL (masalan https://uy77.uz)

import hashlib


def click_cfg():
    cfg = {
        "merchant_id": os.environ.get("CLICK_MERCHANT_ID", "").strip(),
        "service_id": os.environ.get("CLICK_SERVICE_ID", "").strip(),
        "secret": os.environ.get("CLICK_SECRET_KEY", "").strip(),
        "merchant_user_id": os.environ.get("CLICK_MERCHANT_USER_ID", "").strip(),
        "site": os.environ.get("SITE_URL", "").strip().rstrip("/"),
    }
    cfg["enabled"] = os.environ.get("CLICK_ENABLED", "0").strip() == "1"
    cfg["ready"] = cfg["enabled"] and all(cfg[k] for k in ("merchant_id", "service_id", "secret", "site"))
    return cfg


def _md5(*parts):
    return hashlib.md5("".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def _click_amount(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def _click_resp(base, error=0, note="Success", **extra):
    out = dict(base)
    out.update(extra)
    out["error"] = error
    out["error_note"] = note
    return jsonify(out)


def _click_check(form, action_expected, cfg, complete):
    """Imzo, service_id va action tekshiruvi. (xato_kodi, matn) yoki None."""
    f = form.get
    if f("service_id", "") != cfg["service_id"]:
        return -8, "Error in request from click"
    if complete:
        expected = _md5(f("click_trans_id", ""), f("service_id", ""), cfg["secret"],
                        f("merchant_trans_id", ""), f("merchant_prepare_id", ""),
                        f("amount", ""), f("action", ""), f("sign_time", ""))
    else:
        expected = _md5(f("click_trans_id", ""), f("service_id", ""), cfg["secret"],
                        f("merchant_trans_id", ""), f("amount", ""),
                        f("action", ""), f("sign_time", ""))
    import hmac
    if not hmac.compare_digest(expected, (f("sign_string", "") or "").lower()):
        return -1, "SIGN CHECK FAILED!"
    if f("action", "") != action_expected:
        return -3, "Action not found"
    return None



# ---------------------------------------------------------
# Xizmatni (VIP / TOP / UP) to'lovdan keyin avtomatik yoqish
# ---------------------------------------------------------

def promo_apply(c, listing_id, service, now=None):
    now = now or datetime.now()
    if service == "vip":
        c.execute("UPDATE listings SET vip=1, vip_until=? WHERE id=?",
                  ((now + timedelta(days=7)).isoformat(), listing_id))
    elif service == "top":
        c.execute("UPDATE listings SET top=1, top_until=? WHERE id=?",
                  ((now + timedelta(days=7)).isoformat(), listing_id))
    elif service == "up":
        c.execute("UPDATE listings SET bumped_at=?, up_until=? WHERE id=?",
                  (now.isoformat(), (now + timedelta(hours=24)).isoformat(), listing_id))
    else:
        raise ValueError("noto'g'ri xizmat")


def listing_from_draft(c, user_id, draft, service):
    now = datetime.now()
    vip_value = 1 if service == "vip" else 0
    top_value = 1 if service == "top" else 0
    vip_until = (now + timedelta(days=7)).isoformat() if service == "vip" else None
    top_until = (now + timedelta(days=7)).isoformat() if service == "top" else None
    c.execute(
        """
        INSERT INTO listings
        (user_id, title, description, price, property_type, deal_type, mortgage, city, district,
         address, rooms, area, image, images, latitude, longitude, category_id, listing_kind,
         brand, model, production_year, body_type, mileage, fuel_type, transmission,
         engine_volume, color, currency, condition, contact_phone,
         vip, top, vip_until, top_until, hidden)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """,
        (
            user_id, draft["title"], draft["description"], draft["price"],
            draft["property_type"], draft["deal_type"], draft["mortgage"],
            draft["city"], draft["district"], draft["address"], draft["rooms"], draft["area"],
            draft["image"], json.dumps(draft.get("images", [draft["image"]]), ensure_ascii=False),
            draft["latitude"], draft["longitude"], draft["category_id"],
            draft.get("listing_kind", "real_estate"), draft.get("brand", ""), draft.get("model", ""),
            draft.get("production_year"), draft.get("body_type", ""), draft.get("mileage", 0),
            draft.get("fuel_type", ""), draft.get("transmission", ""), draft.get("engine_volume", ""),
            draft.get("color", ""), draft.get("currency", "USD"), draft.get("condition", ""),
            draft.get("contact_phone", ""), vip_value, top_value, vip_until, top_until,
        )
    )
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def _click_fulfill(c, order):
    """To'langan Click buyurtmasini bajaradi: e'lon/xizmat yoki balans."""
    oid, uid, amount = order["id"], order["user_id"], int(order["amount"])
    purpose = order["purpose"] or "balance"

    if purpose in ("new_listing", "service"):
        c.execute("SAVEPOINT fulfill")
        try:
            if purpose == "new_listing":
                lid = listing_from_draft(c, uid, json.loads(order["draft"]), order["service"])
            else:
                lid = order["listing_id"]
                row = c.execute("SELECT user_id FROM listings WHERE id=?", (lid,)).fetchone()
                if not row or row["user_id"] != uid:
                    raise ValueError("e'lon topilmadi")
                promo_apply(c, lid, order["service"])
            c.execute(
                "INSERT INTO payments(user_id, listing_id, service, amount, status) VALUES (?,?,?,?,?)",
                (uid, lid, order["service"].upper(), amount, "paid")
            )
            c.execute("UPDATE click_orders SET listing_id=? WHERE id=?", (lid, oid))
            c.execute("RELEASE SAVEPOINT fulfill")
            return
        except Exception as e:
            c.execute("ROLLBACK TO SAVEPOINT fulfill")
            c.execute("RELEASE SAVEPOINT fulfill")
            c.execute("UPDATE click_orders SET error_note=? WHERE id=?",
                      (f"Xizmat yoqilmadi, pul balansga qaytarildi: {e}"[:200], oid))
            reason = f"Click to'lovi #{oid}: xizmat yoqilmadi, balansga qaytarildi"
    else:
        reason = f"Click orqali to'lov #{oid}"

    u = c.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()
    old = int(u["balance"] or 0)
    new = old + amount
    c.execute("UPDATE users SET balance=? WHERE id=?", (new, uid))
    c.execute(
        "INSERT INTO balance_history(user_id, admin_id, amount, old_balance, new_balance, reason) VALUES (?,?,?,?,?,?)",
        (uid, None, amount, old, new, reason)
    )


def payme_cfg():
    cfg = {
        "merchant_id": os.environ.get("PAYME_MERCHANT_ID", "").strip(),
        "key": os.environ.get("PAYME_KEY", "").strip(),
        "site": os.environ.get("SITE_URL", "").strip().rstrip("/"),
        "test": os.environ.get("PAYME_TEST", "0").strip() == "1",
        "enabled": os.environ.get("PAYME_ENABLED", "0").strip() == "1",
    }
    cfg["ready"] = cfg["enabled"] and all(cfg[k] for k in ("merchant_id", "key", "site"))
    return cfg


def demo_pay_on():
    """SINOV rejimi: haqiqiy pul yechilmaydi. Serverda DEMO_PAY=1 bo'lsa yoki admin paneldan yoqilsa ishlaydi."""
    if os.environ.get("DEMO_PAY", "0").strip() == "1":
        return True
    try:
        return get_setting_text("demo_pay", "0") == "1"
    except Exception:
        return False


def pay_providers():
    out = []
    if click_cfg()["ready"]:
        out.append("click")
    if payme_cfg()["ready"]:
        out.append("payme")
    if demo_pay_on():
        out.append("demo")
    return out


def pay_any_ready():
    return bool(pay_providers())


def click_checkout_url(oid, amount):
    cfg = click_cfg()
    params = {
        "service_id": cfg["service_id"],
        "merchant_id": cfg["merchant_id"],
        "amount": amount,
        "transaction_param": oid,
        "return_url": f"{cfg['site']}/pay/result?order={oid}",
    }
    if cfg["merchant_user_id"]:
        params["merchant_user_id"] = cfg["merchant_user_id"]
    return "https://my.click.uz/services/pay?" + urlencode(params)


def payme_checkout_url(oid, amount):
    import base64
    cfg = payme_cfg()
    raw = (
        f"m={cfg['merchant_id']};ac.order_id={oid};a={int(amount) * 100};"
        f"c={cfg['site']}/pay/result?order={oid};l=uz"
    )
    host = "https://test.paycom.uz/" if cfg["test"] else "https://checkout.paycom.uz/"
    return host + base64.b64encode(raw.encode("utf-8")).decode("ascii")


def click_order_redirect(user_id, amount, purpose, service="", listing_id=None, draft=None):
    """Buyurtma yaratadi. Bitta usul yoqilgan bo'lsa to'g'ri o'sha sahifaga,
    ikkalasi yoqilgan bo'lsa usul tanlash sahifasiga yo'naltiradi."""
    c = db()
    cur = c.execute(
        "INSERT INTO click_orders(user_id, amount, purpose, service, listing_id, draft) VALUES (?,?,?,?,?,?)",
        (user_id, amount, purpose, service, listing_id,
         json.dumps(draft, ensure_ascii=False) if draft else None)
    )
    oid = cur.lastrowid
    c.commit()
    c.close()
    providers = pay_providers()
    if len(providers) == 1:
        return pay_go(oid, amount, providers[0])
    return redirect(f"/pay/method/{oid}")


def pay_go(oid, amount, provider):
    c = db()
    c.execute("UPDATE click_orders SET provider=? WHERE id=? AND status IN ('new','prepared')", (provider, oid))
    c.commit()
    c.close()
    if provider == "demo":
        return redirect(f"/pay/demo/{oid}")
    if provider == "payme":
        return redirect(payme_checkout_url(oid, amount))
    return redirect(click_checkout_url(oid, amount))


SERVICE_TITLES = {"vip": "👑 VIP", "top": "🔥 TOP", "up": "🚀 Tepaga ko'tarish"}


@app.route("/pay/method/<int:oid>")
def pay_method(oid):
    if not login_required():
        return redirect("/login")
    c = db()
    order = c.execute(
        "SELECT * FROM click_orders WHERE id=? AND user_id=?", (oid, session["user_id"])
    ).fetchone()
    c.close()
    if not order or order["status"] not in ("new", "prepared"):
        return redirect("/profile")
    providers = pay_providers()
    if not providers:
        flash("Karta orqali to'lash hozircha mavjud emas.")
        return redirect("/add/payment")

    btn = {
        "click": '<button class="pm-btn pm-click" name="provider" value="click">Click orqali to\'lash</button>',
        "payme": '<button class="pm-btn pm-payme" name="provider" value="payme">Payme orqali to\'lash</button>',
        "demo": '<button class="pm-btn pm-demo" name="provider" value="demo">🧪 Sinov to\'lovi (pul yechilmaydi)</button>',
    }
    buttons = "".join(btn[p] for p in providers)
    title = SERVICE_TITLES.get(order["service"], order["service"] or "To'lov")
    back = "/add/payment" if order["purpose"] == "new_listing" else "/profile"

    content = f"""
    <style>
      .pm-btn{{display:block;width:100%;border:0;border-radius:14px;padding:15px;font-weight:800;font-size:16px;cursor:pointer;margin-top:10px}}
      .pm-click{{background:#378ADD;color:#fff}}
      .pm-payme{{background:#1D9E75;color:#fff}}
      .pm-demo{{background:#EF9F27;color:#412402}}
    </style>
    <div class="kd-wrap" style="max-width:480px">
      <a class="kd-back" href="{back}">← Orqaga</a>
      <h1 style="margin:0 0 14px">To'lovni tasdiqlash</h1>
      <div class="kd-box">
        <div class="kc-meta">Xizmat</div>
        <div style="font-weight:800;font-size:18px">{esc(title)}</div>
        <div class="kc-meta" style="margin-top:12px">Summa</div>
        <div style="font-weight:800;font-size:26px">{esc(money(order["amount"]))} <span title="Summani o'zgartirib bo'lmaydi">🔒</span></div>
      </div>
      <form method="post" action="/pay/start/{oid}" class="kd-box">
        <div style="font-weight:800">To'lov usulini tanlang</div>
        {buttons}
        <p style="color:var(--muted);font-size:12px;margin:12px 0 0">
          Karta ma'lumotlari va SMS parolni tanlangan to'lov tizimining xavfsiz sahifasida kiritasiz.
          Biz karta raqamingizni ko'rmaymiz va saqlamaymiz.
        </p>
      </form>
    </div>
    """
    return render_page(content, "To'lov usuli")


@app.route("/pay/start/<int:oid>", methods=["POST"])
def pay_start(oid):
    if not login_required():
        return redirect("/login")
    provider = request.form.get("provider", "")
    if provider not in pay_providers():
        flash("Bu to'lov usuli hozircha mavjud emas.")
        return redirect(f"/pay/method/{oid}")
    c = db()
    order = c.execute(
        "SELECT * FROM click_orders WHERE id=? AND user_id=? AND status IN ('new','prepared')",
        (oid, session["user_id"])
    ).fetchone()
    c.close()
    if not order:
        return redirect("/profile")
    return pay_go(oid, int(order["amount"]), provider)


@app.route("/pay/click/listing", methods=["POST"])
def pay_click_listing():
    if not login_required():
        return redirect("/login")
    if not pay_any_ready():
        flash("Karta orqali to'lash hozircha mavjud emas.")
        return redirect("/add/payment")
    draft = session.get("new_listing_draft")
    if not draft:
        flash("E'lon ma'lumotlari topilmadi.")
        return redirect("/post-ad")
    prices = service_prices()
    service = draft.get("service", "free")
    if service not in prices or int(prices[service]) <= 0:
        return redirect("/add/payment")
    return click_order_redirect(
        session["user_id"], int(prices[service]), "new_listing", service, None, draft
    )


@app.route("/pay/result")
def pay_result():
    if not login_required():
        return redirect("/login")
    try:
        oid = int(request.args.get("order", "0"))
    except Exception:
        oid = 0
    try:
        tries = int(request.args.get("n", "0"))
    except Exception:
        tries = 0
    c = db()
    order = c.execute(
        "SELECT * FROM click_orders WHERE id=? AND user_id=?", (oid, session["user_id"])
    ).fetchone()
    c.close()
    if not order:
        return redirect("/profile")

    if order["status"] == "paid":
        if (order["purpose"] or "balance") == "new_listing":
            session.pop("new_listing_draft", None)
        if order["listing_id"] and not order["error_note"]:
            flash("To'lov qabul qilindi. Xizmat avtomatik yoqildi!")
            return redirect(f"/listing/{order['listing_id']}")
        if order["error_note"]:
            flash("To'lov qabul qilindi, lekin xizmatni yoqib bo'lmadi. Pul balansingizga qaytarildi.")
        else:
            flash("To'lov qabul qilindi. Balansingiz to'ldirildi!")
        return redirect("/profile")

    if order["status"] == "cancelled":
        flash("To'lov bekor qilindi. Pul yechilmadi.")
        return redirect("/add/payment" if (order["purpose"] or "") == "new_listing" else "/profile")

    if tries >= 20:
        content = """
        <div class="form-card" style="max-width:520px;margin:30px auto;text-align:center">
          <h2>To'lov hali tasdiqlanmadi</h2>
          <p style="color:var(--muted)">Agar pul kartangizdan yechilgan bo'lsa, bir necha daqiqada
          xizmat avtomatik yoqiladi. Profilingizni tekshiring.</p>
          <a class="post-btn" href="/profile">Profilga o'tish</a>
        </div>"""
        return render_page(content, "To'lov")

    content = f"""
    <meta http-equiv="refresh" content="3;url=/pay/result?order={order['id']}&n={tries + 1}">
    <div class="form-card" style="max-width:520px;margin:30px auto;text-align:center">
      <div style="font-size:44px">⏳</div>
      <h2>To'lov tekshirilmoqda...</h2>
      <p style="color:var(--muted)">Iltimos, sahifani yopmang. Tasdiqlangach xizmat avtomatik yoqiladi.</p>
    </div>"""
    return render_page(content, "To'lov")



# =========================================================
# PAYME MERCHANT API (JSON-RPC)  —  /payme
# =========================================================
# Muhit o'zgaruvchilari: PAYME_ENABLED=1, PAYME_MERCHANT_ID, PAYME_KEY,
# SITE_URL, (sinov uchun) PAYME_TEST=1

PAYME_TIMEOUT_MS = 12 * 60 * 60 * 1000


def _pm_now():
    return int(datetime.now().timestamp() * 1000)


def _pm_ok(rid, result):
    return jsonify({"jsonrpc": "2.0", "id": rid, "result": result})


def _pm_err(rid, code, ru, uz, en, data=None):
    return jsonify({
        "jsonrpc": "2.0", "id": rid,
        "error": {"code": code, "message": {"ru": ru, "uz": uz, "en": en}, "data": data}
    })


def _pm_auth_ok(cfg):
    import base64
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        login, _, password = base64.b64decode(header[6:]).decode("utf-8").partition(":")
    except Exception:
        return False
    return hmac.compare_digest(login, "Paycom") and hmac.compare_digest(password, cfg["key"])


def _pm_tx_view(tx):
    return {
        "create_time": tx["create_time"],
        "perform_time": tx["perform_time"] or 0,
        "cancel_time": tx["cancel_time"] or 0,
        "transaction": str(tx["id"]),
        "state": tx["state"],
        "reason": tx["reason"],
    }


def _pm_check_order(c, rid, params):
    """(order, xato_javobi). Hisob va summani tekshiradi."""
    account = params.get("account") or {}
    try:
        oid = int(account.get("order_id"))
    except Exception:
        return None, _pm_err(rid, -31050, "Заказ не найден", "Buyurtma topilmadi", "Order not found", "order_id")
    order = c.execute("SELECT * FROM click_orders WHERE id=?", (oid,)).fetchone()
    if not order:
        return None, _pm_err(rid, -31050, "Заказ не найден", "Buyurtma topilmadi", "Order not found", "order_id")
    try:
        amount = int(params.get("amount"))
    except Exception:
        amount = -1
    if amount != int(order["amount"]) * 100:
        return None, _pm_err(rid, -31001, "Неверная сумма", "Noto'g'ri summa", "Wrong amount")
    if order["status"] == "paid":
        return None, _pm_err(rid, -31051, "Заказ уже оплачен", "Buyurtma allaqachon to'langan", "Order already paid", "order_id")
    if order["status"] == "cancelled":
        return None, _pm_err(rid, -31052, "Заказ отменён", "Buyurtma bekor qilingan", "Order cancelled", "order_id")
    return order, None


def _pm_expire(c, tx):
    c.execute(
        "UPDATE payme_transactions SET state=-1, cancel_time=?, reason=4 WHERE id=? AND state=1",
        (_pm_now(), tx["id"])
    )


@app.route("/payme", methods=["POST"])
def payme_endpoint():
    cfg = payme_cfg()
    data = request.get_json(silent=True) or {}
    rid = data.get("id")
    method = data.get("method")
    params = data.get("params") or {}

    if not cfg["ready"] or not _pm_auth_ok(cfg):
        return _pm_err(rid, -32504, "Недостаточно привилегий", "Ruxsat yo'q", "Insufficient privilege")
    if not method:
        return _pm_err(rid, -32600, "Неверный запрос", "Noto'g'ri so'rov", "Invalid request")

    c = db()
    try:
        if method == "CheckPerformTransaction":
            order, err = _pm_check_order(c, rid, params)
            return err or _pm_ok(rid, {"allow": True})

        if method == "CreateTransaction":
            pid = str(params.get("id", ""))
            tx = c.execute("SELECT * FROM payme_transactions WHERE payme_id=?", (pid,)).fetchone()
            if tx:
                if tx["state"] != 1:
                    return _pm_err(rid, -31008, "Невозможно выполнить операцию", "Amalni bajarib bo'lmaydi", "Cannot perform")
                if _pm_now() - tx["create_time"] > PAYME_TIMEOUT_MS:
                    _pm_expire(c, tx)
                    c.commit()
                    return _pm_err(rid, -31008, "Время истекло", "Vaqt tugadi", "Timed out")
                return _pm_ok(rid, {"create_time": tx["create_time"], "transaction": str(tx["id"]), "state": 1})

            order, err = _pm_check_order(c, rid, params)
            if err:
                return err
            other = c.execute(
                "SELECT id FROM payme_transactions WHERE order_id=? AND state=1", (order["id"],)
            ).fetchone()
            if other:
                return _pm_err(rid, -31099, "Заказ ожидает оплаты", "Buyurtma to'lovni kutmoqda",
                               "Order has another active transaction", "order_id")
            now = _pm_now()
            cur = c.execute(
                "INSERT INTO payme_transactions(payme_id, payme_time, order_id, amount, state, create_time) VALUES (?,?,?,?,1,?)",
                (pid, params.get("time"), order["id"], int(params.get("amount")), now)
            )
            c.execute("UPDATE click_orders SET status='prepared', provider='payme' WHERE id=? AND status='new'", (order["id"],))
            c.commit()
            return _pm_ok(rid, {"create_time": now, "transaction": str(cur.lastrowid), "state": 1})

        if method == "PerformTransaction":
            tx = c.execute("SELECT * FROM payme_transactions WHERE payme_id=?", (str(params.get("id", "")),)).fetchone()
            if not tx:
                return _pm_err(rid, -31003, "Транзакция не найдена", "Tranzaksiya topilmadi", "Transaction not found")
            if tx["state"] == 2:
                return _pm_ok(rid, {"transaction": str(tx["id"]), "perform_time": tx["perform_time"], "state": 2})
            if tx["state"] != 1:
                return _pm_err(rid, -31008, "Невозможно выполнить операцию", "Amalni bajarib bo'lmaydi", "Cannot perform")
            if _pm_now() - tx["create_time"] > PAYME_TIMEOUT_MS:
                _pm_expire(c, tx)
                c.commit()
                return _pm_err(rid, -31008, "Время истекло", "Vaqt tugadi", "Timed out")

            now = _pm_now()
            cur = c.execute(
                "UPDATE payme_transactions SET state=2, perform_time=? WHERE id=? AND state=1", (now, tx["id"])
            )
            if cur.rowcount != 1:
                c.rollback()
                return _pm_err(rid, -31008, "Невозможно выполнить операцию", "Amalni bajarib bo'lmaydi", "Cannot perform")
            order = c.execute("SELECT * FROM click_orders WHERE id=?", (tx["order_id"],)).fetchone()
            cur = c.execute(
                "UPDATE click_orders SET status='paid', paid_at=?, provider='payme' WHERE id=? AND status!='paid'",
                (datetime.now().isoformat(timespec="seconds"), tx["order_id"])
            )
            if cur.rowcount == 1:
                _click_fulfill(c, order)
            c.commit()
            return _pm_ok(rid, {"transaction": str(tx["id"]), "perform_time": now, "state": 2})

        if method == "CancelTransaction":
            tx = c.execute("SELECT * FROM payme_transactions WHERE payme_id=?", (str(params.get("id", "")),)).fetchone()
            if not tx:
                return _pm_err(rid, -31003, "Транзакция не найдена", "Tranzaksiya topilmadi", "Transaction not found")
            if tx["state"] == 1:
                now = _pm_now()
                c.execute(
                    "UPDATE payme_transactions SET state=-1, cancel_time=?, reason=? WHERE id=? AND state=1",
                    (now, params.get("reason"), tx["id"])
                )
                c.execute("UPDATE click_orders SET status='new' WHERE id=? AND status='prepared'", (tx["order_id"],))
                c.commit()
                return _pm_ok(rid, {"transaction": str(tx["id"]), "cancel_time": now, "state": -1})
            if tx["state"] == 2:
                # Xizmat allaqachon yoqilgan: avtomatik qaytarib bo'lmaydi
                return _pm_err(rid, -31007, "Заказ выполнен. Невозможно отменить транзакцию",
                               "Buyurtma bajarilgan. Tranzaksiyani bekor qilib bo'lmaydi",
                               "Order completed. Cannot cancel")
            return _pm_ok(rid, {"transaction": str(tx["id"]), "cancel_time": tx["cancel_time"], "state": tx["state"]})

        if method == "CheckTransaction":
            tx = c.execute("SELECT * FROM payme_transactions WHERE payme_id=?", (str(params.get("id", "")),)).fetchone()
            if not tx:
                return _pm_err(rid, -31003, "Транзакция не найдена", "Tranzaksiya topilmadi", "Transaction not found")
            return _pm_ok(rid, _pm_tx_view(tx))

        if method == "GetStatement":
            try:
                t_from, t_to = int(params.get("from")), int(params.get("to"))
            except Exception:
                return _pm_err(rid, -32600, "Неверный запрос", "Noto'g'ri so'rov", "Invalid request")
            rows = c.execute(
                "SELECT * FROM payme_transactions WHERE create_time BETWEEN ? AND ? ORDER BY create_time",
                (t_from, t_to)
            ).fetchall()
            return _pm_ok(rid, {"transactions": [
                {
                    "id": r["payme_id"], "time": r["payme_time"], "amount": r["amount"],
                    "account": {"order_id": str(r["order_id"])},
                    "create_time": r["create_time"], "perform_time": r["perform_time"] or 0,
                    "cancel_time": r["cancel_time"] or 0, "transaction": str(r["id"]),
                    "state": r["state"], "reason": r["reason"],
                } for r in rows
            ]})

        return _pm_err(rid, -32601, "Метод не найден", "Metod topilmadi", "Method not found", method)
    finally:
        c.close()



# =========================================================
# SINOV TO'LOV OYNASI (DEMO_PAY=1) — haqiqiy pul yechilmaydi
# =========================================================
# Faqat jarayonni ko'rish va sinash uchun. Haqiqiy saytda DEMO_PAY ni YOQMANG,
# aks holda har kim bepul VIP/TOP olishi mumkin.

DEMO_SMS_CODE = "123456"


def _demo_order(oid):
    if not demo_pay_on() or not login_required():
        return None
    c = db()
    order = c.execute(
        "SELECT * FROM click_orders WHERE id=? AND user_id=?", (oid, session["user_id"])
    ).fetchone()
    c.close()
    return order


@app.route("/pay/demo/<int:oid>", methods=["GET", "POST"])
def pay_demo(oid):
    if not demo_pay_on():
        return "Topilmadi", 404
    if not login_required():
        return redirect("/login")
    order = _demo_order(oid)
    if not order or order["status"] not in ("new", "prepared"):
        return redirect("/profile")

    step = request.form.get("step", "card")
    title = SERVICE_TITLES.get(order["service"], order["service"] or "To'lov")
    amount_txt = esc(money(order["amount"]))
    error = ""

    if request.method == "POST" and step == "card":
        card = re.sub(r"\D", "", request.form.get("card", ""))
        exp = request.form.get("exp", "").strip()
        if len(card) != 16:
            error = "Karta raqami 16 ta raqam bo'lishi kerak."
        elif not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", exp):
            error = "Amal qilish muddatini OO/YY ko'rinishida yozing (masalan 12/28)."
        else:
            step = "sms"      # karta raqami saqlanmaydi
        if error:
            step = "card"

    elif request.method == "POST" and step == "sms":
        if request.form.get("code", "").strip() != DEMO_SMS_CODE:
            error = "SMS parol noto'g'ri."
        else:
            now = datetime.now().isoformat(timespec="seconds")
            c = db()
            cur = c.execute(
                "UPDATE click_orders SET status='paid', paid_at=?, provider='demo' WHERE id=? AND status IN ('new','prepared')",
                (now, oid)
            )
            if cur.rowcount == 1:
                fresh = c.execute("SELECT * FROM click_orders WHERE id=?", (oid,)).fetchone()
                _click_fulfill(c, fresh)
            c.commit()
            c.close()
            return redirect(f"/pay/result?order={oid}")

    err_html = f'<div style="background:#fff0f0;color:#b3261e;padding:10px 12px;border-radius:10px;margin-bottom:10px;font-weight:700">{esc(error)}</div>' if error else ""
    banner = '<div style="background:#fff3cd;border:1px solid #f2d36b;color:#664d03;padding:8px 12px;border-radius:10px;font-size:13px;font-weight:700;text-align:center;margin-bottom:12px">🧪 SINOV REJIMI — haqiqiy pul yechilmaydi</div>'

    if step == "sms":
        body = f"""
        <p style="color:var(--muted);margin:0 0 12px">Telefoningizga SMS parol yuborildi.<br>
        <b>Sinov kodi: {DEMO_SMS_CODE}</b></p>
        <form method="post">
          <input type="hidden" name="step" value="sms">
          <input name="code" inputmode="numeric" maxlength="6" placeholder="••••••" autofocus required
                 style="width:100%;text-align:center;font-size:28px;letter-spacing:10px;font-weight:800;padding:12px;border:1px solid var(--line);border-radius:12px;margin-bottom:12px">
          <button class="pm-btn pm-click" style="margin-top:0">Tasdiqlash</button>
        </form>
        <p style="text-align:center;color:var(--muted);font-size:12px;margin:12px 0 0">Kartadan {amount_txt} yechiladi</p>"""
    else:
        body = f"""
        <form method="post">
          <input type="hidden" name="step" value="card">
          <label class="kc-meta">Karta raqami</label>
          <input name="card" inputmode="numeric" maxlength="19" placeholder="8600 0000 0000 0000" autofocus required
                 style="width:100%;font-size:18px;padding:12px;border:1px solid var(--line);border-radius:12px;margin:4px 0 12px">
          <label class="kc-meta">Amal qilish muddati</label>
          <input name="exp" maxlength="5" placeholder="OO/YY" required
                 style="width:100%;font-size:18px;padding:12px;border:1px solid var(--line);border-radius:12px;margin:4px 0 12px">
          <button class="pm-btn pm-click" style="margin-top:0">To'lash</button>
        </form>"""

    content = f"""
    <style>
      .pm-btn{{display:block;width:100%;border:0;border-radius:14px;padding:15px;font-weight:800;font-size:16px;cursor:pointer}}
      .pm-click{{background:#378ADD;color:#fff}}
    </style>
    <div class="kd-wrap" style="max-width:440px">
      {banner}
      <div class="kd-box">
        <div style="text-align:center;font-weight:900;font-size:22px;color:#378ADD;margin-bottom:4px">to'lov</div>
        <div style="text-align:center;color:var(--muted);font-size:13px">Uy77 · {esc(title)}</div>
        <div class="kc-meta" style="margin-top:12px">Summa</div>
        <div style="font-weight:800;font-size:26px;margin-bottom:14px">{amount_txt} 🔒</div>
        {err_html}
        {body}
      </div>
      <a href="/pay/method/{oid}" style="display:block;text-align:center;color:var(--muted);font-size:13px">← To'lov usulini o'zgartirish</a>
    </div>
    """
    return render_page(content, "To'lov (sinov)")


@app.route("/click/prepare", methods=["POST"])
def click_prepare():
    cfg = click_cfg()
    f = request.form.get
    base = {
        "click_trans_id": f("click_trans_id", ""),
        "merchant_trans_id": f("merchant_trans_id", ""),
        "merchant_prepare_id": f("merchant_trans_id", ""),
    }
    if not cfg["ready"]:
        return _click_resp(base, -8, "Error in request from click")

    bad = _click_check(request.form, "0", cfg, complete=False)
    if bad:
        return _click_resp(base, *bad)

    try:
        oid = int(f("merchant_trans_id", ""))
    except Exception:
        return _click_resp(base, -5, "User does not exist")

    c = db()
    order = c.execute("SELECT * FROM click_orders WHERE id=?", (oid,)).fetchone()
    if not order:
        c.close()
        return _click_resp(base, -5, "User does not exist")

    if _click_amount(f("amount")) != float(order["amount"]):
        c.close()
        return _click_resp(base, -2, "Incorrect parameter amount")
    if order["status"] == "paid":
        c.close()
        return _click_resp(base, -4, "Already paid")
    if order["status"] == "cancelled":
        c.close()
        return _click_resp(base, -9, "Transaction cancelled")

    c.execute(
        "UPDATE click_orders SET status='prepared', click_trans_id=?, click_paydoc_id=? WHERE id=? AND status IN ('new','prepared')",
        (f("click_trans_id", ""), f("click_paydoc_id", ""), oid)
    )
    c.commit()
    c.close()
    return _click_resp(base, 0, "Success")


@app.route("/click/complete", methods=["POST"])
def click_complete():
    cfg = click_cfg()
    f = request.form.get
    base = {
        "click_trans_id": f("click_trans_id", ""),
        "merchant_trans_id": f("merchant_trans_id", ""),
        "merchant_confirm_id": f("merchant_prepare_id", ""),
    }
    if not cfg["ready"]:
        return _click_resp(base, -8, "Error in request from click")

    bad = _click_check(request.form, "1", cfg, complete=True)
    if bad:
        return _click_resp(base, *bad)

    try:
        oid = int(f("merchant_trans_id", ""))
        pid = int(f("merchant_prepare_id", ""))
    except Exception:
        return _click_resp(base, -6, "Transaction does not exist")

    c = db()
    order = c.execute("SELECT * FROM click_orders WHERE id=?", (oid,)).fetchone()
    if not order:
        c.close()
        return _click_resp(base, -5, "User does not exist")
    if pid != oid or (order["click_trans_id"] or "") != f("click_trans_id", ""):
        c.close()
        return _click_resp(base, -6, "Transaction does not exist")
    if _click_amount(f("amount")) != float(order["amount"]):
        c.close()
        return _click_resp(base, -2, "Incorrect parameter amount")
    if order["status"] == "paid":
        c.close()
        return _click_resp(base, -4, "Already paid")
    if order["status"] == "cancelled":
        c.close()
        return _click_resp(base, -9, "Transaction cancelled")

    # Click xato yuborgan bo'lsa (error < 0) — tranzaksiya bekor qilinadi
    try:
        click_error = int(f("error", "0") or 0)
    except Exception:
        click_error = 0
    if click_error < 0:
        c.execute(
            "UPDATE click_orders SET status='cancelled', error_note=? WHERE id=? AND status!='paid'",
            (f("error_note", "")[:200], oid)
        )
        c.commit()
        c.close()
        return _click_resp(base, -9, "Transaction cancelled")

    # Faqat 'prepared' holatidan 'paid' ga bir marta o'tadi (qayta so'rovdan himoya)
    now = datetime.now().isoformat(timespec="seconds")
    cur = c.execute(
        "UPDATE click_orders SET status='paid', paid_at=? WHERE id=? AND status='prepared'",
        (now, oid)
    )
    if cur.rowcount != 1:
        c.rollback()
        c.close()
        return _click_resp(base, -4, "Already paid")

    _click_fulfill(c, order)
    c.commit()
    c.close()
    return _click_resp(base, 0, "Success")


@app.route("/balance/click", methods=["POST"])
def balance_click():
    if not login_required():
        return redirect("/login")
    cfg = click_cfg()
    if not cfg["ready"]:
        flash("Click hali ulanmagan.")
        return redirect("/balance/topup")

    ps = pay_settings()
    try:
        amount = int(re.sub(r"\D", "", request.form.get("amount", "")) or 0)
    except Exception:
        amount = 0
    if amount < ps["min"] or amount > ps["max"]:
        flash(f"Summa {money(ps['min'])} dan {money(ps['max'])} gacha bo'lishi kerak.")
        return redirect("/balance/topup")

    user = current_user()
    c = db()
    cur = c.execute("INSERT INTO click_orders(user_id, amount) VALUES(?,?)", (user["id"], amount))
    oid = cur.lastrowid
    c.commit()
    c.close()

    params = {
        "service_id": cfg["service_id"],
        "merchant_id": cfg["merchant_id"],
        "amount": amount,
        "transaction_param": oid,
        "return_url": cfg["site"] + "/profile",
    }
    if cfg["merchant_user_id"]:
        params["merchant_user_id"] = cfg["merchant_user_id"]
    return redirect("https://my.click.uz/services/pay?" + urlencode(params))



@app.route("/admin/demo-pay", methods=["POST"])
def admin_demo_pay():
    if not admin_required():
        return redirect("/admin-login")
    on = request.form.get("value") == "1"
    c = db()
    set_setting_text("demo_pay", "1" if on else "0", conn=c)
    admin_log("DEMO_PAY", "Sinov to'lov rejimi " + ("YOQILDI" if on else "o'chirildi"), conn=c)
    c.commit()
    c.close()
    flash("Sinov rejimi yoqildi. Haqiqiy pul yechilmaydi." if on else "Sinov rejimi o'chirildi.")
    return redirect("/admin/click")


@app.route("/admin/click")
def admin_click():
    if not admin_required():
        return redirect("/admin-login")
    cfg = click_cfg()
    c = db()
    rows = c.execute(
        """
        SELECT click_orders.*, users.name uname, users.phone uphone
        FROM click_orders JOIN users ON users.id=click_orders.user_id
        ORDER BY click_orders.id DESC LIMIT 200
        """
    ).fetchall()
    total = c.execute("SELECT COALESCE(SUM(amount),0) FROM click_orders WHERE status='paid'").fetchone()[0]
    c.close()

    names = {"new": ("Yangi", "blue"), "prepared": ("Jarayonda", "yellow"),
             "paid": ("To'langan", "green"), "cancelled": ("Bekor", "red")}
    body = ""
    for r in rows:
        lb, col = names.get(r["status"], (r["status"], "blue"))
        body += f"""<tr><td>#{r['id']}</td><td>{esc(r['uname'])}<br><small>{esc(r['uphone'])}</small></td>
        <td><b>{esc(money(r['amount']))}</b></td><td><span class="admin-badge {col}">{lb}</span></td>
        <td>{esc(str(r['created_at'])[:16])}</td><td>{esc(str(r['paid_at'] or '')[:16])}</td><td>{esc((r['provider'] or 'click').title())} · {esc({"balance": "Balans", "new_listing": "Yangi e'lon", "service": "Xizmat"}.get(r['purpose'] or 'balance', ''))} {esc(r['service'] or '')} {esc(r['error_note'])}</td></tr>"""
    if not body:
        body = '<tr><td colspan="7">Hozircha Click to\'lovlari yo\'q.</td></tr>'

    pm = payme_cfg()
    demo_warn = ('<span class="admin-badge red">⚠ SINOV REJIMI YOQILGAN: haqiqiy saytda o\'chiring!</span> ' if demo_pay_on() else '')
    state = demo_warn + ('<span class="admin-badge green">Payme ulangan</span> ' if pm["ready"] else '<span class="admin-badge red">Payme o\'chirilgan</span> ') + ('<span class="admin-badge green">Click ulangan</span>' if cfg["ready"]
             else '<span class="admin-badge red">Click o\'chirilgan (CLICK_ENABLED=1 va kalitlar kerak)</span>')
    base = cfg["site"] or "https://SAYTINGIZ"
    content = f"""
    <h1 class="admin-page-title">🟦 Onlayn to'lovlar (Click va Payme)</h1>
    <div class="admin-page-subtitle">Avtomatik to'lovlar. Jami to'langan: <b>{esc(money(total))}</b></div>
    <div style="margin-bottom:14px">{state}</div>
    <div class="admin-panel" style="margin-bottom:14px;border:2px solid {'#e53935' if demo_pay_on() else '#e6e8ec'}">
      <b>🧪 Sinov to'lov rejimi</b>
      <p style="color:#5b6b7e;font-size:13px;margin:6px 0 10px">
        Yoqilganda mijoz VIP/TOP to'lovida Click oynasiga o'xshash <b>sinov oynasini</b> ko'radi:
        karta kiritadi, SMS kod (123456) yozadi va xizmat yoqiladi. <b>Haqiqiy pul yechilmaydi.</b>
        Click va Payme ulanmaguncha jarayonni ko'rish uchun kerak.
        <b style="color:#b3261e">Haqiqiy saytda albatta o'chiring</b>, aks holda har kim bepul VIP/TOP olishi mumkin.
      </p>
      <form method="post" action="/admin/demo-pay">
        <input type="hidden" name="value" value="{'0' if demo_pay_on() else '1'}">
        <button class="admin-btn {'red' if demo_pay_on() else 'yellow'}" type="submit">
          {'⏹ Sinov rejimini o\'chirish' if demo_pay_on() else '▶ Sinov rejimini yoqish'}
        </button>
      </form>
    </div>
    <div class="admin-panel" style="margin-bottom:14px">
      <b>Click kabinetiga kiritiladigan manzillar:</b><br>
      Prepare: <code>{esc(base)}/click/prepare</code><br>
      Complete: <code>{esc(base)}/click/complete</code><br>
      <b>Payme kabinetiga kiritiladigan manzil:</b> <code>{esc(base)}/payme</code>
    </div>
    <div class="admin-panel"><div class="admin-table-wrap"><table class="admin-table">
      <thead><tr><th>ID</th><th>Foydalanuvchi</th><th>Summa</th><th>Holat</th><th>Yaratildi</th><th>To'landi</th><th>Maqsad / izoh</th></tr></thead>
      <tbody>{body}</tbody></table></div></div>
    """
    return render_admin(content, "Onlayn to'lovlar", "click")



# =========================================================
# ADMIN: RO'YXATDAN O'TISH STATISTIKASI
# =========================================================

@app.route("/admin/registrations")
def admin_registrations():
    if not admin_required():
        return redirect("/admin-login")

    c = db()
    L = "datetime({col},'+5 hours')"   # Toshkent vaqti (UTC+5)

    def cond(col, window):
        loc = L.format(col=col)
        if window == "today":
            return f"date({loc}) = date('now','+5 hours')"
        if window == "week":
            return f"{loc} >= datetime('now','+5 hours','-7 days')"
        if window == "month":
            return f"{loc} >= datetime('now','+5 hours','-30 days')"
        if window == "year":
            return f"{loc} >= datetime('now','+5 hours','-365 days')"
        return "1=1"

    NOT_REG = "phone NOT IN (SELECT phone FROM users)"

    def card_numbers(window):
        reg = c.execute(f"SELECT COUNT(*) FROM users WHERE is_admin=0 AND {cond('created_at', window)}").fetchone()[0]
        started = c.execute(f"SELECT COUNT(DISTINCT phone) FROM auth_events WHERE event='sms_sent' AND is_new=1 AND {cond('created_at', window)}").fetchone()[0]
        incomplete = c.execute(f"SELECT COUNT(DISTINCT phone) FROM auth_events WHERE event='sms_sent' AND is_new=1 AND {NOT_REG} AND {cond('created_at', window)}").fetchone()[0]
        logins = c.execute(f"SELECT COUNT(*) FROM auth_events WHERE event='verified' AND is_new=0 AND {cond('created_at', window)}").fetchone()[0]
        return reg, started, incomplete, logins

    windows = [("today", "Bugun"), ("week", "7 kun"), ("month", "30 kun"), ("year", "365 kun"), ("all", "Jami")]
    cards = ""
    for key, label in windows:
        reg, started, incomplete, logins = card_numbers(key)
        cards += f"""
        <div class="admin-panel" style="flex:1;min-width:170px;margin:0">
          <div style="color:#8090a3;font-size:13px;font-weight:700">{label}</div>
          <div style="font-size:30px;font-weight:900;margin:4px 0">{reg}</div>
          <div style="font-size:12px;color:#5b6b7e;line-height:1.7">
            ro'yxatdan o'tdi<br>
            boshlagan: <b>{started}</b><br>
            tugatmagan: <b>{incomplete}</b><br>
            qayta kirgan: <b>{logins}</b>
          </div>
        </div>"""

    def series(group_user, group_event, limit, title):
        users = dict(c.execute(
            f"SELECT {group_user} k, COUNT(*) FROM users WHERE is_admin=0 GROUP BY k"
        ).fetchall())
        started = dict(c.execute(
            f"SELECT {group_event} k, COUNT(DISTINCT phone) FROM auth_events WHERE event='sms_sent' AND is_new=1 GROUP BY k"
        ).fetchall())
        incomplete = dict(c.execute(
            f"SELECT {group_event} k, COUNT(DISTINCT phone) FROM auth_events WHERE event='sms_sent' AND is_new=1 AND {NOT_REG} GROUP BY k"
        ).fetchall())
        logins = dict(c.execute(
            f"SELECT {group_event} k, COUNT(*) FROM auth_events WHERE event='verified' AND is_new=0 GROUP BY k"
        ).fetchall())
        keys = sorted(set(users) | set(started) | set(incomplete) | set(logins), reverse=True)[:limit]
        top = max([users.get(k, 0) for k in keys] + [1])
        rows = ""
        for k in keys:
            n = users.get(k, 0)
            w = int(n * 100 / top)
            rows += f"""<tr><td><b>{esc(k)}</b></td>
              <td style="width:40%"><div style="background:#ffd54a;height:12px;border-radius:6px;width:{w}%;min-width:{3 if n else 0}px"></div></td>
              <td><b>{n}</b></td><td>{started.get(k, 0)}</td><td>{incomplete.get(k, 0)}</td><td>{logins.get(k, 0)}</td></tr>"""
        if not rows:
            rows = '<tr><td colspan="6">Ma\'lumot yo\'q.</td></tr>'
        return f"""
        <div class="admin-panel" style="margin-top:16px">
          <div class="admin-panel-title">{title}</div>
          <div class="admin-table-wrap"><table class="admin-table">
            <thead><tr><th>Davr</th><th></th><th>Ro'yxatdan o'tdi</th><th>Boshlagan</th><th>Tugatmagan</th><th>Qayta kirgan</th></tr></thead>
            <tbody>{rows}</tbody></table></div>
        </div>"""

    def loc(col):
        return L.format(col=col)

    day_u, day_e = f"date({loc('created_at')})", f"date({loc('created_at')})"
    wk = f"date({loc('created_at')},'weekday 0','-6 days')"
    mo = f"strftime('%Y-%m',{loc('created_at')})"
    yr = f"strftime('%Y',{loc('created_at')})"

    tables = (
        series(day_u, day_e, 30, "📅 Kunlar bo'yicha (oxirgi 30 kun)")
        + series(wk, wk, 12, "🗓 Haftalar bo'yicha (hafta boshi: dushanba)")
        + series(mo, mo, 12, "📆 Oylar bo'yicha")
        + series(yr, yr, 10, "📈 Yillar bo'yicha")
    )

    unfinished = c.execute(
        f"""
        SELECT phone, COUNT(*) tries, MAX({loc('created_at')}) last
        FROM auth_events
        WHERE event='sms_sent' AND is_new=1 AND {NOT_REG}
        GROUP BY phone ORDER BY MAX(created_at) DESC LIMIT 30
        """
    ).fetchall()
    recent = c.execute(
        f"SELECT phone, {loc('created_at')} at FROM users WHERE is_admin=0 ORDER BY id DESC LIMIT 20"
    ).fetchall()
    c.close()

    un_rows = "".join(
        f"<tr><td>{esc(r['phone'])}</td><td>{r['tries']}</td><td>{esc(str(r['last'])[:16])}</td></tr>"
        for r in unfinished
    ) or '<tr><td colspan="3">Hozircha yo\'q.</td></tr>'
    rec_rows = "".join(
        f"<tr><td>{esc(r['phone'])}</td><td>{esc(str(r['at'])[:16])}</td></tr>"
        for r in recent
    ) or '<tr><td colspan="2">Hozircha yo\'q.</td></tr>'

    content = f"""
    <h1 class="admin-page-title">👥 Ro'yxatdan o'tish statistikasi</h1>
    <div class="admin-page-subtitle">Vaqt Toshkent bo'yicha. 7, 30 va 365 kun &mdash; oxirgi shuncha kun ichida.</div>
    <div style="display:flex;gap:12px;flex-wrap:wrap">{cards}</div>

    <div class="admin-panel" style="margin-top:16px;color:#5b6b7e;font-size:13px;line-height:1.7">
      <b>Tushuntirish:</b><br>
      <b>Ro'yxatdan o'tdi</b> &mdash; SMS kodni tasdiqlab, hisobi yaratilgan yangi foydalanuvchilar.<br>
      <b>Boshlagan</b> &mdash; yangi raqam kiritib, SMS kod olgan odamlar.<br>
      <b>Tugatmagan</b> &mdash; SMS kod olgan, lekin hali ro'yxatdan o'tmaganlar.<br>
      <b>Qayta kirgan</b> &mdash; oldin ro'yxatdan o'tgan va qayta SMS bilan kirganlar.<br>
      Boshlagan va tugatmagan sonlari yangi tizim ishga tushgan kundan hisoblanadi, oldingi kunlar uchun faqat "ro'yxatdan o'tdi" ko'rinadi.
    </div>

    {tables}

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px">
      <div class="admin-panel"><div class="admin-panel-title">⏳ Tugatmaganlar (oxirgi 30 ta)</div>
        <div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Telefon</th><th>Urinish</th><th>Oxirgi</th></tr></thead><tbody>{un_rows}</tbody></table></div></div>
      <div class="admin-panel"><div class="admin-panel-title">✅ Oxirgi ro'yxatdan o'tganlar</div>
        <div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Telefon</th><th>Vaqt</th></tr></thead><tbody>{rec_rows}</tbody></table></div></div>
    </div>
    """
    return render_admin(content, "Ro'yxatdan o'tish", "regs")


# =========================================================
# ADMIN: MOBIL MENYU
# =========================================================

@app.route("/admin/mobile-menu", methods=["GET", "POST"])
def admin_mobile_menu():
    if not admin_required():
        return redirect("/admin-login")

    menu = get_mobile_menu()
    items = list(menu["items"])
    while len(items) < 6:
        items.append({"key": f"slot{len(items)+1}", "icon": "•", "uz": "", "ru": "", "en": "",
                      "url": "/", "enabled": False, "center": False})
    items = items[:6]

    if request.method == "POST":
        center = request.form.get("center", "")
        new_items = []
        for n in range(6):
            old = items[n]
            new_items.append({
                "key": old.get("key") or f"slot{n+1}",
                "icon": (request.form.get(f"icon_{n}", "") or "•").strip()[:8],
                "uz": request.form.get(f"uz_{n}", "").strip()[:20],
                "ru": request.form.get(f"ru_{n}", "").strip()[:20],
                "en": request.form.get(f"en_{n}", "").strip()[:20],
                "url": safe_menu_url(request.form.get(f"url_{n}", "/")),
                "enabled": request.form.get(f"enabled_{n}") == "1",
                "center": center == str(n),
            })
        # tartib: formadagi "order_n" bo'yicha
        def order_of(n):
            try:
                return int(request.form.get(f"order_{n}", n))
            except Exception:
                return n
        idx = sorted(range(6), key=lambda n: (order_of(n), n))
        new_items = [new_items[n] for n in idx]

        data = {
            "enabled": request.form.get("menu_enabled") == "1",
            "items": new_items,
        }
        c = db()
        set_setting_text("mobile_menu", json.dumps(data, ensure_ascii=False), conn=c)
        admin_log("MOBILE_MENU", "Mobil menyu yangilandi", conn=c)
        c.commit()
        c.close()
        flash("Mobil menyu saqlandi.")
        return redirect("/admin/mobile-menu")

    rows = ""
    for n, it in enumerate(items):
        rows += f"""
        <tr>
          <td><input type="number" name="order_{n}" value="{n+1}" style="width:56px"></td>
          <td><input type="checkbox" name="enabled_{n}" value="1" {"checked" if it.get("enabled") else ""}></td>
          <td><input name="icon_{n}" value="{esc(it.get('icon'))}" maxlength="8" style="width:56px;font-size:20px;text-align:center"></td>
          <td><input name="uz_{n}" value="{esc(it.get('uz'))}" placeholder="UZ" style="width:120px"></td>
          <td><input name="ru_{n}" value="{esc(it.get('ru'))}" placeholder="RU" style="width:120px"></td>
          <td><input name="en_{n}" value="{esc(it.get('en'))}" placeholder="EN" style="width:120px"></td>
          <td><input name="url_{n}" value="{esc(it.get('url'))}" style="width:190px"></td>
          <td><input type="radio" name="center" value="{n}" {"checked" if it.get("center") else ""}></td>
        </tr>
        """

    content = f"""
    <h1 class="admin-page-title">📱 Mobil menyu</h1>
    <div class="admin-page-subtitle">Telefondagi pastki menyu va mobil ilova sozlamalari</div>

    <div class="admin-panel">
      <form method="post">
        <label style="display:flex;gap:8px;align-items:center;margin-bottom:14px;font-weight:700">
          <input type="checkbox" name="menu_enabled" value="1" {"checked" if menu.get("enabled", True) else ""}>
          Pastki menyu yoqilgan
        </label>

        <div class="admin-table-wrap">
          <table class="admin-table">
            <thead><tr>
              <th>Tartib</th><th>Yoqilgan</th><th>Ikonka</th><th>UZ</th><th>RU</th><th>EN</th><th>Havola</th><th>Katta tugma</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>

        <p style="color:#8090a3;font-size:13px;margin:12px 0">
          Eng ko'pi bilan 6 ta tugma. "Katta tugma" odatda "Qo'shish" uchun (sariq, o'rtada).
          Havola <b>/</b> bilan boshlanishi kerak (masalan <b>/?section=avto</b>) yoki to'liq https:// manzil.
          Mobil ilova bu sozlamani <b>/api/mobile/config?lang=uz</b> orqali oladi.
        </p>

        <button class="admin-btn yellow" type="submit">💾 Saqlash</button>
      </form>
    </div>
    """
    return render_admin(content, "Mobil menyu", "mobile")


# =========================================================
# ADMIN BO'LIMLAR
# =========================================================

@app.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():
    if not admin_required():
        return redirect("/admin-login")

    if request.method=="POST":
        name=request.form.get("name","").strip()
        icon=request.form.get("icon","📂").strip() or "📂"
        kind=request.form.get("kind","real_estate").strip()
        try:
            sort_order=int(request.form.get("sort_order","0") or 0)
        except:
            sort_order=0
        if kind not in {"real_estate","auto"}:
            kind="real_estate"
        slug=slugify(request.form.get("slug","").strip() or name)

        if not name:
            flash("Bo'lim nomini kiriting.")
            return redirect("/admin/categories")

        c=db()
        try:
            c.execute("""
                INSERT INTO categories(name,slug,icon,kind,sort_order,is_active)
                VALUES(?,?,?,?,?,1)
            """,(name,slug,icon,kind,sort_order))
            c.commit()
            admin_log("CATEGORY_CREATE",f"Bo'lim qo'shildi: {name}",conn=c)
            c.commit()
            flash("Bo'lim muvaffaqiyatli qo'shildi.")
        except sqlite3.IntegrityError:
            c.rollback()
            flash("Bu slug bilan bo'lim allaqachon mavjud.")
        finally:
            c.close()
        return redirect("/admin/categories")

    c=db()
    categories=c.execute("""
        SELECT categories.*,
               (SELECT COUNT(*) FROM listings WHERE listings.category_id=categories.id) listing_count
        FROM categories
        ORDER BY sort_order,id
    """).fetchall()
    c.close()

    rows=""
    for cat in categories:
        rows+=f"""
        <tr>
          <td>#{cat['id']}</td>
          <td style="font-size:22px">{esc(cat['icon'])}</td>
          <td><strong>{esc(cat['name'])}</strong><br><small>{esc(cat['slug'])}</small></td>
          <td>{'🚗 Avto' if cat['kind']=='auto' else '🏠 Ko‘chmas mulk'}</td>
          <td>{cat['listing_count']}</td>
          <td>{'FAOL' if cat['is_active'] else 'YOPIQ'}</td>
          <td>
            <div class="admin-actions">
              <a class="admin-btn yellow" href="/admin/category/{cat['id']}/edit">✏️ Tahrirlash</a>
              <form method="post" action="/admin/category/{cat['id']}/toggle" style="display:inline">
                <button class="admin-btn" type="submit">{'Yopish' if cat['is_active'] else 'Ochish'}</button>
              </form>
              <form method="post" action="/admin/category/{cat['id']}/delete" style="display:inline" onsubmit="return confirm('Bo‘lim o‘chirilsinmi?')">
                <button class="admin-btn red" type="submit">🗑️ O‘chirish</button>
              </form>
            </div>
          </td>
        </tr>
        """

    content=f"""
    <h1 class="admin-page-title">📂 Bo'limlar</h1>
    <div class="admin-page-subtitle">Saytdagi bo'limlarni qo'shish, tahrirlash va boshqarish</div>

    <div class="admin-panel" style="margin-bottom:15px">
      <h2 class="admin-panel-title">＋ Bo'lim qo'shish</h2>
      <form method="post" class="admin-form-grid">
        <div class="admin-form-group"><label>Bo'lim nomi</label><input name="name" placeholder="Masalan: Xizmatlar" required></div>
        <div class="admin-form-group"><label>Ikonka</label><input name="icon" value="📂" maxlength="8"></div>
        <div class="admin-form-group"><label>Slug</label><input name="slug" placeholder="avtomatik yaratiladi"></div>
        <div class="admin-form-group">
          <label>Bo'lim turi</label>
          <select name="kind"><option value="real_estate">🏠 Ko'chmas mulk</option><option value="auto">🚗 Avto</option></select>
        </div>
        <div class="admin-form-group"><label>Tartib</label><input type="number" name="sort_order" value="10"></div>
        <div style="display:flex;align-items:end"><button class="admin-btn yellow" type="submit">＋ Bo'lim qo'shish</button></div>
      </form>
    </div>

    <div class="admin-panel">
      <h2 class="admin-panel-title">Mavjud bo'limlar</h2>
      <div class="admin-table-wrap">
        <table class="admin-table">
          <thead><tr><th>ID</th><th></th><th>Bo'lim</th><th>Turi</th><th>E'lonlar</th><th>Holat</th><th>Amallar</th></tr></thead>
          <tbody>{rows or '<tr><td colspan="7">Bo‘limlar yo‘q.</td></tr>'}</tbody>
        </table>
      </div>
    </div>
    """
    return render_admin(content,"Bo'limlar","categories")


@app.route("/admin/category/<int:category_id>/edit", methods=["GET","POST"])
def admin_category_edit(category_id):
    if not admin_required():
        return redirect("/admin-login")
    c=db()
    category=c.execute("SELECT * FROM categories WHERE id=?",(category_id,)).fetchone()
    c.close()
    if not category:
        flash("Bo'lim topilmadi.")
        return redirect("/admin/categories")

    if request.method=="POST":
        name=request.form.get("name","").strip()
        icon=request.form.get("icon","📂").strip() or "📂"
        slug=slugify(request.form.get("slug","").strip() or name)
        kind=request.form.get("kind","real_estate").strip()
        try: sort_order=int(request.form.get("sort_order","0") or 0)
        except: sort_order=0
        if kind not in {"real_estate","auto"}: kind="real_estate"
        if not name:
            flash("Bo'lim nomini kiriting.")
            return redirect(f"/admin/category/{category_id}/edit")
        c=db()
        try:
            c.execute("""UPDATE categories SET name=?,slug=?,icon=?,kind=?,sort_order=? WHERE id=?""",
                      (name,slug,icon,kind,sort_order,category_id))
            # Category kind o'zgarsa, mavjud e'lonlarning qat'iy ajratilishi saqlanadi:
            c.execute("UPDATE listings SET listing_kind=? WHERE category_id=?",(kind,category_id))
            c.commit()
            admin_log("CATEGORY_EDIT",f"Bo'lim #{category_id} tahrirlandi.",conn=c)
            c.commit()
            flash("Bo'lim yangilandi.")
        except sqlite3.IntegrityError:
            c.rollback()
            flash("Bu slug bilan boshqa bo'lim mavjud.")
        finally:
            c.close()
        return redirect("/admin/categories")

    content=f"""
    <div class="admin-panel" style="max-width:700px">
      <h1 class="admin-page-title">✏️ Bo'limni tahrirlash</h1>
      <form method="post" class="admin-form-grid">
        <div class="admin-form-group"><label>Bo'lim nomi</label><input name="name" value="{esc(category['name'])}" required></div>
        <div class="admin-form-group"><label>Ikonka</label><input name="icon" value="{esc(category['icon'])}"></div>
        <div class="admin-form-group"><label>Slug</label><input name="slug" value="{esc(category['slug'])}" required></div>
        <div class="admin-form-group"><label>Bo'lim turi</label>
          <select name="kind">
            <option value="real_estate" {'selected' if category['kind']=='real_estate' else ''}>🏠 Ko'chmas mulk</option>
            <option value="auto" {'selected' if category['kind']=='auto' else ''}>🚗 Avto</option>
          </select>
        </div>
        <div class="admin-form-group"><label>Tartib</label><input type="number" name="sort_order" value="{category['sort_order']}"></div>
        <div><button class="admin-btn yellow" type="submit">💾 Saqlash</button> <a class="admin-btn" href="/admin/categories">Bekor qilish</a></div>
      </form>
    </div>
    """
    return render_admin(content,"Bo'limni tahrirlash","categories")


@app.route("/admin/category/<int:category_id>/toggle", methods=["POST"])
def admin_category_toggle(category_id):
    if not admin_required():
        return redirect("/admin-login")
    c=db()
    c.execute("UPDATE categories SET is_active=CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",(category_id,))
    c.commit()
    admin_log("CATEGORY_TOGGLE",f"Bo'lim #{category_id} holati o'zgartirildi.",conn=c)
    c.commit()
    c.close()
    return redirect("/admin/categories")


@app.route("/admin/category/<int:category_id>/delete", methods=["POST"])
def admin_category_delete(category_id):
    if not admin_required():
        return redirect("/admin-login")
    if category_id in (1,2):
        flash("Asosiy Ko'chmas mulk va Avto bo'limlarini o'chirib bo'lmaydi.")
        return redirect("/admin/categories")
    c=db()
    count=c.execute("SELECT COUNT(*) FROM listings WHERE category_id=?",(category_id,)).fetchone()[0]
    if count:
        c.close()
        flash("Bu bo'limda e'lonlar bor. Avval e'lonlarni boshqa bo'limga o'tkazing yoki o'chiring.")
        return redirect("/admin/categories")
    c.execute("DELETE FROM categories WHERE id=?",(category_id,))
    c.commit()
    admin_log("CATEGORY_DELETE",f"Bo'lim #{category_id} o'chirildi.",conn=c)
    c.commit()
    c.close()
    flash("Bo'lim o'chirildi.")
    return redirect("/admin/categories")


# =========================================================
# ADMIN SETTINGS
# =========================================================

@app.route(
    "/admin/settings",
    methods=["GET", "POST"]
)
def admin_settings():

    if not admin_required():
        return redirect("/admin-login")

    if request.method == "POST":

        old_vip = get_setting(
            "vip_price",
            VIP_PRICE
        )

        old_top = get_setting(
            "top_price",
            TOP_PRICE
        )

        old_up = get_setting(
            "up_price",
            UP_PRICE
        )

        try:

            new_vip = int(
                request.form.get(
                    "vip_price",
                    old_vip
                )
            )

            new_top = int(
                request.form.get(
                    "top_price",
                    old_top
                )
            )

            new_up = int(
                request.form.get(
                    "up_price",
                    old_up
                )
            )

        except:

            flash(
                "Narx noto'g'ri kiritildi."
            )

            return redirect(
                "/admin/settings"
            )

        if min(
            new_vip,
            new_top,
            new_up
        ) < 0:

            flash(
                "Narx manfiy bo'lishi mumkin emas."
            )

            return redirect(
                "/admin/settings"
            )

        c = db()

        values = {
            "vip_price": new_vip,
            "top_price": new_top,
            "up_price": new_up
        }

        old_values = {
            "vip_price": old_vip,
            "top_price": old_top,
            "up_price": old_up
        }

        for key, value in values.items():

            c.execute(
                """
                UPDATE settings
                SET value=?,
                    updated_at=?
                WHERE key=?
                """,
                (
                    str(value),
                    datetime.now().isoformat(),
                    key
                )
            )

            if old_values[key] != value:

                admin_log(
                    "PRICE_CHANGE",
                    f"{key}: "
                    f"{old_values[key]} -> {value}",
                    conn=c
                )

        c.commit()
        c.close()

        flash(
            "Xizmat narxlari muvaffaqiyatli yangilandi."
        )

        return redirect(
            "/admin/settings"
        )

    vip = get_setting(
        "vip_price",
        VIP_PRICE
    )

    top = get_setting(
        "top_price",
        TOP_PRICE
    )

    up = get_setting(
        "up_price",
        UP_PRICE
    )

    content = f"""

    <h1 class="admin-page-title">
    ⚙️ Sozlamalar
    </h1>

    <div class="admin-page-subtitle">
    Uy77 xizmatlari va narxlarini boshqarish
    </div>


    <div class="admin-price-grid">

    <div class="admin-price-card">

    <div style="font-size:30px">
    👑
    </div>

    <h3>
    VIP
    </h3>

    <div class="admin-price">
    {money(vip)}
    </div>

    <span style="font-size:9px;color:#8090a3">
    7 kun
    </span>

    </div>


    <div class="admin-price-card">

    <div style="font-size:30px">
    🔥
    </div>

    <h3>
    TOP
    </h3>

    <div class="admin-price">
    {money(top)}
    </div>

    <span style="font-size:9px;color:#8090a3">
    7 kun
    </span>

    </div>


    <div class="admin-price-card">

    <div style="font-size:30px">
    🚀
    </div>

    <h3>
    UP
    </h3>

    <div class="admin-price">
    {money(up)}
    </div>

    <span style="font-size:9px;color:#8090a3">
    24 soat
    </span>

    </div>

    </div>


    <br>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Xizmat narxlarini o'zgartirish
    </h2>

    <form
        method="post"
        class="admin-form-grid"
    >

    <div class="admin-form-group">

    <label>
    VIP narxi
    </label>

    <input
        type="number"
        name="vip_price"
        min="0"
        value="{vip}"
        required
    >

    </div>


    <div class="admin-form-group">

    <label>
    TOP narxi
    </label>

    <input
        type="number"
        name="top_price"
        min="0"
        value="{top}"
        required
    >

    </div>


    <div class="admin-form-group">

    <label>
    UP narxi
    </label>

    <input
        type="number"
        name="up_price"
        min="0"
        value="{up}"
        required
    >

    </div>

    <div></div>

    <div>

    <button
        class="admin-btn yellow"
        type="submit"
    >
    💾 Saqlash
    </button>

    </div>

    </form>

    </div>


    <div
        class="admin-panel"
        style="
        margin-top:15px;
        background:#fffbea
        "
    >

    <strong>
    ⚠️ Muhim
    </strong>

    <p
        style="
        font-size:11px;
        color:#68778a;
        line-height:1.6
        "
    >
    Bu yerda narx o'zgartirilgandan keyin
    foydalanuvchilar tomonidagi VIP/TOP/UP
    narxlari avtomatik ravishda yangi narxga o'tadi.
    O'zgarishlar harakatlar tarixiga yoziladi.
    </p>

    </div>

    """

    return render_admin(
        content,
        "Sozlamalar",
        "settings"
    )


# =========================================================
# ADMIN SEARCH
# =========================================================

@app.route("/admin/search")
def admin_search():

    if not admin_required():
        return redirect("/admin-login")

    q = request.args.get(
        "q",
        ""
    ).strip()

    if not q:

        return redirect("/admin")

    c = db()

    users = c.execute(
        """
        SELECT *
        FROM users
        WHERE name LIKE ?
        OR phone LIKE ?
        LIMIT 20
        """,
        (
            f"%{q}%",
            f"%{q}%"
        )
    ).fetchall()

    listings_data = c.execute(
        """
        SELECT
            listings.*,
            users.name owner
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE listings.title LIKE ?
        OR listings.address LIKE ?
        LIMIT 20
        """,
        (
            f"%{q}%",
            f"%{q}%"
        )
    ).fetchall()

    c.close()

    user_rows = "".join(
        f"""
        <tr>
        <td>#{u["id"]}</td>
        <td>{esc(u["name"])}</td>
        <td>{esc(u["phone"])}</td>
        <td>{money(u["balance"])}</td>
        <td>
        <a class="admin-btn"
           href="/admin/user/{u['id']}">
        Ko'rish
        </a>
        </td>
        </tr>
        """
        for u in users
    )

    listing_rows = "".join(
        f"""
        <tr>
        <td>#{l["id"]}</td>
        <td>{esc(l["title"])}</td>
        <td>{esc(l["owner"])}</td>
        <td>{price_of(l)}</td>
        <td>
        <a class="admin-btn"
           href="/listing/{l['id']}"
           target="_blank">
        Ko'rish
        </a>
        </td>
        </tr>
        """
        for l in listings_data
    )

    content = f"""

    <h1 class="admin-page-title">
    🔎 Qidiruv
    </h1>

    <div class="admin-page-subtitle">
    Natija: {esc(q)}
    </div>

    <div class="admin-grid">

    <div class="admin-panel">

    <h2 class="admin-panel-title">
    Foydalanuvchilar
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>
    <th>ID</th>
    <th>Ism</th>
    <th>Telefon</th>
    <th>Balans</th>
    <th></th>
    </tr>

    </thead>

    <tbody>

    {
        user_rows
        or
        '<tr><td colspan="5">Topilmadi.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>


    <div class="admin-panel">

    <h2 class="admin-panel-title">
    E'lonlar
    </h2>

    <div class="admin-table-wrap">

    <table class="admin-table">

    <thead>

    <tr>
    <th>ID</th>
    <th>E'lon</th>
    <th>Egasi</th>
    <th>Narx</th>
    <th></th>
    </tr>

    </thead>

    <tbody>

    {
        listing_rows
        or
        '<tr><td colspan="5">Topilmadi.</td></tr>'
    }

    </tbody>

    </table>

    </div>

    </div>

    </div>

    """

    return render_admin(
        content,
        "Qidiruv",
        "dashboard"
    )


# =========================================================
# CLEANUP EXPIRED
# =========================================================

def cleanup_expired():

    c = db()

    now = datetime.now().isoformat()

    c.execute("""
        UPDATE listings
        SET vip=0
        WHERE vip=1
        AND vip_until IS NOT NULL
        AND vip_until < ?
    """, (
        now,
    ))

    c.execute("""
        UPDATE listings
        SET top=0
        WHERE top=1
        AND top_until IS NOT NULL
        AND top_until < ?
    """, (
        now,
    ))

    c.execute("""
        UPDATE listings
        SET bumped_at=NULL,
            up_until=NULL
        WHERE bumped_at IS NOT NULL
        AND up_until IS NOT NULL
        AND up_until < ?
    """, (
        now,
    ))

    c.commit()
    c.close()


# =========================================================
# API
# =========================================================

@app.route("/api/listings")
def api_listings():

    cleanup_expired()

    c = db()

    rows = c.execute("""
        SELECT
            listings.*,
            users.phone owner_phone
        FROM listings
        JOIN users
        ON users.id=listings.user_id
        WHERE listings.latitude IS NOT NULL
        AND listings.longitude IS NOT NULL
        AND listings.hidden=0
        AND users.blocked=0
        AND listings.listing_kind='real_estate' 
        ORDER BY
            listings.vip DESC,
            listings.top DESC,
            listings.bumped_at DESC,
            listings.id DESC
    """).fetchall()

    c.close()

    result = []

    for row in rows:

        result.append({

            "id":
                row["id"],

            "title":
                row["title"],

            "price":
                row["price"],

            "price_text":
                money(row["price"]),

            "property_type":
                row["property_type"],

            "deal_type":
                row["deal_type"],

            "mortgage":
                row["mortgage"],

            "city":
                row["city"],

            "district":
                row["district"],

            "address":
                row["address"],

            "rooms":
                row["rooms"],

            "area":
                row["area"],

            "latitude":
                row["latitude"],

            "longitude":
                row["longitude"],

            "image":
                row["image"],

            "phone":
                row["owner_phone"]

        })

    return jsonify(result)


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return render_page(
        """
        <div class="form-card">

        <h1>
        404
        </h1>

        <p>
        Sahifa topilmadi.
        </p>

        <a
            class="btn"
            href="/"
        >
        Bosh sahifaga qaytish
        </a>

        </div>
        """
    ), 404


@app.errorhandler(500)
def server_error(error):

    return render_page(
        """
        <div class="form-card">

        <h1>
        500
        </h1>

        <p>
        Serverda xatolik yuz berdi.
        </p>

        <a
            class="btn"
            href="/"
        >
        Bosh sahifaga qaytish
        </a>

        </div>
        """
    ), 500


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print("=" * 60)

    print(
        "Uy77"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print("=" * 60)

    print(
        "ADMIN TELEFON:",
        ADMIN_PHONE
    )

    print(
        "ADMIN LOGIN:",
        "http://127.0.0.1:5000/admin-login"
    )

    print(
        "ADMIN PAROL:",
        ADMIN_DEFAULT_PASSWORD
    )

    print("=" * 60)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )