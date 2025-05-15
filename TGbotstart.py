import telebot
from telebot.types import Message
import psycopg2
from datetime import datetime

# Конфигурация
TOKEN = '7693581495:AAHLXUsap-Fqlq3V2-EN9QH9yh7ht05eqpg'
CHANNEL_ID = '-1002488607863'

# Подключение к базе данных
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="1234",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()
bot = telebot.TeleBot(TOKEN)

# Словарь для временного хранения данных о студенте
user_data = {}

def validate_date(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    bot.reply_to(message, "Привет! Я бот для управления студентами. Доступные команды:\n"
                          "/add_student - добавить нового студента\n"
                          "/get_ratings - показать рейтинг по среднему баллу")

@bot.message_handler(commands=['add_student'])
def start_add_student(message: Message):
    chat_id = message.chat.id
    user_data[chat_id] = {}  # Инициализация данных для нового студента
    bot.send_message(chat_id, "Введите имя студента:")
    bot.register_next_step_handler(message, process_first_name)

def process_first_name(message: Message):
    chat_id = message.chat.id
    user_data[chat_id]['s_name'] = message.text
    bot.send_message(chat_id, "Введите фамилию студента:")
    bot.register_next_step_handler(message, process_last_name)

def process_last_name(message: Message):
    chat_id = message.chat.id
    user_data[chat_id]['f_name'] = message.text
    bot.send_message(chat_id, "Введите отчество студента:")
    bot.register_next_step_handler(message, process_middle_name)

def process_middle_name(message: Message):
    chat_id = message.chat.id
    user_data[chat_id]['l_name'] = message.text
    bot.send_message(chat_id, "Введите дату рождения студента (в формате YYYY-MM-DD):")
    bot.register_next_step_handler(message, process_birth_date)

def process_birth_date(message: Message):
    chat_id = message.chat.id
    if validate_date(message.text):
        user_data[chat_id]['birth_date'] = message.text
        bot.send_message(chat_id, "Введите год поступления студента:")
        bot.register_next_step_handler(message, process_admission_year)
    else:
        bot.send_message(chat_id, "Неверный формат даты. Попробуйте снова.")
        bot.register_next_step_handler(message, process_birth_date)

def process_admission_year(message: Message):
    chat_id = message.chat.id
    try:
        admission_year = int(message.text)
        if admission_year < 2000 or admission_year > datetime.now().year:
            raise ValueError
        user_data[chat_id]['admission_year'] = admission_year
        bot.send_message(chat_id, "Введите курс студента:")
        bot.register_next_step_handler(message, process_course)
    except ValueError:
        bot.send_message(chat_id, "Неверный формат года. Попробуйте снова.")
        bot.register_next_step_handler(message, process_admission_year)

def process_course(message: Message):
    chat_id = message.chat.id
    try:
        course = int(message.text)
        if course < 1 or course > 6:
            raise ValueError
        user_data[chat_id]['course'] = course
        bot.send_message(chat_id, "Введите группу студента:")
        bot.register_next_step_handler(message, process_group)
    except ValueError:
        bot.send_message(chat_id, "Неверный формат курса. Попробуйте снова.")
        bot.register_next_step_handler(message, process_course)

def process_group(message: Message):
    chat_id = message.chat.id
    user_data[chat_id]['group_name'] = message.text

    # Сохранение студента в базу данных
    try:
        cursor.execute(
            "INSERT INTO students (s_name, f_name, l_name, birth_date, admission_year, course, group_name) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                user_data[chat_id]['s_name'],
                user_data[chat_id]['f_name'],
                user_data[chat_id]['l_name'],
                user_data[chat_id]['birth_date'],
                user_data[chat_id]['admission_year'],
                user_data[chat_id]['course'],
                user_data[chat_id]['group_name']
            )
        )
        conn.commit()
        bot.send_message(chat_id, "Студент успешно добавлен!")
    except Exception as e:
        conn.rollback()
        bot.send_message(chat_id, f"Ошибка: {str(e)}")


@bot.message_handler(commands=['get_ratings'])
def get_ratings(message: Message):
    try:
        cursor.execute("""
                SELECT s.id, s.s_name, s.f_name, s.l_name, 
                       ROUND(AVG(g.grade), 2) as avg_grade,
                       s.birth_date, s.admission_year, s.course, s.group_name
                FROM students s
                JOIN grades g ON s.id = g.student_id
                GROUP BY s.id
                ORDER BY avg_grade DESC
            """)

        response = "Рейтинг студентов по среднему баллу:\n\n"
        for idx, row in enumerate(cursor.fetchall(), 1):
            response += (f"{idx}. {row[1]} {row[2]} {row[3]}\n"
                         f"Дата рождения: {row[5]}\n"
                         f"Год поступления: {row[6]}\n"
                         f"Курс: {row[7]}\n"
                         f"Группа: {row[8]}\n"
                         f"Средний балл: {row[4]}\n\n")

        bot.reply_to(message, response)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}") #asedfasdf


if __name__ == '__main__':
    bot.polling(none_stop=True)