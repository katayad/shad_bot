# coding=utf-8
import config
import json
import pprint
import telepot
import time
import datetime
from telepot.loop import MessageLoop
from utils import *

from pprint import pprint

bot = telepot.Bot(config.token)
bot.getMe()

def get_audio(msg):
    #"%s/%s" % (msg["chat"]["id"], file_id)
    try:
        os.stat("data/audio")
    except:
        os.mkdir("data/audio")

    dr = "data/audio/chat_" + str(msg["chat"]["id"])
    try:
        os.stat(dr)
    except:
        os.mkdir(dr)

    path = "%s/%s.%s" % (dr, msg["voice"]["file_id"], msg["voice"]["mime_type"].split("/")[1])
    audio = bot.download_file(msg["voice"]["file_id"], path)
    return path

def handle(msg):
    if ("voice" in msg) :
        pprint(msg)
        variants = recognise_audio(get_audio(msg))

        if (len(variants)):
            text = variants[0]
        else:
            bot.sendMessage(msg["chat"]["id"], "Не понял")
            return
    else:
        text = msg["text"]
    print(text)
    text = translate("en", text)
    print(text)
    text, period = get_period(text)
    if (period[0] >= 6 or period[1] >= 7):
        bot.sendMessage(msg["chat"]["id"],"хз")
        time.sleep(1)
        bot.sendMessage(msg["chat"]["id"],"Могу заглянуть лишь на 5 дней вперед..")
        return

    print(text, period)
    city = get_city(text)
    print(city)

    city_ru = translate("ru", city)
    bot.sendMessage(msg["chat"]["id"], city_ru)

    days = get_weather(city, period)

    week_day = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    print(days)
    for day in days:
        print(day["dt"])
        date = datetime.datetime.utcfromtimestamp(int(day["dt"]))
        #print(date.strftime('%Y-%m-%dT%H:%M:%SZ'))
        #print(date.weekday())
        bot.sendMessage(
            msg["chat"]["id"],
            "%s(%s)\n    %s°C, %s" % (
                week_day[date.weekday()],
                date.strftime('%m-%d'),
                day["main"]["temp"],
                day["weather"][0]["description"]
            )
        )

    bot.sendPhoto(msg["chat"]["id"], GetImage(city_ru, get_query_by_desc_id(days[0]["weather"][0]["id"]) ))
    bot.sendMessage(msg["chat"]["id"], GetPoem(get_query_by_desc_id(days[0]["weather"][0]["id"])))

print ('Listening ...')
while 1:
    try:
        MessageLoop(bot, handle).run_forever()
    except:
        pass
    time.sleep(10)
