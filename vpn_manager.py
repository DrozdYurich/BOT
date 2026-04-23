import os
import qrcode
import random
import subprocess
from PIL import Image
from datetime import datetime

CONFIG_DIR = "vpn_configs"
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# Сервера
SERVERS = {
    1: {"name": "Россия", "endpoint": "ru.securevpn.com:51820", "public_key": "SERVER_PUBLIC_KEY_RU"},
    2: {"name": "Нидерланды", "endpoint": "nl.securevpn.com:51820", "public_key": "SERVER_PUBLIC_KEY_NL"},
    3: {"name": "Германия", "endpoint": "de.securevpn.com:51820", "public_key": "SERVER_PUBLIC_KEY_DE"},
    4: {"name": "США", "endpoint": "us.securevpn.com:51820", "public_key": "SERVER_PUBLIC_KEY_US"}
}

def generate_private_key():
    """Генерирует приватный ключ WireGuard"""
    try:
        return subprocess.check_output("wg genkey", shell=True).decode().strip()
    except:
        return f"PRIVATE_KEY_{random.randint(100000, 999999)}"

def generate_public_key(private_key):
    """Генерирует публичный ключ из приватного"""
    try:
        return subprocess.check_output(f"echo '{private_key}' | wg pubkey", shell=True).decode().strip()
    except:
        return f"PUBLIC_KEY_{random.randint(100000, 999999)}"

def generate_client_ip(user_id, server_id=1):
    """Генерирует IP для клиента"""
    ip_suffix = (user_id % 253) + 2
    return f"10.0.{server_id}.{ip_suffix}/32"

def generate_vpn_config(user_id, server_id=1):
    """Генерирует конфиг для указанного сервера"""
    
    private_key = generate_private_key()
    public_key = generate_public_key(private_key)
    client_ip = generate_client_ip(user_id, server_id)
    
    server = SERVERS.get(server_id, SERVERS[1])
    
    config_text = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}
DNS = 8.8.8.8, 1.1.1.1, 77.88.8.8
MTU = 1420

[Peer]
PublicKey = {server['public_key']}
Endpoint = {server['endpoint']}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    
    # Сохраняем файл
    filename = f"{CONFIG_DIR}/user_{user_id}_server_{server_id}.conf"
    with open(filename, "w") as f:
        f.write(config_text)
    
    # Создаём QR-код
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(config_text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_filename = f"{CONFIG_DIR}/user_{user_id}_server_{server_id}.png"
    qr_img.save(qr_filename)
    
    return {
        "private_key": private_key,
        "public_key": public_key,
        "ip": client_ip,
        "config_text": config_text,
        "config_file": filename,
        "qr_file": qr_filename,
        "server_id": server_id,
        "server_name": server['name']
    }

def delete_user_configs(user_id):
    """Удаляет все конфиги пользователя"""
    for file in os.listdir(CONFIG_DIR):
        if file.startswith(f"user_{user_id}"):
            os.remove(os.path.join(CONFIG_DIR, file))

def get_config_info(config_file):
    """Получает информацию о конфиге"""
    if not os.path.exists(config_file):
        return None
    
    with open(config_file, "r") as f:
        content = f.read()
    
    return {
        "content": content,
        "size": os.path.getsize(config_file),
        "created": datetime.fromtimestamp(os.path.getctime(config_file))
    }