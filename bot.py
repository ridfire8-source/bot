import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# -----------------------------
# Настройки бота
# -----------------------------
TOKEN = "8505130329:AAEkutlvSTEp6CiSH8j_Ps-RCM1Ay6MXMUk"
ADMIN_ID = 7230440657
CHANNEL_USERNAME = "@fitestbo"

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# -----------------------------
# База данных SQLite
# -----------------------------
conn = sqlite3.connect("codes.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    title TEXT
)
""")
conn.commit()

# -----------------------------
# FSM состояния для админа
# -----------------------------
class AdminStates(StatesGroup):
    waiting_for_add = State()
    waiting_for_delete = State()

# -----------------------------
# Проверка подписки на канал
# -----------------------------
async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "creator", "administrator"]:
            return True
        else:
            return False
    except:
        return False

# -----------------------------
# Стартовый хэндлер
# -----------------------------
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    await msg.answer(
        "Привет! Это бот поиска фильмов/сериалов/аниме по коду.\n"
        f"Перед использованием убедись, что подписан на {CHANNEL_USERNAME}.\n"
        "Отправь код фильма, чтобы узнать название."
    )

# -----------------------------
# Админка
# -----------------------------
@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ У тебя нет доступа к админ-панели.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить код", callback_data="admin_add")],
            [InlineKeyboardButton(text="📄 Просмотреть коды", callback_data="admin_view")],
            [InlineKeyboardButton(text="❌ Удалить код", callback_data="admin_delete")]
        ]
    )
    await msg.answer("Админ-панель:", reply_markup=kb)

# -----------------------------
# Обработка кнопок админа через callback
# -----------------------------
@dp.callback_query()
async def admin_buttons(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ Нет доступа", show_alert=True)
        return

    if call.data == "admin_add":
        await call.message.answer("Введите код и название через запятую.\nПример:\n1234, Inception")
        await state.set_state(AdminStates.waiting_for_add)
        await call.answer()

    elif call.data == "admin_view":
        cursor.execute("SELECT code, title FROM movies")
        rows = cursor.fetchall()
        if not rows:
            await call.message.answer("Список пуст")
        else:
            msg_text = "\n".join([f"{c} → {t}" for c, t in rows])
            await call.message.answer(msg_text)
        await call.answer()

    elif call.data == "admin_delete":
        await call.message.answer("Введите код, который нужно удалить")
        await state.set_state(AdminStates.waiting_for_delete)
        await call.answer()

# -----------------------------
# Добавление кода с FSM
# -----------------------------
@dp.message(AdminStates.waiting_for_add)
async def add_code_fsm(msg: Message, state: FSMContext):
    try:
        code, title = msg.text.split(",", 1)
        code = code.strip()
        title = title.strip()
        cursor.execute("INSERT OR REPLACE INTO movies (code, title) VALUES (?, ?)", (code, title))
        conn.commit()
        await msg.answer(f"✅ Код {code} добавлен → {title}")
    except:
        await msg.answer("❌ Неверный формат. Пример:\n1234, Inception")
    await state.clear()

# -----------------------------
# Удаление кода с FSM
# -----------------------------
@dp.message(AdminStates.waiting_for_delete)
async def delete_code_fsm(msg: Message, state: FSMContext):
    code = msg.text.strip()
    cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
    conn.commit()
    await msg.answer(f"✅ Код {code} удалён")
    await state.clear()

# -----------------------------
# Пользовательский поиск по коду
# -----------------------------
@dp.message()
async def find_movie(msg: Message):
    user_id = msg.from_user.id
    if not await check_subscription(user_id):
        await msg.answer(f"❌ Подпишись на канал {CHANNEL_USERNAME}, чтобы пользоваться ботом.")
        return

    code = msg.text.strip()
    cursor.execute("SELECT title FROM movies WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row:
        await msg.answer(f"🎬 Код {code} → {row[0]}")
    else:
        await msg.answer("❌ Фильм/сериал с таким кодом не найден")

# -----------------------------
# Запуск бота
# -----------------------------
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
