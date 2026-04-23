import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Информация о VPN сервисе
VPN_INFO = {
    "name": "SecureVPN",
    "version": "2.0",
    "servers": ["Россия", "Нидерланды", "Германия", "США"],
    "protocols": ["WireGuard", "OpenVPN"],
    "speed": "до 1 Гбит/с",
    "devices": 5,
    "money_back": "3 дня"
}

# Цены
PRICES = {
    7: 150,    # 7 дней - 150 руб
    30: 500,   # 30 дней - 500 руб
    90: 1200,  # 90 дней - 1200 руб
    365: 4000  # 365 дней - 4000 руб
}