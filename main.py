import telebot
import requests
from flask import Flask, request
import os
import logging
import sqlite3
from datetime import datetime
from xml.etree import ElementTree as ET

# ===== НАСТРОЙКИ =====
BOT_TOKEN = '8193906266:AAFR3cqoUsU06xFBWyLoADAUSYJTQH3Sng4'
T_INVEST_LINK = 'https://tbank.ru/baf/94078nKg1qd'  # Твоя партнёрская ссылка

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (date TEXT, currency TEXT, rate REAL)''')
    conn.commit()
    conn.close()

def save_to_db(currency, rate):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute("INSERT INTO history VALUES (?, ?, ?)", 
              (datetime.now().strftime('%Y-%m-%d %H:%M'), currency, rate))
    conn.commit()
    conn.close()

def get_history(currency, limit=5):
    conn = sqlite3.connect('currency.db')
    c = conn.cursor()
    c.execute("SELECT date, rate FROM history WHERE currency=? ORDER BY date DESC LIMIT ?", 
              (currency, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# ===== ВАЛЮТЫ =====
CURRENCIES = {
    'R01235': {'code': 'USD', 'name': '🇺🇸 Доллар США', 'nominal': 1},
    'R01239': {'code': 'EUR', 'name': '🇪🇺 Евро', 'nominal': 1},
    'R01375': {'code': 'CNY', 'name': '🇨🇳 Юань', 'nominal': 1},
    'R01010': {'code': 'GBP', 'name': '🇬🇧 Фунт стерлингов', 'nominal': 1},
    'R01190': {'code': 'JPY', 'name': '🇯🇵 Иена', 'nominal': 100},
    'R01500': {'code': 'TRY', 'name': '🇹🇷 Турецкая лира', 'nominal': 1},
    'R01535': {'code': 'KZT', 'name': '🇰🇿 Тенге', 'nominal': 100},
    'R01215': {'code': 'UAH', 'name': '🇺🇦 Гривна', 'nominal': 1},
    'R01135': {'code': 'BYN', 'name': '🇧🇾 Бел. рубль', 'nominal': 1},
    'R01700': {'code': 'CHF', 'name': '🇨🇭 Франк', 'nominal': 1},
}

# ===== КЛАВИАТУРЫ =====
def main_keyboard():
    from telebot import types
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('💱 Все курсы')
    btn2 = types.KeyboardButton('🔄 Конвертер')
    btn3 = types.KeyboardButton('📈 История')
    btn4 = types.KeyboardButton('📊 Т-Инвестиции')
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    return markup

def currency_keyboard():
    from telebot import types
    markup = types.InlineKeyboardMarkup()
    buttons = []
    for vid, data in CURRENCIES.items():
        buttons.append(types.InlineKeyboardButton(data['code'], callback_data=f'rate_{vid}'))
    # По 3 кнопки в ряд
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    return markup

# ===== ФУНКЦИИ =====
def get_currency_rates():
    try:
        xml = requests.get('https://www.cbr.ru/scripts/XML_daily.asp', timeout=10).content
        root = ET.fromstring(xml)
        rates = {}
        
        for vid, data in CURRENCIES.items():
            valute = root.find(f".//Valute[@ID='{vid}']")
            if valute:
                nominal = float(valute.find('Nominal').text.replace(',', '.'))
                value = float(valute.find('Value').text.replace(',', '.'))
                rate = value / nominal
                rates[data['code']] = rate
                save_to_db(data['code'], rate)
        
        # Криптовалюты (с другого API)
        try:
            crypto = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json', timeout=5).json()
            rates['BTC'] = crypto['bpi']['USD']['rate_float']
            rates['ETH'] = 0  # Можно добавить другой API для ETH
        except:
            pass
        
        return rates
    except Exception as e:
        logger.error(f"Ошибка получения курсов: {e}")
        return None

def format_rates_message(rates):
    msg = "💱 <b>Курсы валют ЦБ РФ</b>\n"
    msg += f"<i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>\n\n"
    
    order = ['USD', 'EUR', 'CNY', 'GBP', 'JPY', 'TRY', 'KZT', 'UAH', 'BYN', 'CHF', 'BTC', 'ETH']
    for code in order:
        if code in rates and rates[code] > 0:
            if code in ['BTC', 'ETH']:
                msg += f"🪙 <b>{code}</b>: ${rates[code]:,.2f}\n"
            else:
                msg += f"{CURRENCIES.get(code, {}).get('name', code)}: <b>{rates[code]:.2f} ₽</b>\n"
    
    msg += f"\n📈 <a href='{T_INVEST_LINK}'>Т-Инвестиции — начни инвестировать!</a>"
    return msg

def convert_currency(amount, from_curr, to_curr, rates):
    if from_curr == 'RUB':
        rub_amount = amount
    elif from_curr in rates:
        rub_amount = amount * rates[from_curr]
    else:
        return None
    
    if to_curr == 'RUB':
        return rub_amount
    elif to_curr in rates:
        return rub_amount / rates[to_curr]
    else:
        return None

# ===== ОБРАБОТЧИКИ =====
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if update and 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        logger.info(f"Сообщение от {chat_id}: {text}")
        
        # Команды и кнопки
        if text in ['/start', '💱 Все курсы']:
            rates = get_currency_rates()
            if rates:
                msg = format_rates_message(rates)
                bot.send_message(chat_id, msg, parse_mode='HTML', reply_markup=main_keyboard())
        
        elif text in ['/convert', '🔄 Конвертер']:
            bot.send_message(chat_id, 
                "🔄 <b>Конвертер валют</b>\n\n"
                "Пример: <code>/convert 100 USD RUB</code>\n"
                "Или: <code>/convert 50 EUR USD</code>\n\n"
                "Доступные: USD, EUR, CNY, GBP, JPY, TRY, KZT, RUB",
                parse_mode='HTML', reply_markup=main_keyboard())
        
        elif text.startswith('/convert'):
            try:
                parts = text.split()
                if len(parts) == 4:
                    amount = float(parts[1])
                    from_curr = parts[2].upper()
                    to_curr = parts[3].upper()
                    rates = get_currency_rates()
                    rates['RUB'] = 1
                    
                    result = convert_currency(amount, from_curr, to_curr, rates)
                    if result:
                        bot.send_message(chat_id,
                            f"💱 <b>{amount:,.2f} {from_curr}</b> = <b>{result:,.2f} {to_curr}</b>\n\n"
                            f"<i>Курс на {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>",
                            parse_mode='HTML', reply_markup=main_keyboard())
                    else:
                        bot.send_message(chat_id, "❌ Неверная валюта", reply_markup=main_keyboard())
                else:
                    bot.send_message(chat_id, "❌ Пример: /convert 100 USD RUB", reply_markup=main_keyboard())
            except Exception as e:
                bot.send_message(chat_id, f"❌ Ошибка: {e}", reply_markup=main_keyboard())
        
        elif text in ['/history', '📈 История']:
            msg = "📈 <b>История курсов (последние 5 записей)</b>\n\n"
            for code in ['USD', 'EUR', 'CNY']:
                history = get_history(code, 5)
                if history:
                    msg += f"<b>{code}</b>:\n"
                    for date, rate in reversed(history):
                        msg += f"  {date}: {rate:.2f} ₽\n"
                    msg += "\n"
            bot.send_message(chat_id, msg, parse_mode='HTML', reply_markup=main_keyboard())
        
        elif text in ['/invest', '📊 Т-Инвестиции']:
            bot.send_message(chat_id,
                f"📈 <b>Т-Инвестиции</b>\n\n"
                "Открой брокерский счёт и начни инвестировать!\n\n"
                f"🔗 <a href='{T_INVEST_LINK}'>Перейти в Т-Инвестиции</a>\n\n"
                "<i>Это партнёрская ссылка — вы поддерживаете развитие бота</i>",
                parse_mode='HTML', reply_markup=main_keyboard())
        
        elif text == '/help':
            bot.send_message(chat_id,
                "🤖 <b>Команды бота:</b>\n\n"
                "/start — Главное меню\n"
                "/rate — Курсы валют\n"
                "/convert — Конвертер\n"
                "/history — История курсов\n"
                "/invest — Т-Инвестиции\n"
                "/help — Эта справка",
                parse_mode='HTML', reply_markup=main_keyboard())
    
    # Обработка callback (inline кнопки)
    if update and 'callback_query' in update:
        callback = update['callback_query']
        chat_id = callback['message']['chat']['id']
        data = callback.get('data', '')
        
        if data.startswith('rate_'):
            vid = data.split('_')[1]
            rates = get_currency_rates()
            if vid in [v['code'] for v in CURRENCIES.values()]:
                for vcode, vdata in CURRENCIES.items():
                    if vdata['code'] == vid.split('_')[0] if '_' in vid else vid:
                        pass
    
    return '', 200

@app.route('/')
def index():
    return '🤖 Бот работает!'

# ===== ЗАПУСК =====
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Запуск на порту {port}")
    app.run(host='0.0.0.0', port=port)
