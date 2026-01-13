"""
Database bilan ishlash moduli - PostgreSQL versiya (Queue Logic)
Funksiya nomi 'get_random_products' lekin mantiq KETMA-KETLIK asosida ishlaydi.
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Optional, Dict, Any

import config 

logger = logging.getLogger(__name__)

class JSONDatabase:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.error("❌ DATABASE_URL topilmadi! Railway Variables ni tekshiring.")
            return

        self._create_tables()
        logger.info("✅ PostgreSQL Database initsializatsiya qilindi")

    def _get_connection(self):
        conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn

    def _create_tables(self):
        """Jadvallarni yaratish va yangilash"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Categories
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS categories (
                            name TEXT PRIMARY KEY
                        );
                    """)
                    
                    # Products
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

                    # --- MUHIM YANGILIK ---
                    # Navbat bilan chiqarish uchun yangi ustun qo'shamiz
                    cur.execute("""
                        ALTER TABLE products 
                        ADD COLUMN IF NOT EXISTS last_posted_at TIMESTAMP;
                    """)
                    # ----------------------

                    # Users
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

                    # Orders
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
                    
                    # Default categories
                    cur.execute("SELECT COUNT(*) as count FROM categories")
                    if cur.fetchone()['count'] == 0:
                        defaults = ["👕 Kiyimlar", "👟 Poyabzal", "🎒 Sumkalar", "⌚ Aksessuarlar", "📱 Elektronika", "🏠 Uy-ro'zg'or"]
                        for cat in defaults:
                            cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (cat,))
                            
        except Exception as e:
            logger.error(f"❌ Jadvallarni yaratishda xatolik: {e}")

    # ==================== LOGIKA O'ZGARGAN QISM ====================

    def get_random_products(self, count: int = 3) -> List[Dict]:
        """
        DIQQAT: Nomi 'random' bo'lgani bilan, aslida KETMA-KETLIK bo'yicha ishlaydi.
        Eng ko'p vaqt davomida chiqmagan tovarlarni oladi.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. Navbatdagi tovarlarni olish
                    # Logic: last_posted_at bo'sh bo'lganlar (yangi) yoki eng eski sana bo'lganlar birinchi chiqadi
                    cur.execute("""
                        SELECT * FROM products 
                        WHERE is_available = TRUE 
                        ORDER BY last_posted_at ASC NULLS FIRST
                        LIMIT %s
                    """, (count,))
                    
                    products = cur.fetchall()
                    
                    if not products:
                        return []

                    # 2. Vaqtni yangilash (Hozir chiqdi deb belgilash)
                    product_ids = tuple([p['id'] for p in products])
                    
                    if product_ids:
                        cur.execute("UPDATE products SET last_posted_at = NOW() WHERE id IN %s", (product_ids,))
                    
                    # 3. Formatlash
                    for p in products: 
                        p['created_at'] = str(p['created_at'])
                        if p.get('last_posted_at'):
                            p['last_posted_at'] = str(p['last_posted_at'])
                            
                    return [dict(p) for p in products]
                    
        except Exception as e:
            logger.error(f"Error getting next products: {e}")
            return []

    # ==================== QOLGAN QISMLAR (O'ZGARISHSIZ) ====================

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
            return True
        except psycopg2.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            return False

    def delete_category(self, category: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM categories WHERE name = %s", (category,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return False

    def update_category(self, old_name: str, new_name: str) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE categories SET name = %s WHERE name = %s", (new_name, old_name))
                    cur.execute("UPDATE products SET category = %s WHERE category = %s", (new_name, old_name))
                    return True
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return False

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
                    product['created_at'] = str(product['created_at'])
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
                    cur.execute("SELECT * FROM products WHERE category = %s AND is_available = TRUE", (category,))
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

    def update_product(self, product_id: int, **kwargs) -> bool:
        try:
            if not kwargs: return False
            set_clause = ", ".join([f"{key} = %s" for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(product_id)
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE products SET {set_clause} WHERE id = %s", tuple(values))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    def toggle_product_availability(self, product_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE products SET is_available = NOT is_available WHERE id = %s RETURNING is_available", (product_id,))
                    result = cur.fetchone()
                    return True if result else False
        except Exception as e:
            logger.error(f"Error toggling product: {e}")
            return False

    def create_order(self, user_id: int, username: str, product_id: int,
                      customer_name: str, phone: str, address: str, quantity: int = 1) -> Dict:
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
                    cur.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
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
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    def add_user(self, user_id: int, username: str = None,
                 first_name: str = None, last_name: str = None) -> Dict:
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id) 
                        DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name
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

# Global database obyekti
db = JSONDatabase()
