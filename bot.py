import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    FSInputFile, CallbackQuery, Message
)
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID, VPN_INFO, PRICES
from database import (
    register_user, get_user, add_vpn_days, remove_vpn_day,
    get_referral_stats, get_user_transactions, create_transaction,
    complete_payment, get_notifications, add_notification,
    mark_notification_read, mark_all_notifications_read,
    get_full_statistics, get_all_users, get_leaderboard,
    check_subscription_status, update_user_phone
)
from vpn_manager import generate_vpn_config, delete_user_configs, SERVERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== КЛАВИАТУРЫ ==========

def main_keyboard():
    """Главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Получить VPN", callback_data="get_vpn")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
        [InlineKeyboardButton(text="🌍 Выбрать сервер", callback_data="select_server")],
        [InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton(text="💳 Купить дни", callback_data="buy_days")],
        [InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ])

def profile_keyboard(user_days):
    """Клавиатура личного кабинета"""
    kb = [
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="💰 История платежей", callback_data="payment_history")],
        [InlineKeyboardButton(text="🔧 Сменить сервер", callback_data="change_server")],
        [InlineKeyboardButton(text="📱 Мои устройства", callback_data="my_devices")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="notifications")],
        [InlineKeyboardButton(text="📞 Связаться с поддержкой", url="https://t.me/support_username")],
    ]
    
    if user_days > 0:
        kb.insert(2, [InlineKeyboardButton(text="✅ Продлить подписку", callback_data="buy_days")])
    
    kb.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def server_keyboard():
    """Клавиатура выбора сервера"""
    kb = []
    for server_id, server in SERVERS.items():
        kb.append([InlineKeyboardButton(text=f"🌍 {server['name']}", callback_data=f"server_{server_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_keyboard():
    """Клавиатура выбора тарифов"""
    kb = []
    for days, price in PRICES.items():
        kb.append([InlineKeyboardButton(text=f"📦 {days} дней — {price} ₽", callback_data=f"pay_{days}_{price}")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(CommandStart())
async def start_command(message: Message):
    """Обработка /start с поддержкой рефералов"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    # Проверяем реферальный параметр
    args = message.text.split()
    referrer_id = None
    
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id:
            referrer_id = ref_id
    
    # Регистрируем пользователя
    result = register_user(user_id, username, first_name, last_name, referrer_id)
    
    # Формируем приветствие
    welcome_text = f"""
🌍 *Добро пожаловать в {VPN_INFO['name']}!*

🔒 *Ваш персональный VPN сервис*
• Скорость: {VPN_INFO['speed']}
• Серверов: {len(VPN_INFO['servers'])}
• Устройств: до {VPN_INFO['devices']}
• Возврат средств: {VPN_INFO['money_back']}

🎁 *Бонус:* При регистрации вы получаете {3 if referrer_id else 0} дня подписки!

📌 *Купить подписку:* нажмите 💳 Купить дни
📌 *Получить VPN:* нажмите 🔐 Получить VPN
"""
    
    if result.get('bonus_applied'):
        welcome_text += "\n\n✨ *+3 дня за приглашение!* ✨"
    
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_keyboard())

@dp.message(Command("admin"))
async def admin_command(message: Message):
    """Админ панель"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён")
        return
    
    stats = get_full_statistics()
    
    admin_text = f"""
🔐 *Админ панель*

📊 *Статистика:*
• 👥 Всего пользователей: *{stats['total_users']}*
• 🟢 Активных: *{stats['active_users']}*
• 📆 Активны сегодня: *{stats['active_24h']}*
• 🆕 За неделю: *{stats['new_week']}*

💰 *Финансы:*
• Всего оплат: *{stats['paid_count']}*
• Сумма: *{stats['paid_sum']} ₽*

👥 *Рефералы:*
• Всего: *{stats['total_refs']}*

📆 *Дней в системе:* *{stats['total_days']}*
"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Полная статистика", callback_data="admin_full_stats")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎁 Выдать дни", callback_data="admin_give_days")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_main")]
    ])
    
    await message.answer(admin_text, parse_mode="Markdown", reply_markup=kb)

# ========== ЛИЧНЫЙ КАБИНЕТ ==========

@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показывает личный кабинет"""
    user = get_user(callback.from_user.id)
    
    if not user:
        await callback.message.answer("Ошибка: пользователь не найден")
        return
    
    profile_text = f"""
👤 *Личный кабинет*

📌 *Основная информация:*
• ID: `{user['user_id']}`
• Имя: {user['first_name']}
• Username: @{user['username'] or 'не указан'}

📆 *Подписка:*
• Дней осталось: *{user['vpn_days']}*
• Действует до: {user['subscription_end'] or 'не активна'}
• Статус: {'✅ Активна' if user['vpn_days'] > 0 else '❌ Не активна'}
"""
    
    await callback.message.answer(
        profile_text,
        parse_mode="Markdown",
        reply_markup=profile_keyboard(user['vpn_days'])
    )
    await callback.answer()

@dp.callback_query(F.data == "my_stats")
async def show_my_stats(callback: CallbackQuery):
    """Показывает детальную статистику пользователя"""
    user = get_user(callback.from_user.id)
    ref_stats = get_referral_stats(callback.from_user.id)
    user_transactions = get_user_transactions(callback.from_user.id, 5)
    
    stats_text = f"""
📊 *Ваша статистика*

📅 *Регистрация:* {user['created_at'][:10] if user['created_at'] else 'неизвестно'}
🕐 *Последний вход:* {user['last_login'][:16] if user['last_login'] else 'сегодня'}

👥 *Рефералы:*
• Приглашено друзей: *{ref_stats['count']}*
• Заработано дней: *{ref_stats['total_bonus']}*

💰 *Платежи:*
• Всего транзакций: *{len(user_transactions)}*
• Успешных: *{sum(1 for t in user_transactions if t[3] == 'paid')}*

🎯 *Лидеры:*
• Пригласите друзей, чтобы попасть в топ!
"""
    
    await callback.message.answer(stats_text, parse_mode="Markdown", reply_markup=profile_keyboard(user['vpn_days']))
    await callback.answer()

@dp.callback_query(F.data == "payment_history")
async def show_payment_history(callback: CallbackQuery):
    """Показывает историю платежей"""
    user_id = callback.from_user.id
    transactions = get_user_transactions(user_id, 10)
    
    if not transactions:
        await callback.message.answer(
            "💰 *История платежей*\n\nУ вас пока нет платежей.\n\nКупите подписку в разделе 💳 Купить дни",
            parse_mode="Markdown",
            reply_markup=profile_keyboard(get_user(user_id)['vpn_days'])
        )
        await callback.answer()
        return
    
    history_text = "💰 *История платежей*\n\n"
    
    for trans in transactions:
        status_emoji = "✅" if trans[3] == "paid" else "⏳"
        date = trans[5][:10] if trans[5] else "дата неизвестна"
        history_text += f"{status_emoji} {date}: {trans[2]} дней — {trans[1]} ₽ ({trans[3]})\n"
    
    if len(transactions) >= 10:
        history_text += "\n*Показаны последние 10 платежей*"
    
    await callback.message.answer(history_text, parse_mode="Markdown", reply_markup=profile_keyboard(get_user(user_id)['vpn_days']))
    await callback.answer()

@dp.callback_query(F.data == "change_server")
async def change_server_menu(callback: CallbackQuery):
    """Меню смены сервера"""
    await callback.message.answer(
        "🌍 *Выберите сервер*\n\n"
        "Вы можете выбрать сервер в любой момент. "
        "Конфиг будет сгенерирован заново для выбранного сервера.",
        parse_mode="Markdown",
        reply_markup=server_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "my_devices")
async def show_my_devices(callback: CallbackQuery):
    """Показывает активные устройства"""
    user = get_user(callback.from_user.id)
    
    devices_text = f"""
📱 *Ваши устройства*

У вас есть возможность подключить до {VPN_INFO['devices']} устройств одновременно.

*Как подключить новое устройство:*
1. Установите WireGuard на новом устройстве
2. Нажмите 🔐 Получить VPN
3. Скачайте конфиг или отсканируйте QR-код

*Активные подключения:*
• Telegram Bot (текущее устройство)

📌 *Совет:* Используйте один конфиг на всех устройствах
"""
    
    await callback.message.answer(devices_text, parse_mode="Markdown", reply_markup=profile_keyboard(user['vpn_days']))
    await callback.answer()

@dp.callback_query(F.data == "notifications")
async def show_notifications(callback: CallbackQuery):
    """Показывает уведомления"""
    user_id = callback.from_user.id
    notifications = get_notifications(user_id, unread_only=True)
    user = get_user(user_id)
    
    if not notifications:
        await callback.message.answer(
            "🔔 *Уведомления*\n\nУ вас нет непрочитанных уведомлений",
            parse_mode="Markdown",
            reply_markup=profile_keyboard(user['vpn_days'])
        )
        await callback.answer()
        return
    
    notif_text = "🔔 *Ваши уведомления*\n\n"
    
    for notif in notifications:
        notif_text += f"📌 *{notif[1]}*\n{notif[2]}\n📅 {notif[3][:10]}\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отметить все прочитанными", callback_data="mark_all_read")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")]
    ])
    
    await callback.message.answer(notif_text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "mark_all_read")
async def mark_all_read(callback: CallbackQuery):
    """Отмечает все уведомления прочитанными"""
    mark_all_notifications_read(callback.from_user.id)
    await callback.message.answer("✅ Все уведомления отмечены как прочитанные")
    await callback.answer()

# ========== ВЫБОР СЕРВЕРА ==========

@dp.callback_query(F.data.startswith("server_"))
async def select_server(callback: CallbackQuery):
    """Выбор сервера"""
    server_id = int(callback.data.split("_")[1])
    server_name = SERVERS[server_id]['name']
    
    # Сохраняем выбранный сервер для пользователя (можно добавить в БД)
    await callback.message.answer(
        f"✅ Выбран сервер: *{server_name}*\n\n"
        f"Теперь нажмите 🔐 Получить VPN, чтобы получить конфиг для этого сервера",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "select_server")
async def select_server_menu(callback: CallbackQuery):
    """Меню выбора сервера"""
    await callback.message.answer(
        "🌍 *Выберите сервер*\n\n"
        "Сервер влияет на:\n"
        "• 🌐 Ваш IP-адрес\n"
        "• ⚡ Скорость соединения\n"
        "• 🔓 Доступ к региональному контенту\n\n"
        "*Рекомендации:*\n"
        "• Россия — для обхода блокировок\n"
        "• Нидерланды/Германия — для Европы\n"
        "• США — для американского контента",
        parse_mode="Markdown",
        reply_markup=server_keyboard()
    )
    await callback.answer()

# ========== ПОЛУЧЕНИЕ VPN ==========

@dp.callback_query(F.data == "get_vpn")
async def get_vpn(callback: CallbackQuery):
    """Выдача VPN конфига"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if not user or user['vpn_days'] <= 0:
        await callback.message.answer(
            "❌ *Нет активных дней подписки!*\n\n"
            "Пополните баланс в разделе 💳 *Купить дни*\n"
            "Или пригласите друзей в разделе 👥 *Реферальная система*",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.answer("⏳ *Генерирую VPN конфиг...*\n\nЭто может занять несколько секунд", parse_mode="Markdown")
    
    try:
        # Генерируем конфиг (по умолчанию сервер 1 - Россия)
        config_data = generate_vpn_config(user_id, server_id=1)
        
        # Отправляем конфиг файлом
        config_doc = FSInputFile(config_data['config_file'])
        await callback.message.answer_document(
            config_doc,
            caption=f"✅ *Ваш VPN конфиг*\n\n"
                   f"🌍 Сервер: {config_data['server_name']}\n"
                   f"📆 Осталось дней: {user['vpn_days']}\n"
                   f"🔑 IP: {config_data['ip']}\n\n"
                   f"📱 *Импортируйте файл в приложение WireGuard*",
            parse_mode="Markdown"
        )
        
        # Отправляем QR-код
        qr_photo = FSInputFile(config_data['qr_file'])
        await callback.message.answer_photo(
            qr_photo,
            caption="📱 *Или отсканируйте QR-код*\n\n"
                   "*Как использовать:*\n"
                   "1. Установите WireGuard\n"
                   "2. Нажмите + → Импорт из файла или QR\n"
                   "3. Включите тумблер для подключения",
            parse_mode="Markdown"
        )
        
        # Спрашиваем про списание дня
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, я подключился", callback_data="confirm_use")],
            [InlineKeyboardButton(text="❌ Пока не использовал", callback_data="back_main")]
        ])
        
        await callback.message.answer(
            "🔐 *Готово!*\n\n"
            "Вы подключились к VPN?\n"
            "Подтвердите использование, чтобы списать 1 день",
            parse_mode="Markdown",
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Ошибка генерации конфига: {e}")
        await callback.message.answer(f"❌ Ошибка: {str(e)}\n\nПожалуйста, попробуйте позже или обратитесь в поддержку")
    
    await callback.answer()

@dp.callback_query(F.data == "confirm_use")
async def confirm_use_vpn(callback: CallbackQuery):
    """Подтверждение использования VPN"""
    user_id = callback.from_user.id
    remaining = remove_vpn_day(user_id)
    
    await callback.message.answer(
        f"✅ *Подтверждено!*\n\n"
        f"Списано 1 день\n"
        f"📆 Осталось дней: {remaining}\n\n"
        f"🔒 Ваше соединение защищено!\n"
        f"🌐 Вы можете безопасно пользоваться интернетом",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    await callback.answer()

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========

@dp.callback_query(F.data == "referral")
async def show_referral_system(callback: CallbackQuery):
    """Показывает реферальную систему"""
    user_id = callback.from_user.id
    ref_stats = get_referral_stats(user_id)
    
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    referral_text = f"""
👥 *Реферальная программа*

🎁 *Как это работает:*
1️⃣ Вы приглашаете друга по ссылке
2️⃣ Друг регистрируется
3️⃣ Вы получаете *+3 дня* подписки
4️⃣ Друг получает *3 дня* бесплатно

📊 *Ваша статистика:*
• Приглашено друзей: *{ref_stats['count']}*
• Заработано дней: *{ref_stats['total_bonus']}*

🔗 *Ваша ссылка:*
`{referral_link}`

🏆 *Топ приглашений обновляется ежедневно*
"""
    
    # Топ рефереров
    top = get_leaderboard(5)
    if top:
        referral_text += "\n\n🏆 *Топ пользователей:*\n"
        for i, t in enumerate(top, 1):
            referral_text += f"{i}. @{t[1] or 'user'} — {t[3]} дней\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={referral_link}&text=Привет! Используй мой VPN бот, получи 3 дня бесплатно!")],
        [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data="copy_link")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])
    
    await callback.message.answer(referral_text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "copy_link")
async def copy_referral_link(callback: CallbackQuery):
    """Отправляет ссылку для копирования"""
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={callback.from_user.id}"
    await callback.message.answer(f"🔗 *Ваша ссылка:*\n`{link}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "my_referrals")
async def show_my_referrals(callback: CallbackQuery):
    """Показывает список приглашённых"""
    ref_stats = get_referral_stats(callback.from_user.id)
    
    if not ref_stats['list']:
        await callback.message.answer(
            "👥 *Мои рефералы*\n\n"
            "Вы пока никого не пригласили.\n"
            "Поделитесь своей ссылкой с друзьями!",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        await callback.answer()
        return
    
    ref_text = "👥 *Мои рефералы*\n\n"
    
    for ref in ref_stats['list']:
        ref_text += f"• @{ref[1] or ref[2]} — +{ref[4]} дней ({ref[3][:10]})\n"
    
    if len(ref_stats['list']) > 10:
        ref_text += f"\n*И ещё {len(ref_stats['list']) - 10} человек*"
    
    await callback.message.answer(ref_text, parse_mode="Markdown", reply_markup=main_keyboard())
    await callback.answer()

# ========== ОПЛАТА ==========

@dp.callback_query(F.data == "buy_days")
async def show_payment_options(callback: CallbackQuery):
    """Показывает варианты оплаты"""
    await callback.message.answer(
        "💳 *Выберите тариф*\n\n"
        "💰 *Доступные пакеты:*\n"
        "📦 7 дней — 150 ₽\n"
        "⭐ 30 дней — 500 ₽\n"
        "💎 90 дней — 1200 ₽\n"
        "🌟 365 дней — 4000 ₽\n\n"
        "⚡ *Способы оплаты:*\n"
        "• Банковская карта\n"
        "• СБП\n"
        "• Криптовалюта (USDT/TON)\n\n"
        "✅ *После оплаты дни добавляются автоматически*",
        parse_mode="Markdown",
        reply_markup=payment_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    """Обработка оплаты"""
    parts = callback.data.split("_")
    days = int(parts[1])
    amount = int(parts[2])
    
    user_id = callback.from_user.id
    
    # Создаём транзакцию в базе данных
    transaction_id = create_transaction(user_id, amount, days, "test")
    
    # В этом месте должна быть интеграция с реальной платёжной системой
    # Сейчас для теста просто начисляем дни
    
    await callback.message.answer(
        f"🔄 *Обработка платежа...*\n\n"
        f"💰 Сумма: {amount} ₽\n"
        f"📆 Дней: {days}\n"
        f"🆔 Транзакция: #{transaction_id}\n\n"
        f"⏳ Пожалуйста, подождите...",
        parse_mode="Markdown"
    )
    
    # Имитация обработки платежа
    await asyncio.sleep(2)
    
    # Завершаем оплату и начисляем дни
    success = complete_payment(transaction_id)
    
    if success:
        user = get_user(user_id)
        await callback.message.answer(
            f"✅ *Оплата выполнена успешно!*\n\n"
            f"💰 Сумма: *{amount} ₽*\n"
            f"➕ Добавлено дней: *{days}*\n"
            f"📆 Ваш баланс: *{user['vpn_days']} дней*\n\n"
            f"Теперь вы можете получить VPN конфиг в главном меню",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        
        # Отправляем уведомление админу
        await bot.send_message(
            ADMIN_ID,
            f"💵 *Новая оплата*\n"
            f"👤 Пользователь: {callback.from_user.id}\n"
            f"👤 Имя: {callback.from_user.first_name}\n"
            f"💰 Сумма: {amount} ₽\n"
            f"📆 Дней: {days}\n"
            f"🆔 Транзакция: #{transaction_id}",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            f"❌ *Ошибка платежа*\n\n"
            f"Пожалуйста, попробуйте позже или обратитесь в поддержку",
            parse_mode="Markdown"
        )
    
    await callback.answer()

# ========== О СЕРВИСЕ И ПОМОЩЬ ==========

@dp.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery):
    """Показывает информацию о сервисе"""
    about_text = f"""
ℹ️ *О сервисе {VPN_INFO['name']}*

🔒 *Что мы предлагаем:*
• Анонимный и безопасный интернет
• Высокая скорость до {VPN_INFO['speed']}
• {len(VPN_INFO['servers'])} серверов по всему миру
• Поддержка всех устройств

🛡️ *Наши преимущества:*
• Без логов (no-logs policy)
• Безлимитный трафик
• Защита от утечек DNS
• Автоматический kill-switch

🌍 *Сервера:*
• {', '.join(VPN_INFO['servers'])}

📱 *Поддерживаемые устройства:*
• Windows, Mac, Linux
• Android, iOS
• Роутеры с поддержкой WireGuard

⏱️ *Гарантия:* {VPN_INFO['money_back']}

📞 *Поддержка:* 24/7
"""
    
    await callback.message.answer(about_text, parse_mode="Markdown", reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показывает помощь"""
    help_text = """
❓ *Помощь и инструкция*

📖 *Как пользоваться ботом:*

1️⃣ *Пополнить баланс*
   → Нажмите 💳 Купить дни
   → Выберите тариф
   → Оплатите

2️⃣ *Получить VPN*
   → Нажмите 🔐 Получить VPN
   → Скачайте .conf файл
   → Импортируйте в WireGuard

3️⃣ *Установка WireGuard:*
   • Windows: wireguard.com/install
   • Mac: App Store
   • Android: Google Play
   • iOS: App Store
   • Linux: sudo apt install wireguard

4️⃣ *Как импортировать конфиг:*
   → Откройте WireGuard
   → Нажмите "Add Tunnel"
   → Выберите файл .conf
   → Нажмите "Activate"

5️⃣ *Проверка подключения:*
   → Перейдите на ipleak.net
   → Ваш IP должен измениться
   → DNS должен показывать ваш регион

🔧 *Частые проблемы:*
• Не подключается? → Смените сервер
• Медленная скорость? → Выберите ближайший сервер
• Нет интернета? → Отключите и включите VPN

📞 *Поддержка:* @support_username
"""
    
    await callback.message.answer(help_text, parse_mode="Markdown", reply_markup=main_keyboard())
    await callback.answer()

# ========== АДМИН-ФУНКЦИИ ==========

@dp.callback_query(F.data == "admin_full_stats")
async def admin_full_stats(callback: CallbackQuery):
    """Полная статистика для админа"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    stats = get_full_statistics()
    
    stats_text = f"""
📊 *Полная статистика*

👥 *Пользователи:*
• Всего: {stats['total_users']}
• Активных: {stats['active_users']}
• Сегодня: {stats['active_24h']}
• За неделю: {stats['new_week']}

💰 *Финансы:*
• Платежей: {stats['paid_count']}
• Сумма: {stats['paid_sum']} ₽
• Средний чек: {stats['paid_sum'] // stats['paid_count'] if stats['paid_count'] > 0 else 0} ₽

👥 *Рефералы:*
• Всего связей: {stats['total_refs']}
• В среднем на пользователя: {stats['total_refs'] / stats['total_users'] if stats['total_users'] > 0 else 0:.1f}

📆 *Система:*
• Всего дней: {stats['total_days']}
• Средний баланс: {stats['total_days'] / stats['total_users'] if stats['total_users'] > 0 else 0:.1f} дней
"""
    
    await callback.message.answer(stats_text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.answer("🌍 *Главное меню*", parse_mode="Markdown", reply_markup=main_keyboard())
    await callback.answer()

# ========== ЗАПУСК ==========

async def main():
    """Запуск бота"""
    print("🚀 Бот запускается...")
    print("✅ База данных подключена")
    print(f"🤖 Бот: @{(await bot.get_me()).username}")
    print("💬 Напишите /start в Telegram")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())