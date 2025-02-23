import os
import pandas as pd
import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

# ID Google Таблицы
SPREADSHEET_ID = "1s1F-DONBzaYH8n1JmQmuWS5Z1HW4lH4cz1Vl5wXSqyw"



# Функция загрузки данных из таблицы
def get_tasks(task_type):
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"
    
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

# Главное меню
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton("📚 Лекционные темы"), KeyboardButton("🛠 Лабораторные работы")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите раздел:", reply_markup=reply_markup)

# Показывает список тем
async def show_topics(update: Update, context: CallbackContext) -> None:
    task_type = "Лекция" if update.message.text == "📚 Лекционные темы" else "Лабораторная"
    tasks = get_tasks(task_type)

    if not tasks:
        await update.message.reply_text("Нет доступных тем.")
        return

    keyboard = []
    for name, details in tasks.items():
        # Если тема недоступна, показываем количество дней до доступности
        if details["days_left"] > 0:
            text = f"{name} (⏳ {details['days_left']} дн.)"
        else:
            text = name
        keyboard.append([KeyboardButton(text)])

    keyboard.append([KeyboardButton("⬅ Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"📜 {task_type}:", reply_markup=reply_markup)

# Показывает выбранную тему
async def show_task(update: Update, context: CallbackContext) -> None:
    if update.message.text == "⬅ Назад":
        await start(update, context)
        return

    task_name = update.message.text.replace(" (⏳", "").split(" дн.)")[0]  # Убираем таймер из кнопки
    tasks = {**get_tasks("Лекция"), **get_tasks("Лабораторная")}  # Объединяем лекции и лабораторные
    task = tasks.get(task_name)

    if not task:
        await update.message.reply_text("Тема не найдена.")
        return

    # Если тема еще не доступна
    if task["days_left"] > 0:
        await update.message.reply_text(
            f"⛔ Тема \"{task_name}\" пока недоступна.\n"
            f"📅 Она откроется {task['unlock_date']} (через {task['days_left']} дней)."
        )
    else:
        text = f"📌 *{task_name}*\n{task['description']}\n[Вот вам ссылка]({task['link']})"
        await update.message.reply_text(text, parse_mode="Markdown")

# Настройка бота
app = Application.builder().token(os.getenv("TOKEN")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📚 Лекционные темы|🛠 Лабораторные работы"), show_topics))
app.add_handler(MessageHandler(filters.TEXT, show_task))

if __name__ == "__main__":
    print("Бот запущен...")
    app.run_polling()


