"""
Database bilan ishlash moduli - PostgreSQL versiya
(Tashqi ko'rinishi eski JSONDatabase bilan bir xil)
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Optional, Dict, Any
import random

# Config faylingizdan kerakli o'zgaruvchilarni import qiling
# Agar configda DATABASE_URL bo'lmasa, uni os.getenv dan olamiz
import config 

logger = logging.getLogger(__name__)

class JSONDatabase:
    """
    Eski JSONDatabase klassining PostgreSQL adaptatsiyasi.
    Barcha metodlar va nomlar saqlab qolingan.
    """

    def __init__(self):
        """
        Initsializatsiya - Bazaga ulanish va jadvallarni yaratish
        """
        # Railwayda DATABASE_URL environment variable ichida bo'ladi
        self.db_url = os.getenv("DATABASE_URL")
        
        if not self.db_url:
            logger.error("❌ DATABASE_URL topilmadi! Railway Variables ni tekshiring.")
            return

        self._create_tables()
        logger.info("✅ PostgreSQL Database initsializatsiya qilindi")

    def _get_connection(self):
        """Bazaga ulanish ob'ektini qaytaradi"""
        conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn

    def _create_tables(self):
        """Jadvallarni yaratish (agar yo'q bo'lsa)"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Categories jadvali
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS categories (
                            name TEXT PRIMARY KEY
                        );
                    """)
                    
                    # Products jadvali
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS products (
                            id SERIAL PRIMARY KEY,
                            category TEXT REFERENCES categories(name) ON DELETE CASCADE,
                            name TEXT NOT NULL,
                            description TEXT,
                            price DECIMAL(15, 2),
                            size TEXT,
                            photo_id TEXT,
                            is_available BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # Users jadvali
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username TEXT,
                            first_name TEXT,
                            last_name TEXT,
                            is_blocked BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # Orders jadvali
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS orders (
                            id SERIAL PRIMARY KEY,
                            order_number TEXT UNIQUE,
                            user_id BIGINT REFERENCES users(user_id),
                            username TEXT,
                            product_id INTEGER REFERENCES products(id),
                            customer_name TEXT,
                            phone TEXT,
                            address TEXT,
                            quantity INTEGER DEFAULT 1,
                            status TEXT DEFAULT 'yangi',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Boshlang'ich kategoriyalarni qo'shish (faqat bo'sh bo'lsa)
                    cur.execute("SELECT COUNT(*) as count FROM categories")
                    if cur.fetchone()['count'] == 0:
                        defaults = [
                            "👕 Kiyimlar", "👟 Poyabzal", "🎒 Sumkalar",
                            "⌚ Aksessuarlar", "📱 Elektronika", "🏠 Uy-ro'zg'or"
                        ]
                        for cat in defaults:
                            cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (cat,))
                            
        except Exception as e:
            logger.error(f"❌ Jadvallarni yaratishda xatolik: {e}")

    # ==================== CATEGORIES ====================

    def get_categories(self) -> List[str]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT name FROM categories")
                    return [row['name'] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    def add_category(self, category: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO categories (name) VALUES (%s)", (category,))
            logger.info(f"✅ Kategoriya qo'shildi: {category}")
            return True
        except psycopg2.IntegrityError:
            logger.warning(f"⚠️ Kategoriya allaqachon mavjud: {category}")
            return False
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            return False

    def delete_category(self, category: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Cascade o'chirish bazada sozlangan, lekin aniqlik uchun:
                    cur.execute("DELETE FROM categories WHERE name = %s", (category,))
                    if cur.rowcount > 0:
                        logger.info(f"✅ Kategoriya o'chirildi: {category}")
                        return True
                    return False
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False

    def update_category(self, old_name: str, new_name: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Bazada foreign key constraints bo'lgani uchun cascade update kerak
                    # Yoki oddiy UPDATE agar foreign keyda ON UPDATE CASCADE bo'lmasa, muammo bo'lishi mumkin.
                    # Oddiy yechim:
                    cur.execute("UPDATE categories SET name = %s WHERE name = %s", (new_name, old_name))
                    # Postgresda products jadvalidagi category ham avtomatik o'zgarishi uchun 
                    # Table yaratishda REFERENCES categories(name) ON UPDATE CASCADE berish kerak edi.
                    # Agar berilmagan bo'lsa, qo'lda yangilaymiz:
                    cur.execute("UPDATE products SET category = %s WHERE category = %s", (new_name, old_name))
                    
                    return True
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return False

    # ==================== PRODUCTS ====================

    def add_product(self, category: str, name: str, description: str,
                    price: float, size: str = None, photo_id: str = None) -> Dict:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO products (category, name, description, price, size, photo_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING *;
                    """, (category, name, description, float(price), size, photo_id))
                    product = cur.fetchone()
                    # Datetime ni stringga o'tkazamiz (eski kod bilan moslik uchun)
                    product['created_at'] = str(product['created_at'])
                    logger.info(f"✅ Tovar qo'shildi: {name} (ID: {product['id']})")
                    return dict(product)
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            return {}

    def get_product(self, product_id: int) -> Optional[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
                    product = cur.fetchone()
                    if product:
                        product['created_at'] = str(product['created_at'])
                        return dict(product)
                    return None
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None

    def get_products_by_category(self, category: str) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM products 
                        WHERE category = %s AND is_available = TRUE
                    """, (category,))
                    products = cur.fetchall()
                    for p in products: p['created_at'] = str(p['created_at'])
                    return [dict(p) for p in products]
        except Exception as e:
            logger.error(f"Error getting products by category: {e}")
            return []

    def get_all_products(self) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM products")
                    products = cur.fetchall()
                    for p in products: p['created_at'] = str(p['created_at'])
                    return [dict(p) for p in products]
        except Exception as e:
            logger.error(f"Error getting all products: {e}")
            return []

    def get_available_products(self) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM products WHERE is_available = TRUE")
                    products = cur.fetchall()
                    for p in products: p['created_at'] = str(p['created_at'])
                    return [dict(p) for p in products]
        except Exception as e:
            logger.error(f"Error getting available products: {e}")
            return []

    def get_random_products(self, count: int = 3) -> List[Dict]:
        # SQL da random olish osonroq (ORDER BY RANDOM())
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM products 
                        WHERE is_available = TRUE 
                        ORDER BY RANDOM() 
                        LIMIT %s
                    """, (count,))
                    products = cur.fetchall()
                    for p in products: p['created_at'] = str(p['created_at'])
                    return [dict(p) for p in products]
        except Exception as e:
            logger.error(f"Error getting random products: {e}")
            return []

    def update_product(self, product_id: int, **kwargs) -> bool:
        try:
            if not kwargs: return False
            
            # SQL query yasash (dynamic)
            set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(product_id)
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE products SET {set_clause} WHERE id = %s", tuple(values))
                    if cur.rowcount > 0:
                        logger.info(f"✅ Tovar yangilandi: ID {product_id}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
                    if cur.rowcount > 0:
                        logger.info(f"✅ Tovar o'chirildi: ID {product_id}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    def toggle_product_availability(self, product_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE products 
                        SET is_available = NOT is_available 
                        WHERE id = %s 
                        RETURNING is_available
                    """, (product_id,))
                    result = cur.fetchone()
                    if result:
                        status = "Mavjud" if result['is_available'] else "Mavjud emas"
                        logger.info(f"✅ Tovar statusi: {product_id} -> {status}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error toggling product: {e}")
            return False

    # ==================== ORDERS ====================

    def create_order(self, user_id: int, username: str, product_id: int,
                      customer_name: str, phone: str, address: str,
                      quantity: int = 1) -> Dict:
        try:
            order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO orders (order_number, user_id, username, product_id, customer_name, phone, address, quantity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *;
                    """, (order_number, user_id, username, product_id, customer_name, phone, address, quantity))
                    order = cur.fetchone()
                    order['created_at'] = str(order['created_at'])
                    logger.info(f"✅ Buyurtma yaratildi: {order_number}")
                    return dict(order)
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return {}

    def get_order(self, order_id: int) -> Optional[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
                    order = cur.fetchone()
                    if order:
                        order['created_at'] = str(order['created_at'])
                        return dict(order)
                    return None
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None

    def get_user_orders(self, user_id: int) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM orders 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC
                    """, (user_id,))
                    orders = cur.fetchall()
                    for o in orders: o['created_at'] = str(o['created_at'])
                    return [dict(o) for o in orders]
        except Exception as e:
            logger.error(f"Error getting user orders: {e}")
            return []

    def get_all_orders(self) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
                    orders = cur.fetchall()
                    for o in orders: o['created_at'] = str(o['created_at'])
                    return [dict(o) for o in orders]
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            return []

    def update_order_status(self, order_id: int, status: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
                    if cur.rowcount > 0:
                        logger.info(f"✅ Buyurtma statusi o'zgartirildi: {order_id} -> {status}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    # ==================== USERS ====================

    def add_user(self, user_id: int, username: str = None,
                 first_name: str = None, last_name: str = None) -> Dict:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Upsert (Insert or Update)
                    cur.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id) 
                        DO UPDATE SET 
                            username = EXCLUDED.username,
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name
                        RETURNING *;
                    """, (user_id, username, first_name, last_name))
                    user = cur.fetchone()
                    user['created_at'] = str(user['created_at'])
                    return dict(user)
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return {}

    def get_all_users(self) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users")
                    users = cur.fetchall()
                    for u in users: u['created_at'] = str(u['created_at'])
                    return [dict(u) for u in users]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def get_users_count(self) -> int:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as count FROM users")
                    return cur.fetchone()['count']
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0


# Global database obyekti (o'zgarmasdan qoladi)
db = JSONDatabase()
