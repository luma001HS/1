import asyncio
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
from aiogram.enums import ChatType

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Вставь сюда свой токен бота
BOT_TOKEN = "8122435242:AAEh8dBz0Sv7-j7f0sIbJTkooEBxZNOhXTA"
ADMIN_ID = 7646557774

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Файл для сохранения данных пользователей
DATA_FILE = "users_data.json"

# Редкости снюсов (от худшей к лучшей)
RARITIES = {
    "Обычный": {"emoji": "⚪", "color": "#808080", "drop_chance": 45},
    "Необычный": {"emoji": "🟢", "color": "#00FF00", "drop_chance": 30},
    "Редкий": {"emoji": "🔵", "color": "#0080FF", "drop_chance": 15},
    "Эпический": {"emoji": "🟣", "color": "#8000FF", "drop_chance": 8},
    "Легендарный": {"emoji": "🟡", "color": "#FFD700", "drop_chance": 2}
}

# Виды снюсов
SNUS_TYPES = [
    "Siberia", "Odens", "Skruf", "General", "Göteborgs Rapé","TON snus","Telegram snus"
    "Ettan", "Catch", "Nick & Johnny", "Thunder", "Kaliber","FAME snus ","Urban snus"
    "Lundgrens", "Kapten", "Kronan", "Prima Fint", "Granit","swag snus",
]

# Кейсы в магазине
CASES = {
    "Новичок": {"price": 500, "emoji": "📦", "description": "Простой кейс для начинающих"},
    "Средний": {"price": 1000, "emoji": "🎁", "description": "Хороший шанс на редкие снюсы"},
    "Премиум": {"price": 2500, "emoji": "💎", "description": "Максимальный шанс на легендарные снюсы"}
}

# Константы для каталога
CATALOG_ITEMS_PER_PAGE = 8

# Ежедневные бонусы (по дням)
DAILY_BONUSES = {
    1: {"coins": 100, "bonus": None},
    2: {"coins": 150, "bonus": None},
    3: {"coins": 200, "bonus": None},
    4: {"coins": 300, "bonus": None},
    5: {"coins": 400, "bonus": None},
    6: {"coins": 500, "bonus": None},
    7: {"coins": 700, "bonus": "free_case"}  # Бонусный кейс на 7 день
}

# Настройки рулетки
ROULETTE_MULTIPLIERS = {
    "💥": {"name": "Проигрыш", "multiplier": 0, "chance": 40, "color": "🔴"},
    "💰": {"name": "x1.5", "multiplier": 1.5, "chance": 30, "color": "🟡"},
    "💎": {"name": "x2", "multiplier": 2, "chance": 20, "color": "🔵"},
    "🚀": {"name": "x3", "multiplier": 3, "chance": 8, "color": "🟣"},
    "⭐": {"name": "x5", "multiplier": 5, "chance": 2, "color": "🟠"}
}


class UserData:
    def __init__(self):
        self.coins = 0
        self.inventory = {}  # {snus_name: {rarity: count}}
        self.last_free_snus = None
        self.last_coin_farm = None
        self.total_free_snus = 0
        self.active_trades = []
        self.daily_bonus_streak = 0
        self.last_daily_bonus = None
        self.total_roulette_games = 0
        self.roulette_wins = 0


def load_users_data() -> Dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Преобразуем данные в объекты UserData
                for user_id in data:
                    if isinstance(data[user_id], dict):
                        user_data = UserData()
                        user_data.__dict__.update(data[user_id])
                        data[user_id] = user_data
                return data
        except:
            pass
    return {}


def save_users_data(data: Dict):
    # Преобразуем объекты UserData в словари для сохранения
    save_data = {}
    for user_id, user_data in data.items():
        save_data[user_id] = user_data.__dict__

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)


users_data = load_users_data()


def get_user_data(user_id: int) -> UserData:
    if str(user_id) not in users_data:
        users_data[str(user_id)] = UserData()
    return users_data[str(user_id)]

def is_group_chat(message: types.Message) -> bool:
    """Проверяет, является ли чат группой"""
    return message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

def generate_random_snus():
    """Генерирует случайный снюс с учетом редкости"""
    rand = random.randint(1, 100)
    cumulative = 0

    for rarity, data in RARITIES.items():
        cumulative += data["drop_chance"]
        if rand <= cumulative:
            snus_type = random.choice(SNUS_TYPES)
            return snus_type, rarity

    # Fallback на обычный
    return random.choice(SNUS_TYPES), "Обычный"


def add_snus_to_inventory(user_data: UserData, snus_type: str, rarity: str):
    """Добавляет снюс в инвентарь пользователя"""
    if snus_type not in user_data.inventory:
        user_data.inventory[snus_type] = {}

    if rarity not in user_data.inventory[snus_type]:
        user_data.inventory[snus_type][rarity] = 0

    user_data.inventory[snus_type][rarity] += 1


def can_get_free_snus(user_data: UserData) -> bool:
    """Проверяет, может ли пользователь получить бесплатный снюс"""
    if not user_data.last_free_snus:
        return True

    if isinstance(user_data.last_free_snus, str):
        last_time = datetime.fromisoformat(user_data.last_free_snus)
    else:
        last_time = user_data.last_free_snus

    return datetime.now() - last_time >= timedelta(hours=1)


def can_get_daily_bonus(user_data: UserData) -> bool:
    """Проверяет, может ли пользователь получить ежедневный бонус"""
    if not user_data.last_daily_bonus:
        return True

    if isinstance(user_data.last_daily_bonus, str):
        last_time = datetime.fromisoformat(user_data.last_daily_bonus)
    else:
        last_time = user_data.last_daily_bonus

    # Проверяем, прошло ли более 20 часов с последнего бонуса
    return datetime.now() - last_time >= timedelta(hours=20)


def update_daily_streak(user_data: UserData):
    """Обновляет серию ежедневных бонусов"""
    now = datetime.now()

    if not user_data.last_daily_bonus:
        user_data.daily_bonus_streak = 1
    else:
        if isinstance(user_data.last_daily_bonus, str):
            last_time = datetime.fromisoformat(user_data.last_daily_bonus)
        else:
            last_time = user_data.last_daily_bonus

        hours_passed = (now - last_time).total_seconds() / 3600

        # Если прошло менее 48 часов - продолжаем серию
        if hours_passed <= 48:
            user_data.daily_bonus_streak += 1
            if user_data.daily_bonus_streak > 7:
                user_data.daily_bonus_streak = 1  # Сброс после 7 дня
        else:
            # Серия прервана
            user_data.daily_bonus_streak = 1

    user_data.last_daily_bonus = now


def can_farm_coins(user_data: UserData) -> bool:
    """Проверяет, может ли пользователь получить монеты"""
    if not user_data.last_coin_farm:
        return True

    if isinstance(user_data.last_coin_farm, str):
        last_time = datetime.fromisoformat(user_data.last_coin_farm)
    else:
        last_time = user_data.last_coin_farm

    return datetime.now() - last_time >= timedelta(minutes=30)


def spin_roulette(bet_amount):
    """Крутит рулетку и возвращает результат"""
    rand = random.randint(1, 100)
    cumulative = 0

    for symbol, data in ROULETTE_MULTIPLIERS.items():
        cumulative += data["chance"]
        if rand <= cumulative:
            multiplier = data["multiplier"]
            win_amount = int(bet_amount * multiplier)
            return symbol, data["name"], multiplier, win_amount, data["color"]

    # Fallback
    return "💥", "Проигрыш", 0, 0, "🔴"

def create_catalog_page(page: int = 0) -> tuple:
    """Создает страницу каталога с пагинацией"""
    total_pages = (len(SNUS_TYPES) - 1) // CATALOG_ITEMS_PER_PAGE + 1

    # Ограничиваем страницу
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1

    start_idx = page * CATALOG_ITEMS_PER_PAGE
    end_idx = min(start_idx + CATALOG_ITEMS_PER_PAGE, len(SNUS_TYPES))
    page_items = SNUS_TYPES[start_idx:end_idx]

    catalog_text = f"""
📚 <b>Каталог снюсов</b>

📊 Всего снюсов в игре: {len(SNUS_TYPES)}
📄 Страница {page + 1} из {total_pages}

🔸 <b>Доступные снюсы:</b>
"""

    for i, snus in enumerate(page_items, start_idx + 1):
        catalog_text += f"\n{i}. <b>{snus}</b>"
        # Показываем все возможные редкости для снюса
        rarities_text = " | ".join([f"{RARITIES[rarity]['emoji']}{rarity}" for rarity in RARITIES.keys()])
        catalog_text += f"\n   {rarities_text}"

    return catalog_text, page, total_pages


def create_catalog_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для навигации по каталогу"""
    keyboard = []

    # Кнопки навигации
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"catalog_page_{current_page - 1}"))
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"catalog_page_{current_page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка с информацией о редкостях
    keyboard.append([InlineKeyboardButton(text="💎 Информация о редкостях", callback_data="show_rarities_info")])

    # Кнопка обновления
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"catalog_page_{current_page}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_data = get_user_data(message.from_user.id)

    welcome_text = f"""
🎯 <b>Добро пожаловать в Снюс Коллекционер!</b> 🎯

Привет, {message.from_user.first_name}! 
Собирай уникальные виды снюсов и становись лучшим коллекционером!

🎮 <b>Доступные команды:</b>
/get - Получить бесплатный снюс (раз в час)
/profile - Твой профиль и коллекция
/catalog - Каталог всех снюсов в игре
/shop - Магазин кейсов
/farm - Получить монеты (раз в 30 мин)
/daily - Ежедневный бонус (каждые 20 часов)
/roulette - Снюс рулетка (делай ставки!)
/pay_reply - Перевод монет (ответь на сообщение)
/pay_id - Перевод монет по ID
/trade - Торговля с другими игроками

💎 <b>Редкости снюсов:</b>
⚪ Обычный - 45%
🟢 Необычный - 30% 
🔵 Редкий - 15%
🟣 Эпический - 8%
🟡 Легендарный - 2%

Удачи в коллекционировании! 🍀
    """

    await message.answer(welcome_text, parse_mode="HTML")
    save_users_data(users_data)


@dp.message(Command("get"))
async def get_free_snus(message: types.Message):
    user_data = get_user_data(message.from_user.id)

    if not can_get_free_snus(user_data):
        time_left = timedelta(hours=1) - (datetime.now() - datetime.fromisoformat(str(user_data.last_free_snus)))
        minutes_left = int(time_left.total_seconds() // 60)
        await message.answer(f"⏰ Подожди еще {minutes_left} минут до следующего бесплатного снюса!")
        return

    snus_type, rarity = generate_random_snus()
    add_snus_to_inventory(user_data, snus_type, rarity)
    user_data.last_free_snus = datetime.now()
    user_data.total_free_snus += 1

    rarity_emoji = RARITIES[rarity]["emoji"]

    text = f"""
🎁 <b>Поздравляю!</b> 

Ты получил: {rarity_emoji} <b>{snus_type}</b> ({rarity})

✨ Следующий бесплатный снюс через 1 час!
    """

    await message.answer(text, parse_mode="HTML")
    save_users_data(users_data)


@dp.message(Command("profile"))
async def show_profile(message: types.Message):
    user_data = get_user_data(message.from_user.id)

    # Подсчет общего количества снюсов
    total_snus = 0
    rarity_counts = {rarity: 0 for rarity in RARITIES.keys()}

    for snus_type, rarities in user_data.inventory.items():
        for rarity, count in rarities.items():
            total_snus += count
            if rarity in rarity_counts:
                rarity_counts[rarity] += count

    profile_text = f"""
👤 <b>Профиль {message.from_user.first_name}</b>
🆔 ID: {message.from_user.id}

💰 Монеты: {user_data.coins}
📦 Всего снюсов: {total_snus}
🎁 Бесплатных снюсов получено: {user_data.total_free_snus}

📊 <b>По редкостям:</b>
"""

    for rarity, count in rarity_counts.items():
        emoji = RARITIES[rarity]["emoji"]
        profile_text += f"{emoji} {rarity}: {count}\n"

    # Показываем топ-5 снюсов в коллекции
    if user_data.inventory:
        profile_text += "\n🏆 <b>Твоя коллекция:</b>\n"

        # Создаем список всех снюсов с их редкостями
        all_snus = []
        for snus_type, rarities in user_data.inventory.items():
            for rarity, count in rarities.items():
                all_snus.extend([(snus_type, rarity)] * count)

        # Группируем и показываем
        shown_count = 0
        shown_items = set()
        for snus_type, rarities in user_data.inventory.items():
            for rarity, count in rarities.items():
                if shown_count >= 10:  # Показываем максимум 10 позиций
                    break
                emoji = RARITIES[rarity]["emoji"]
                profile_text += f"{emoji} {snus_type} ({rarity}) x{count}\n"
                shown_count += 1
            if shown_count >= 10:
                break

        if total_snus > 10:
            profile_text += f"\n... и еще {total_snus - 10} снюсов"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_profile")]
    ])

    await message.answer(profile_text, parse_mode="HTML", reply_markup=keyboard)


@dp.message(Command("catalog"))
async def show_catalog(message: types.Message):
    """Показывает каталог всех снюсов в игре"""
    catalog_text, current_page, total_pages = create_catalog_page(0)
    keyboard = create_catalog_keyboard(current_page, total_pages)

    await message.answer(catalog_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("catalog_page_"))
async def catalog_page_handler(callback: CallbackQuery):
    """Обработчик навигации по страницам каталога"""
    try:
        page = int(callback.data.replace("catalog_page_", ""))
        catalog_text, current_page, total_pages = create_catalog_page(page)
        keyboard = create_catalog_keyboard(current_page, total_pages)

        await callback.message.edit_text(catalog_text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        await callback.answer("Ошибка при загрузке страницы!")


@dp.callback_query(F.data == "show_rarities_info")
async def show_rarities_info(callback: CallbackQuery):
    """Показывает подробную информацию о редкостях"""
    rarities_text = """
💎 <b>Информация о редкостях</b>

Каждый снюс может иметь одну из 5 редкостей:

"""

    for rarity, data in RARITIES.items():
        rarities_text += f"{data['emoji']} <b>{rarity}</b> - {data['drop_chance']}%\n"

    rarities_text += """
📈 <b>Шансы получения:</b>
• Бесплатный снюс (/get) - стандартные шансы
• Кейс "Новичок" - улучшенные шансы на редкие
• Кейс "Средний" - хорошие шансы на эпические  
• Кейс "Премиум" - шанс на легендарные!

💡 Собирай снюсы всех редкостей!
"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к каталогу", callback_data="catalog_page_0")]
    ])

    await callback.message.edit_text(rarities_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@dp.message(Command("daily"))
async def daily_bonus(message: types.Message):
    """Ежедневный бонус"""
    user_data = get_user_data(message.from_user.id)

    if not can_get_daily_bonus(user_data):
        time_left = timedelta(hours=20) - (datetime.now() - datetime.fromisoformat(str(user_data.last_daily_bonus)))
        hours_left = int(time_left.total_seconds() // 3600)
        minutes_left = int((time_left.total_seconds() % 3600) // 60)
        await message.answer(f"⏰ Следующий ежедневный бонус через {hours_left}ч {minutes_left}м!")
        return

    update_daily_streak(user_data)
    current_day = user_data.daily_bonus_streak
    bonus_data = DAILY_BONUSES[current_day]

    # Добавляем монеты
    user_data.coins += bonus_data["coins"]

    bonus_text = f"""
🎁 <b>Ежедневный бонус!</b>

📅 День {current_day}/7
💰 Получено: +{bonus_data["coins"]} монет
💳 Баланс: {user_data.coins} монет
"""

    # Бонусный кейс на 7 день
    if bonus_data["bonus"] == "free_case":
        snus_type, rarity = generate_random_snus()
        add_snus_to_inventory(user_data, snus_type, rarity)
        rarity_emoji = RARITIES[rarity]["emoji"]
        bonus_text += f"\n🎉 <b>БОНУС 7-го ДНЯ!</b>\n🎁 Бесплатный снюс: {rarity_emoji} {snus_type} ({rarity})"

    # Показываем прогресс до следующего дня
    if current_day < 7:
        next_bonus = DAILY_BONUSES[current_day + 1]["coins"]
        bonus_text += f"\n\n📈 Завтра: +{next_bonus} монет"
    else:
        bonus_text += f"\n\n🔄 Завтра серия начнется заново!"

    bonus_text += f"\n⏰ Следующий бонус через 20 часов"

    await message.answer(bonus_text, parse_mode="HTML")
    save_users_data(users_data)


@dp.message(Command("roulette"))
async def roulette_menu(message: types.Message):
    """Меню рулетки"""
    user_data = get_user_data(message.from_user.id)

    roulette_text = f"""
🎰 <b>Снюс Рулетка</b>

💰 Твои монеты: {user_data.coins}
🎮 Игр сыграно: {user_data.total_roulette_games}
🏆 Выигрышей: {user_data.roulette_wins}

🎯 <b>Шансы выигрыша:</b>
💥 Проигрыш - 40%
💰 x1.5 - 30%
💎 x2 - 20%  
🚀 x3 - 8%
⭐ x5 - 2%

💡 Выбери размер ставки:
"""

    # Создаем кнопки для ставок
    keyboard = []
    bet_amounts = [50, 100, 250, 500, 2000, 6700]

    for i in range(0, len(bet_amounts), 2):
        row = []
        for j in range(2):
            if i + j < len(bet_amounts):
                amount = bet_amounts[i + j]
                if user_data.coins >= amount:
                    row.append(InlineKeyboardButton(
                        text=f"💰 {amount} монет",
                        callback_data=f"roulette_bet_{amount}"
                    ))
                else:
                    row.append(InlineKeyboardButton(
                        text=f"❌ {amount} монет",
                        callback_data="insufficient_funds"
                    ))
        keyboard.append(row)

    # Кнопка для максимальной ставки
    if user_data.coins >= 1000:
        keyboard.append([InlineKeyboardButton(
            text=f"🔥 ВСЁ ИЛИ НИЧЕГО ({user_data.coins} монет)",
            callback_data=f"roulette_bet_{user_data.coins}"
        )])

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(roulette_text, parse_mode="HTML", reply_markup=keyboard_markup)


@dp.callback_query(F.data.startswith("roulette_bet_"))
async def roulette_spin(callback: CallbackQuery):
    """Крутит рулетку"""
    try:
        bet_amount = int(callback.data.replace("roulette_bet_", ""))
        user_data = get_user_data(callback.from_user.id)

        if user_data.coins < bet_amount:
            await callback.answer("Недостаточно монет!")
            return

        # Снимаем ставку
        user_data.coins -= bet_amount
        user_data.total_roulette_games += 1

        # Крутим рулетку
        symbol, name, multiplier, win_amount, color = spin_roulette(bet_amount)

        # Добавляем выигрыш
        user_data.coins += win_amount

        if win_amount > bet_amount:
            user_data.roulette_wins += 1

        # Создаем анимацию вращения
        spinning_text = """
🎰 <b>Рулетка крутится...</b>

💥 💰 💎 🚀 ⭐
💰 💎 🚀 ⭐ 💥  
💎 🚀 ⭐ 💥 💰
        """

        await callback.message.edit_text(spinning_text, parse_mode="HTML")
        await asyncio.sleep(2)  # Задержка для эффекта

        # Показываем результат
        if win_amount > bet_amount:
            result_text = f"""
🎉 <b>ВЫИГРЫШ!</b> 

🎰 Результат: {color} {symbol} {name}
💰 Ставка: {bet_amount} монет
🏆 Выигрыш: {win_amount} монет
📈 Прибыль: +{win_amount - bet_amount} монет

💳 Баланс: {user_data.coins} монет
"""
        elif win_amount == bet_amount:
            result_text = f"""
😐 <b>Возврат ставки</b>

🎰 Результат: {color} {symbol} {name}  
💰 Ставка: {bet_amount} монет
🔄 Возврат: {win_amount} монет

💳 Баланс: {user_data.coins} монет
"""
        else:
            result_text = f"""
💥 <b>Проигрыш!</b>

🎰 Результат: {color} {symbol} {name}
💰 Потеряно: {bet_amount} монет

💳 Баланс: {user_data.coins} монет
"""

        # Кнопки для продолжения
        keyboard = []
        if user_data.coins >= 50:
            keyboard.append([InlineKeyboardButton(text="🎰 Играть еще", callback_data="roulette_again")])

        keyboard.append([InlineKeyboardButton(text="📊 Статистика", callback_data="roulette_stats")])

        keyboard_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(result_text, parse_mode="HTML", reply_markup=keyboard_markup)

        save_users_data(users_data)

    except Exception as e:
        await callback.answer("Ошибка при обработке ставки!")

@dp.callback_query(F.data == "roulette_again")
async def roulette_again(callback: CallbackQuery):
    """Играть в рулетку еще раз"""
    user_data = get_user_data(callback.from_user.id)

    roulette_text = f"""
🎰 <b>Снюс Рулетка</b>

💰 Твои монеты: {user_data.coins}
🎮 Игр сыграно: {user_data.total_roulette_games}
🏆 Выигрышей: {user_data.roulette_wins}

🎯 <b>Шансы выигрыша:</b>
💥 Проигрыш - 40%
💰 x1.5 - 30%
💎 x2 - 20%  
🚀 x3 - 8%
⭐ x5 - 2%

💡 Выбери размер ставки:
"""

    # Создаем кнопки для ставок
    keyboard = []
    bet_amounts = [50, 100, 250, 500, 2000, 6700]

    for i in range(0, len(bet_amounts), 2):
        row = []
        for j in range(2):
            if i + j < len(bet_amounts):
                amount = bet_amounts[i + j]
                if user_data.coins >= amount:
                    row.append(InlineKeyboardButton(
                        text=f"💰 {amount} монет",
                        callback_data=f"roulette_bet_{amount}"
                    ))
                else:
                    row.append(InlineKeyboardButton(
                        text=f"❌ {amount} монет",
                        callback_data="insufficient_funds"
                    ))
        keyboard.append(row)

    # Кнопка для максимальной ставки
    if user_data.coins >= 1000:
        keyboard.append([InlineKeyboardButton(
            text=f"🔥 ВСЁ ИЛИ НИЧЕГО ({user_data.coins} монет)",
            callback_data=f"roulette_bet_{user_data.coins}"
        )])

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(roulette_text, parse_mode="HTML", reply_markup=keyboard_markup)
    await callback.answer()

@dp.message(Command("farm"))
async def farm_coins(message: types.Message):
    user_data = get_user_data(message.from_user.id)

    if not can_farm_coins(user_data):
        time_left = timedelta(minutes=30) - (datetime.now() - datetime.fromisoformat(str(user_data.last_coin_farm)))
        minutes_left = int(time_left.total_seconds() // 60)
        await message.answer(f"⏰ Подожди еще {minutes_left} минут до следующего фарма монет!")
        return

    coins_earned = random.randint(100, 250)
    user_data.coins += coins_earned
    user_data.last_coin_farm = datetime.now()

    text = f"""
💰 <b>Монеты получены!</b>

Ты заработал: +{coins_earned} монет
💳 Баланс: {user_data.coins} монет

⏰ Следующий фарм через 30 минут!
    """

    await message.answer(text, parse_mode="HTML")
    save_users_data(users_data)



@dp.message(Command("shop"))
async def show_shop(message: types.Message):
    user_data = get_user_data(message.from_user.id)

    shop_text = f"""
🛒 <b>Магазин кейсов</b>

💰 Твои монеты: {user_data.coins}

📦 <b>Доступные кейсы:</b>
"""

    keyboard_buttons = []
    for case_name, case_data in CASES.items():
        shop_text += f"\n{case_data['emoji']} <b>{case_name}</b> - {case_data['price']} монет\n"
        shop_text += f"   {case_data['description']}\n"

        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{case_data['emoji']} {case_name} ({case_data['price']} монет)",
                callback_data=f"buy_case_{case_name}"
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(shop_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("buy_case_"))
async def buy_case(callback: CallbackQuery):
    case_name = callback.data.replace("buy_case_", "")
    user_data = get_user_data(callback.from_user.id)

    if case_name not in CASES:
        await callback.answer("Неизвестный кейс!")
        return

    case_price = CASES[case_name]["price"]

    if user_data.coins < case_price:
        await callback.answer(f"Недостаточно монет! Нужно {case_price}, у тебя {user_data.coins}")
        return

    user_data.coins -= case_price

    # Генерируем снюс из кейса (улучшенные шансы для дорогих кейсов)
    if case_name == "Новичок":
        chances = {"Обычный": 50, "Необычный": 35, "Редкий": 15, "Эпический": 0, "Легендарный": 0}
    elif case_name == "Средний":
        chances = {"Обычный": 30, "Необычный": 40, "Редкий": 20, "Эпический": 10, "Легендарный": 0}
    else:  # Премиум
        chances = {"Обычный": 10, "Необычный": 30, "Редкий": 35, "Эпический": 20, "Легендарный": 5}

    rand = random.randint(1, 100)
    cumulative = 0
    selected_rarity = "Обычный"

    for rarity, chance in chances.items():
        cumulative += chance
        if rand <= cumulative:
            selected_rarity = rarity
            break

    snus_type = random.choice(SNUS_TYPES)
    add_snus_to_inventory(user_data, snus_type, selected_rarity)

    rarity_emoji = RARITIES[selected_rarity]["emoji"]
    case_emoji = CASES[case_name]["emoji"]

    result_text = f"""
🎉 <b>Кейс открыт!</b>

{case_emoji} Кейс: {case_name}
🎁 Получен: {rarity_emoji} <b>{snus_type}</b> ({selected_rarity})

💰 Остаток монет: {user_data.coins}
    """

    await callback.message.edit_text(result_text, parse_mode="HTML")
    await callback.answer(f"Поздравляю! Получен {selected_rarity} {snus_type}!")
    save_users_data(users_data)


@dp.message(Command("trade"))
async def trade_menu(message: types.Message):
    trade_text = """
🤝 <b>Торговля</b>

Здесь ты можешь обменяться снюсами с другими игроками!

📋 <b>Команды для торговли:</b>
/trade_offer @username - Предложить обмен пользователю
/trade_list - Посмотреть активные предложения
/trade_accept [ID] - Принять предложение обмена

💡 <b>Как это работает:</b>
1. Предложи обмен другому игроку
2. Выбери свои снюсы для обмена  
3. Дождись принятия предложения
4. Обмен завершен!
    """

    await message.answer(trade_text, parse_mode="HTML")


@dp.callback_query(F.data == "refresh_profile")
async def refresh_profile(callback: CallbackQuery):
    await callback.message.delete()
    await show_profile(callback.message)
    await callback.answer("Профиль обновлен!")


@dp.message(Command("admin_balance"))
async def admin_give_balance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        # Команда: /admin_balance 1000
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажи сумму: /admin_balance 1000")
            return

        amount = int(args[1])
        user_data = get_user_data(message.from_user.id)
        user_data.coins += amount

        await message.answer(f"✅ Добавлено {amount} монет!\n💰 Баланс: {user_data.coins}")
        save_users_data(users_data)

    except ValueError:
        await message.answer("❌ Неверная сумма!")


@dp.message(Command("admin_snus"))
async def admin_give_snus(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        # Команда: /admin_snus Siberia Легендарный 5
        args = message.text.split()
        if len(args) < 4:
            await message.answer(
                "❌ Формат: /admin_snus [тип] [редкость] [количество]\nПример: /admin_snus Siberia Легендарный 5")
            return

        snus_type = args[1]
        rarity = args[2]
        count = int(args[3])

        if snus_type not in SNUS_TYPES:
            await message.answer(f"❌ Неизвестный тип снюса: {snus_type}")
            return

        if rarity not in RARITIES:
            await message.answer(f"❌ Неизвестная редкость: {rarity}")
            return

        user_data = get_user_data(message.from_user.id)
        for _ in range(count):
            add_snus_to_inventory(user_data, snus_type, rarity)

        rarity_emoji = RARITIES[rarity]["emoji"]
        await message.answer(f"✅ Добавлено {count}x {rarity_emoji} {snus_type} ({rarity})")
        save_users_data(users_data)

    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат команды!")


@dp.message(Command("admin_help"))
async def admin_help(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    help_text = """
🔧 <b>Админ команды:</b>

/admin_balance [сумма] - Добавить монеты
/admin_snus [тип] [редкость] [кол-во] - Добавить снюс
/admin_help - Эта справка

<b>Примеры:</b>
/admin_balance 5000
/admin_snus Siberia Легендарный 3
    """

    await message.answer(help_text, parse_mode="HTML")

async def main():
    print("🤖 Снюс Коллекционер Бот запускается...")
    print("📝 Не забудь вставить свой BOT_TOKEN!")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("🔑 Проверь, что ты вставил правильный BOT_TOKEN")


@dp.message(Command("pay"))
async def pay_coins(message: types.Message):
    """Перевод монет другому игроку"""
    args = message.text.split()

    if len(args) < 3:
        await message.answer("""
💸 <b>Перевод монет</b>

📋 Формат: /pay @username сумма
📝 Пример: /pay @friend 500

💡 Переводи монеты другим игрокам!
        """, parse_mode="HTML")
        return

    try:
        username = args[1].replace("@", "").lower()
        amount = int(args[2])

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0!")
            return

        sender_data = get_user_data(message.from_user.id)

        if sender_data.coins < amount:
            await message.answer(f"❌ Недостаточно монет! У тебя: {sender_data.coins}")
            return

        # Ищем получателя по username
        recipient_id = None
        recipient_name = None

        for user_id_str, user_data in users_data.items():
            # Здесь мы не можем получить username из сохраненных данных
            # Поэтому будем использовать reply на сообщение получателя
            pass

        await message.answer(f"""
❌ <b>Перевод по username недоступен</b>

💡 Используй команду /pay_reply отвечая на сообщение игрока:
1. Ответь на сообщение игрока которому хочешь перевести
2. Напиши /pay_reply {amount}

Или используй /pay_id [ID] [сумма] если знаешь ID игрока
        """, parse_mode="HTML")

    except ValueError:
        await message.answer("❌ Неверная сумма!")


@dp.message(Command("pay_reply"))
async def pay_reply(message: types.Message):
    """Перевод монет через reply"""
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение игрока которому хочешь перевести монеты!")
        return

    args = message.text.split()

    if len(args) < 2:
        await message.answer("❌ Укажи сумму: /pay_reply 500")
        return

    try:
        amount = int(args[1])

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0!")
            return

        sender_data = get_user_data(message.from_user.id)
        recipient_id = message.reply_to_message.from_user.id
        recipient_name = message.reply_to_message.from_user.first_name

        if sender_data.coins < amount:
            await message.answer(f"❌ Недостаточно монет! У тебя: {sender_data.coins}")
            return

        if message.from_user.id == recipient_id:
            await message.answer("❌ Нельзя переводить монеты самому себе!")
            return

        # Выполняем перевод
        recipient_data = get_user_data(recipient_id)
        sender_data.coins -= amount
        recipient_data.coins += amount

        # Уведомления
        await message.answer(f"""
✅ <b>Перевод выполнен!</b>

💸 Переведено: {amount} монет
👤 Получатель: {recipient_name}
💰 Остаток: {sender_data.coins} монет
        """, parse_mode="HTML")

        # Уведомляем получателя если это не группа
        if not is_group_chat(message):
            try:
                await bot.send_message(
                    recipient_id,
                    f"""
🎁 <b>Получен перевод!</b>

💰 Сумма: +{amount} монет
👤 От: {message.from_user.first_name}
💳 Баланс: {recipient_data.coins} монет
                    """,
                    parse_mode="HTML"
                )
            except:
                pass  # Получатель заблокировал бота

        save_users_data(users_data)

    except ValueError:
        await message.answer("❌ Неверная сумма!")


@dp.message(Command("pay_id"))
async def pay_by_id(message: types.Message):
    """Перевод монет по ID"""
    args = message.text.split()

    if len(args) < 3:
        await message.answer("""
💸 <b>Перевод по ID</b>

📋 Формат: /pay_id [ID] [сумма]
📝 Пример: /pay_id 123456789 500

💡 ID можно узнать в профиле игрока
        """, parse_mode="HTML")
        return

    try:
        recipient_id = int(args[1])
        amount = int(args[2])

        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0!")
            return

        sender_data = get_user_data(message.from_user.id)

        if sender_data.coins < amount:
            await message.answer(f"❌ Недостаточно монет! У тебя: {sender_data.coins}")
            return

        if message.from_user.id == recipient_id:
            await message.answer("❌ Нельзя переводить монеты самому себе!")
            return

        # Проверяем существует ли получатель
        if str(recipient_id) not in users_data:
            await message.answer("❌ Игрок с таким ID не найден!")
            return

        # Выполняем перевод
        recipient_data = get_user_data(recipient_id)
        sender_data.coins -= amount
        recipient_data.coins += amount

        await message.answer(f"""
✅ <b>Перевод выполнен!</b>

💸 Переведено: {amount} монет
🆔 ID получателя: {recipient_id}
💰 Остаток: {sender_data.coins} монет
        """, parse_mode="HTML")

        # Уведомляем получателя
        try:
            await bot.send_message(
                recipient_id,
                f"""
🎁 <b>Получен перевод!</b>

💰 Сумма: +{amount} монет
👤 От: {message.from_user.first_name} (ID: {message.from_user.id})
💳 Баланс: {recipient_data.coins} монет
                """,
                parse_mode="HTML"
            )
        except:
            await message.answer("Дал жизни бомжу 🎡")

        save_users_data(users_data)

    except ValueError:
        await message.answer("❌ Неверный формат! Используй числа для ID и суммы")

if __name__ == "__main__":
    asyncio.run(main())