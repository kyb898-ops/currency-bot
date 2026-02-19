import telebot
import requests
from flask import Flask, request
import os
from xml.etree import ElementTree as ET

# ===== ВСТАВЬ СЮДА СВОЙ ТОКЕН =====
BOT_TOKEN = 'ВСТАВЬ_СЮДА_ТОКЕН_ОТ_BOTFATHER'
# ==================================

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start', 'rate'])
def send_rate(message):
    try:
        xml = requests.get('https://www.cbr.ru/scripts/XML_daily.asp', timeout=10).content
        root = ET.fromstring(xml)
        msg = "💱 <b>Курсы ЦБ РФ:</b>\n\n"
        
        # USD
        usd = root.find(".//Valute[@ID='R01235']")
        usd_rate = float(usd.find('Value').text.replace(',','.')) / float(usd.find('Nominal').text.replace(',','.'))
        msg += f"🇺🇸 USD: {usd_rate:.2f} ₽\n"
        
        # EUR
        eur = root.find(".//Valute[@ID='R01239']")
        eur_rate = float(eur.find('Value').text.replace(',','.')) / float(eur.find('Nominal').text.replace(',','.'))
        msg += f"🇪🇺 EUR: {eur_rate:.2f} ₽\n"
        
        # CNY
        cny = root.find(".//Valute[@ID='R01375']")
        cny_rate = float(cny.find('Value').text.replace(',','.')) / float(cny.find('Nominal').text.replace(',','.'))
        msg += f"🇨🇳 CNY: {cny_rate:.2f} ₽\n"
        
        bot.reply_to(message, msg, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return '', 200

@app.route('/')
def index():
    return '🤖 Бот работает!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
