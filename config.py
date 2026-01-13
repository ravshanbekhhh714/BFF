"""
Telegram Shop Bot - Konfiguratsiya fayli (JSON versiya)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot tokeni
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Admin ID'lar ro'yxati
ADMINS = [
    7485738561,  # Birinchi admin
    5606706053,
    7732032898,# Ikkinchi admin
]
ADMIN_USERNAME = "BFF_007"

# Kanal va guruh ID'lari
CHANNEL_ID = -1003196603414  # @yourchannel
GROUP_ID = -5045327244    # Guruh ID

# JSON fayllar yo'llari
DATA_DIR = "data"
PRODUCTS_FILE = f"{DATA_DIR}/products.json"
ORDERS_FILE = f"{DATA_DIR}/orders.json"
USERS_FILE = f"{DATA_DIR}/users.json"
CATEGORIES_FILE = f"{DATA_DIR}/categories.json"

# Avtomatik post vaqtlari (24-soatlik format)
AUTO_POST_TIMES = [
    "11:00",
    "15:00",
    "20:00"
]

# Kuniga post qilinadigan tovarlar soni
DAILY_POSTS_COUNT = 3

# FAQ javoblari
FAQ_ANSWERS = {
    "yetkazish": """🚚 Siz ikki usulni tanlashingiz mumkin:

Avto yetkazib berish: 20–25 ish kuni ichida yetkaziladi. Narxi kilosiga 6 USD (72 000 so‘m).

Avia yetkazib berish: 7–10 ish kuni ichida yetkaziladi. Narxi kilosiga 9 USD (108 000 so‘m).

Gulistonga kelgan mahsulotni BTS orqali boshqa viloyatlarga 2–3 ish kuni ichida jo‘natish mumkin. Narxi alohida belgilanadi (bog‘lanib so‘rashingiz mumkin).""",

    "tolov": "To‘lov faqat onlayn karta orqali amalga oshiriladi.",
    "aloqa": """📞 Biz bilan bog'lanish:
📱 Telefon: +998 94 721 00 78
🌐 Telegram: @BFF_007
⏰ Ish vaqti: 9:00 - 18:00"""
}

# Xabarlar
MESSAGES = {
    "start": """
👋 Xush kelibsiz!

🛍 Bizning internet do'konimizga xush kelibsiz!

Menyu orqali tovarlarni ko'ring va buyurtma bering.
    """,
    "order_success": "✅ Buyurtmangiz qabul qilindi! Tez orada operator siz bilan bog'lanadi.",
    "order_cancel": "❌ Buyurtma bekor qilindi.",
    "admin_panel": "👨‍💼 Admin panel",
    "no_products": "📭 Hozircha tovarlar yo'q",
    "product_added": "✅ Tovar muvaffaqiyatli qo'shildi!",
    "product_deleted": "🗑 Tovar o'chirildi",
    "invalid_input": "❌ Noto'g'ri ma'lumot kiritildi. Qaytadan urinib ko'ring.",
    "category_added": "✅ Kategoriya qo'shildi!",
    "category_deleted": "🗑 Kategoriya o'chirildi",
}
