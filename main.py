import telebot
import requests
from flask import Flask, request
import os
import logging
from xml.etree import ElementTree as ET

# Включаем логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== ВСТАВЬ СЮДА СВОЙ ТОКЕН =====
BOT_TOKEN = '8193906266:AAFR3cqoUsU06xFBWyLoADAUSYJTQH3Sng4'
# ==================================

bot = telebot.TeleBot(BOT_TOKEN, skip_pending=True)
app = Flask(__name__)

# ===== ОБРАБОТЧИКИ КОМАНД =====
@bot.message_handler(commands=['start', 'rate'])
def send_rate(message):
    logger.info(f"Получена команда от пользователя {message.chat.id}")
    try:
        xml = requests.get('https://www.cbr.ru/scripts/XML_daily.asp', timeout=10).content
        root = ET.fromstring(xml)
        msg = "💱 <b>Курсы ЦБ РФ:</b>\n\n"
        
        usd = root.find(".//Valute[@ID='R01235']")
        usd_rate = float(usd.find('Value').text.replace(',','.')) / float(usd.find('Nominal').text.replace(',','.'))
        msg += f"🇺🇸 USD: {usd_rate:.2f} ₽\n"
        
        eur = root.find(".//Valute[@ID='R01239']")
        eur_rate = float(eur.find('Value').text.replace(',','.')) / float(eur.find('Nominal').text.replace(',','.'))
        msg += f"🇪🇺 EUR: {eur_rate:.2f} ₽\n"
        
        cny = root.find(".//Valute[@ID='R01375']")
        cny_rate = float(cny.find('Value').text.replace(',','.')) / float(cny.find('Nominal').text.replace(',','.'))
        msg += f"🇨🇳 CNY: {cny_rate:.2f} ₽\n"
        
        logger.info(f"Отправляю ответ пользователю {message.chat.id}")
        bot.reply_to(message, msg, parse_mode='HTML')
        logger.info("Ответ отправлен успешно")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ===== ВЕБХУК ДЛЯ FLASK =====
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Получен POST запрос от Telegram")
    update = request.get_json()
    logger.info(f"Получены данные: {update}")
    
    if update:
        bot.process_new_updates([telebot.types.Update.de_json(update)])
        logger.info("Обработка обновлений завершена")
    
    return '', 200

@app.route('/')
def index():
    return '🤖 Бот работает!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port)
