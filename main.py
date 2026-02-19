import telebot
import requests
from flask import Flask, request
import os
import logging
from xml.etree import ElementTree as ET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = '8193906266:AAFR3cqoUsU06xFBWyLoADAUSYJTQH3Sng4'
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def get_currency_rates():
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
        
        return msg
    except Exception as e:
        return f"❌ Ошибка: {e}"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Получен update: {update}")
    
    if update and 'message' in update:
        message = update['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        logger.info(f"Сообщение от {chat_id}: {text}")
        
        # Ручная проверка команд
        if text in ['/start', '/rate']:
            logger.info("Команда обнаружена, отправляю курсы")
            msg = get_currency_rates()
            bot.send_message(chat_id, msg, parse_mode='HTML')
            logger.info("Сообщение отправлено")
    
    return '', 200

@app.route('/')
def index():
    return '🤖 Бот работает!'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Запуск на порту {port}")
    app.run(host='0.0.0.0', port=port)
