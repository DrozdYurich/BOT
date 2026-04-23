import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

# ========== ПОДКЛЮЧЕНИЕ ==========
conn = sqlite3.connect("vpn_bot.db", check_same_thread=False)
cursor = conn.cursor()

# ========== СОЗДАНИЕ ВСЕХ ТАБЛИЦ ==========

# 1. Пользователи
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    referrer_id INTEGER,
    vpn_days INTEGER DEFAULT 0,
    subscription_end DATE,
    config_file TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id)
)
""")

# 2. Рефералы
cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    referred_id INTEGER UNIQUE,
    bonus_days INTEGER DEFAULT 3,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
    FOREIGN KEY (referred_id) REFERENCES users(user_id)
)
""")

# 3. Транзакции (оплаты)
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    days INTEGER,
    payment_method TEXT,
    payment_id TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

# 4. VPN конфиги
cursor.execute("""
CREATE TABLE IF NOT EXISTS vpn_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    private_key TEXT,
    public_key TEXT,
    ip_address TEXT,
    server_id INTEGER DEFAULT 1,
    config_text TEXT,
    qr_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

# 5. Сервера
cursor.execute("""
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    location TEXT,
    endpoint TEXT,
    public_key TEXT,
    ip_range TEXT,
    is_active BOOLEAN DEFAULT 1
)
""")

# 6. Уведомления
cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    message TEXT,
    is_read BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

# 7. Сессии (для безопасности)
cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_token TEXT UNIQUE,
    device_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
""")

conn.commit()

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ==========

def register_user(user_id: int, username: str, first_name: str, last_name: str = "", referrer_id: int = None):
    """Регистрация нового пользователя"""
    
    # Проверяем существование
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Обновляем last_login
        cursor.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (datetime.now(), user_id))
        conn.commit()
        return {"user": get_user_dict(existing), "bonus_applied": False}
    
    # Создаём нового пользователя
    subscription_end = (datetime.now() + timedelta(days=3)).date() if referrer_id else None
    
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name, last_name, referrer_id, vpn_days, subscription_end, last_login)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, first_name, last_name, referrer_id, 3 if referrer_id else 0, subscription_end, datetime.now()))
    
    # Если есть реферер, начисляем бонус
    bonus_applied = False
    if referrer_id and referrer_id != user_id:
        # Проверяем, не было ли уже реферала
        cursor.execute("SELECT * FROM referrals WHERE referred_id = ?", (user_id,))
        if not cursor.fetchone():
            # Начисляем бонус рефереру
            cursor.execute("UPDATE users SET vpn_days = vpn_days + 3 WHERE user_id = ?", (referrer_id,))
            
            # Записываем реферала
            cursor.execute("""
                INSERT INTO referrals (referrer_id, referred_id, bonus_days, status)
                VALUES (?, ?, ?, ?)
            """, (referrer_id, user_id, 3, 'active'))
            
            # Создаём уведомление для реферера
            add_notification(referrer_id, "🎉 Новый реферал!", f"Пользователь {first_name} присоединился по вашей ссылке! Вы получили +3 дня.")
            
            bonus_applied = True
    
    conn.commit()
    
    user = get_user(user_id)
    return {"user": user, "bonus_applied": bonus_applied}

def get_user_dict(user_tuple) -> Dict:
    """Преобразует кортеж пользователя в словарь"""
    if not user_tuple:
        return None
    
    return {
        "user_id": user_tuple[0],
        "username": user_tuple[1],
        "first_name": user_tuple[2],
        "last_name": user_tuple[3],
        "phone": user_tuple[4],
        "referrer_id": user_tuple[5],
        "vpn_days": user_tuple[6],
        "subscription_end": user_tuple[7],
        "config_file": user_tuple[8],
        "is_active": bool(user_tuple[9]),
        "created_at": user_tuple[10],
        "last_login": user_tuple[11]
    }

def get_user(user_id: int) -> Dict:
    """Получает данные пользователя"""
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Обновляем время последнего входа
        cursor.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (datetime.now(), user_id))
        conn.commit()
        return get_user_dict(user)
    return None

def update_user_phone(user_id: int, phone: str):
    """Обновляет номер телефона пользователя"""
    cursor.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
    conn.commit()

def add_vpn_days(user_id: int, days: int) -> int:
    """Добавляет дни подписки"""
    cursor.execute("UPDATE users SET vpn_days = vpn_days + ? WHERE user_id = ?", (days, user_id))
    
    # Обновляем дату окончания подписки
    cursor.execute("SELECT subscription_end FROM users WHERE user_id = ?", (user_id,))
    current_end = cursor.fetchone()[0]
    
    if current_end:
        new_end = datetime.strptime(current_end, "%Y-%m-%d").date() + timedelta(days=days)
    else:
        new_end = datetime.now().date() + timedelta(days=days)
    
    cursor.execute("UPDATE users SET subscription_end = ? WHERE user_id = ?", (new_end, user_id))
    conn.commit()
    
    cursor.execute("SELECT vpn_days FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

def remove_vpn_day(user_id: int) -> int:
    """Списывает один день"""
    cursor.execute("UPDATE users SET vpn_days = vpn_days - 1 WHERE user_id = ? AND vpn_days > 0", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT vpn_days FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========

def get_referral_stats(user_id: int) -> Dict:
    """Получает статистику рефералов"""
    # Количество приглашённых
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND status = 'active'", (user_id,))
    count = cursor.fetchone()[0]
    
    # Всего бонусных дней
    cursor.execute("SELECT SUM(bonus_days) FROM referrals WHERE referrer_id = ? AND status = 'active'", (user_id,))
    total_bonus = cursor.fetchone()[0] or 0
    
    # Список приглашённых
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name, r.created_at, r.bonus_days
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))
    referrals_list = cursor.fetchall()
    
    # Статистика по месяцам
    cursor.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*)
        FROM referrals
        WHERE referrer_id = ?
        GROUP BY month
        ORDER BY month DESC
    """, (user_id,))
    monthly_stats = cursor.fetchall()
    
    return {
        "count": count,
        "total_bonus": total_bonus,
        "list": referrals_list,
        "monthly": monthly_stats
    }

def get_top_referrers(limit: int = 10) -> List[Tuple]:
    """Топ пользователей по рефералам"""
    cursor.execute("""
        SELECT u.user_id, u.username, u.first_name, COUNT(r.id) as ref_count, SUM(r.bonus_days) as total_bonus
        FROM users u
        LEFT JOIN referrals r ON u.user_id = r.referrer_id AND r.status = 'active'
        GROUP BY u.user_id
        ORDER BY ref_count DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()

# ========== ПЛАТЕЖИ И ТРАНЗАКЦИИ ==========

def create_transaction(user_id: int, amount: int, days: int, payment_method: str = "test") -> int:
    """Создаёт новую транзакцию"""
    cursor.execute("""
        INSERT INTO transactions (user_id, amount, days, payment_method, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, amount, days, payment_method, 'pending', datetime.now()))
    conn.commit()
    return cursor.lastrowid

def update_transaction(transaction_id: int, status: str, payment_id: str = None):
    """Обновляет статус транзакции"""
    if payment_id:
        cursor.execute("""
            UPDATE transactions 
            SET status = ?, payment_id = ?, paid_at = ?
            WHERE id = ?
        """, (status, payment_id, datetime.now(), transaction_id))
    else:
        cursor.execute("""
            UPDATE transactions 
            SET status = ?, paid_at = ?
            WHERE id = ?
        """, (status, datetime.now(), transaction_id))
    conn.commit()

def complete_payment(transaction_id: int) -> bool:
    """Завершает оплату и начисляет дни"""
    cursor.execute("SELECT user_id, days, status FROM transactions WHERE id = ?", (transaction_id,))
    trans = cursor.fetchone()
    
    if not trans or trans[2] != 'pending':
        return False
    
    # Начисляем дни
    add_vpn_days(trans[0], trans[1])
    
    # Обновляем статус
    update_transaction(transaction_id, 'paid')
    
    # Создаём уведомление
    add_notification(trans[0], "✅ Оплата получена", f"Вам начислено {trans[1]} дней подписки!")
    
    return True

def get_user_transactions(user_id: int, limit: int = 10) -> List[Tuple]:
    """История транзакций пользователя"""
    cursor.execute("""
        SELECT id, amount, days, status, payment_method, created_at, paid_at
        FROM transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    return cursor.fetchall()

def get_total_earnings() -> Dict:
    """Общая статистика по оплатам"""
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM transactions WHERE status = 'paid'")
    count, total = cursor.fetchone()
    return {"count": count or 0, "total": total or 0}

# ========== VPN КОНФИГИ ==========

def save_vpn_config(user_id: int, config_data: Dict):
    """Сохраняет VPN конфиг"""
    cursor.execute("""
        INSERT OR REPLACE INTO vpn_configs 
        (user_id, private_key, public_key, ip_address, server_id, config_text, qr_code, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, config_data['private_key'], config_data['public_key'], 
          config_data['ip'], config_data.get('server_id', 1), 
          config_data['config_text'], config_data.get('qr_code', ''), datetime.now()))
    conn.commit()

def get_user_vpn_config(user_id: int) -> Dict:
    """Получает VPN конфиг пользователя"""
    cursor.execute("SELECT * FROM vpn_configs WHERE user_id = ?", (user_id,))
    config = cursor.fetchone()
    
    if config:
        return {
            "user_id": config[1],
            "private_key": config[2],
            "public_key": config[3],
            "ip_address": config[4],
            "server_id": config[5],
            "config_text": config[6],
            "qr_code": config[7],
            "created_at": config[8],
            "last_used": config[9]
        }
    return None

def update_config_usage(user_id: int):
    """Обновляет время последнего использования конфига"""
    cursor.execute("UPDATE vpn_configs SET last_used = ? WHERE user_id = ?", (datetime.now(), user_id))
    conn.commit()

# ========== УВЕДОМЛЕНИЯ ==========

def add_notification(user_id: int, title: str, message: str):
    """Добавляет уведомление пользователю"""
    cursor.execute("""
        INSERT INTO notifications (user_id, title, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, title, message, datetime.now()))
    conn.commit()

def get_notifications(user_id: int, unread_only: bool = True) -> List[Tuple]:
    """Получает уведомления пользователя"""
    if unread_only:
        cursor.execute("""
            SELECT id, title, message, created_at, is_read
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT id, title, message, created_at, is_read
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id,))
    return cursor.fetchall()

def mark_notification_read(notification_id: int):
    """Отмечает уведомление как прочитанное"""
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()

def mark_all_notifications_read(user_id: int):
    """Отмечает все уведомления как прочитанные"""
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

# ========== СТАТИСТИКА ДЛЯ АДМИНА ==========

def get_full_statistics() -> Dict:
    """Полная статистика для админа"""
    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE vpn_days > 0")
    active_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(vpn_days) FROM users")
    total_days = cursor.fetchone()[0] or 0
    
    # Рефералы
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE status = 'active'")
    total_refs = cursor.fetchone()[0]
    
    # Транзакции
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM transactions WHERE status = 'paid'")
    paid_count, paid_sum = cursor.fetchone()
    
    # Активность за последние 24 часа
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE last_login > datetime('now', '-1 day')
    """)
    active_24h = cursor.fetchone()[0]
    
    # За последние 7 дней
    cursor.execute("""
        SELECT COUNT(*) FROM users 
        WHERE created_at > datetime('now', '-7 days')
    """)
    new_week = cursor.fetchone()[0]
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_days": total_days,
        "total_refs": total_refs,
        "paid_count": paid_count or 0,
        "paid_sum": paid_sum or 0,
        "active_24h": active_24h,
        "new_week": new_week
    }

def get_all_users(page: int = 1, per_page: int = 20) -> Dict:
    """Список всех пользователей с пагинацией"""
    offset = (page - 1) * per_page
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT user_id, username, first_name, vpn_days, created_at, last_login
        FROM users
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    users = cursor.fetchall()
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": users
    }

# ========== СЕРВЕРА ==========

def add_server(name: str, location: str, endpoint: str, public_key: str, ip_range: str) -> int:
    """Добавляет новый сервер"""
    cursor.execute("""
        INSERT INTO servers (name, location, endpoint, public_key, ip_range)
        VALUES (?, ?, ?, ?, ?)
    """, (name, location, endpoint, public_key, ip_range))
    conn.commit()
    return cursor.lastrowid

def get_servers() -> List[Tuple]:
    """Получает список серверов"""
    cursor.execute("SELECT * FROM servers WHERE is_active = 1")
    return cursor.fetchall()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def check_subscription_status(user_id: int) -> Dict:
    """Проверяет статус подписки"""
    user = get_user(user_id)
    if not user:
        return {"has_subscription": False, "days_left": 0}
    
    return {
        "has_subscription": user['vpn_days'] > 0,
        "days_left": user['vpn_days'],
        "expires_at": user['subscription_end']
    }

def get_leaderboard(limit: int = 10) -> List[Tuple]:
    """Таблица лидеров по дням подписки"""
    cursor.execute("""
        SELECT user_id, username, first_name, vpn_days
        FROM users
        WHERE vpn_days > 0
        ORDER BY vpn_days DESC
        LIMIT ?
    """, (limit,))
    return cursor.fetchall()
# Добавь это в конец database.py

def get_user_dict(user_tuple):
    """Преобразует кортеж пользователя в словарь"""
    if not user_tuple:
        return None
    
    return {
        "user_id": user_tuple[0],
        "username": user_tuple[1],
        "first_name": user_tuple[2],
        "last_name": user_tuple[3],
        "phone": user_tuple[4],
        "referrer_id": user_tuple[5],
        "vpn_days": user_tuple[6],
        "subscription_end": user_tuple[7],
        "config_file": user_tuple[8],
        "is_active": bool(user_tuple[9]) if user_tuple[9] is not None else True,
        "created_at": user_tuple[10],
        "last_login": user_tuple[11]
    }
print("✅ База данных SQLite готова!")