import os
import pandas as pd
import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# ID Google Таблиц для разных языков
SPREADSHEET_ID_RU = "1g1XqVEb0B6vI7f0Oh1QDjGQ-hEwtGjoMPSzwvOWwrZ4"  # Замените на реальный ID
SPREADSHEET_ID_KG = "1xqsSnmsgoMN69fzk5BIDfd9OsphfLQHz42_V60RfNao"  # Замените на реальный ID

# Глобальная переменная для хранения выбранного языка
USER_LANGUAGE = {}

# Функция загрузки данных из таблицы
def get_tasks(task_type, language):
    # Выбираем ID таблицы в зависимости от языка
    spreadsheet_id = SPREADSHEET_ID_RU if language == "ru" else SPREADSHEET_ID_KG
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv"
    
    try:
        df = pd.read_csv(url)  # Загружаем таблицу
    except Exception as e:
        print(f"Ошибка загрузки таблицы: {e}")
        return {}

    today = datetime.date.today()
    tasks = {}

    for _, row in df.iterrows():
        if str(row.get("Тип", "")).strip() == task_type:
            unlock_date_str = str(row.get("Дата разблокировки", "")).strip()

            try:
                unlock_date = datetime.datetime.strptime(unlock_date_str, "%Y-%m-%d").date()
                days_left = (unlock_date - today).days
            except ValueError:
                continue  # Пропустить, если дата неправильная

            tasks[row["Название"]] = {
                "description": row.get("Описание", "Нет описания"),
                "link": row.get("Ссылка", "#"),
                "unlock_date": unlock_date,
                "days_left": days_left
            }

    return tasks

# Выбор языка
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇰🇬 Кыргызский")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите язык / Тил тандаңыз:", reply_markup=reply_markup)

# Обработка выбора языка
async def choose_language(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "🇷🇺 Русский":
        USER_LANGUAGE[user_id] = "ru"
        await update.message.reply_text("Язык выбран: Русский")
        await show_main_menu(update, context)
    elif text == "🇰🇬 Кыргызский":
        USER_LANGUAGE[user_id] = "kg"
        await update.message.reply_text("Тил тандалды: Кыргызча")
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выберите язык / Тил тандаңыз.")

# Главное меню
async def show_main_menu(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    language = USER_LANGUAGE.get(user_id, "ru")  # По умолчанию русский

    if language == "ru":
        keyboard = [
            [KeyboardButton("📚 Лекционные темы"), KeyboardButton("🛠 Лабораторные работы")],
        ]
        text = "Выберите раздел:"
    else:
        keyboard = [
            [KeyboardButton("📚 Лекциялар"), KeyboardButton("🛠 Лаборатория")],
        ]
        text = "Бөлүмдү тандаңыз:"

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=reply_markup)

# Показывает список тем
async def show_topics(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    language = USER_LANGUAGE.get(user_id, "ru")  # По умолчанию русский

    if language == "ru":
        task_type = "Лекция" if update.message.text == "📚 Лекционные темы" else "Лабораторная"
    else:
        task_type = "Лекция" if update.message.text == "📚 Лекциялар" else "Лаборатория"

    tasks = get_tasks(task_type, language)

    if not tasks:
        await update.message.reply_text("Нет доступных тем." if language == "ru" else "Жеткиликтүү темалар жок.")
        return

    keyboard = []
    for name, details in tasks.items():
        if details["days_left"] > 0:
            text = f"{name} (⏳ {details['days_left']} дн.)" if language == "ru" else f"{name} (⏳ {details['days_left']} күн)"
        else:
            text = name
        keyboard.append([KeyboardButton(text)])

    keyboard.append([KeyboardButton("⬅ Назад" if language == "ru" else "⬅ Артка")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"📜 {task_type}:" if language == "ru" else f"📜 {task_type}:", reply_markup=reply_markup)

# Показывает выбранную тему
async def show_task(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    language = USER_LANGUAGE.get(user_id, "ru")  # По умолчанию русский

    if update.message.text == ("⬅ Назад" if language == "ru" else "⬅ Артка"):
        await show_main_menu(update, context)
        return

    task_name = update.message.text.split(" (⏳")[0]  # Убираем таймер из кнопки
    tasks = {**get_tasks("Лекция", language), **get_tasks("Лабораторная", language)}  # Объединяем лекции и лабораторные
    task = tasks.get(task_name)

    if not task:
        await update.message.reply_text("Тема не найдена." if language == "ru" else "Тема табылган жок.")
        return

    if task["days_left"] > 0:
        await update.message.reply_text(
            f"⛔ Тема \"{task_name}\" пока недоступна.\n"
            f"📅 Она откроется {task['unlock_date']} (через {task['days_left']} дней)."
            if language == "ru" else
            f"⛔ Тема \"{task_name}\" азырынча жеткиликтүү эмес.\n"
            f"📅 Ал {task['unlock_date']} күнү ачылат ({task['days_left']} күн калды)."
        )
    else:
        text = f"📌 *{task_name}*\n{task['description']}\n[Вот вам ссылка]({task['link']})"
        await update.message.reply_text(text, parse_mode="Markdown")

# Настройка бота
app = Application.builder().token(os.getenv("TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("🇷🇺 Русский|🇰🇬 Кыргызский"), choose_language))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📚 Лекционные темы|🛠 Лабораторные работы|📚 Лекциялар|🛠 Лаборатория"), show_topics))
app.add_handler(MessageHandler(filters.TEXT, show_task))

if __name__ == "__main__":
    print("Бот запущен...")
    app.run_polling()
