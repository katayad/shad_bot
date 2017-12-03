import re
import datetime
import os
import requests
import config
import json
import xml.etree.ElementTree as etree
import difflib

cities_list = json.load(open("data/city.list.min.json", "r"))
cities = []
for city in cities_list:
    cities.append(city["name"].lower())
print(difflib.get_close_matches("verhnyaya salda", cities))

def text2int(textnum, numwords={}):
    try:
        return int(textnum)
    except:
        pass
    if not numwords:
        units = [
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen",
        ]

        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        scales = ["hundred", "thousand", "million", "billion", "trillion"]

        numwords["and"] = (1, 0)
        for idx, word in enumerate(units):    numwords[word] = (1, idx)
        for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
        for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
            raise Exception("Illegal word: " + word)

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

day_num = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6
}
days = 'monday|tuesday|wednesday|thursday|friday|saturday|sunday'
from_to = re.compile(r'from (%s) to (%s)' % (days, days))

this_week = re.compile(r'(this|on the|in the|during the|for a|for the|for one) week')
next_week = re.compile(r'(for)?(the next|next) week')
for_n_weeks = re.compile(r'(for|in)?\s*(\w+)\s*week?( in advance)?')

for_n_days = re.compile(r'(for|in the next) (\w+) days')
on_day = re.compile(r'(on )?(a )?(%s)(\'s)?' % days)


current = re.compile(r'(now|right now|like|current)')
today = re.compile(r'(for )?today')
tommorrow = re.compile(r'(for )?(tomorrow|the next day)')
aftertommorrow = re.compile(r'(for )?(the )?day after tomorrow')
def get_period(text):
    res = aftertommorrow.search(text)
    if (res):
        return text[:res.start()] + text[res.end():], (2, 3)
    res = tommorrow.search(text)
    if (res):
        return text[:res.start()] + text[res.end():], (1, 2)
    res = today.search(text)
    if (res):
        return text[:res.start()] + text[res.end():], (0, 1)
    res = current.search(text)
    if (res):
        return text[:res.start()] + text[res.end():], (0, 1)

    res = on_day.search(text)
    if (res):
        delta = (day_num[res.group(3)] - datetime.datetime.today().weekday() + 7) % 7
        return text[:res.start()] + text[res.end():], (delta, delta + 1)

    res = for_n_days.search(text)
    if (res):
        return text[:res.start()] + text[res.end():], (1, text2int(res.group(2)) + 1)

    res = this_week.search(text)
    if (res):
        return text[:res.start()] + text[res.end():], (1, 8)

    res = next_week.search(text)
    if (res):
            return text[:res.start()] + text[res.end():], (7 - datetime.datetime.today().weekday(), 7 - datetime.datetime.today().weekday() + 7)

    res = for_n_weeks.search(text)
    if (res):
        print(res.group(3))
        if res.group(3) == "":
            return text[:res.start()] + text[res.end():], (16, 13)
        return text[:res.start()] + text[res.end():], (1, text2int(res.group(3)) * 7 + 1)


    return text, (0, 1)

def translate(to, txt):
    hash_key = 'trnsl.1.1.20171116T145421Z.f3e43b7ad850d650.c614c9dc7e87b4fd7e547042cd517da9f20575a4'
    r = requests.get(
        "https://translate.yandex.net/api/v1.5/tr.json/translate?lang=%s&key=%s&text=%s" % (to, hash_key, txt)
    )
    #return r.text
    return json.loads(r.text)["text"][0]

def get_current_weather(city):
    print(city)
    resp = json.loads(
        requests.get(
            "http://api.openweathermap.org/data/2.5/weather?q=%s&units=metric&lang=ru&APPID=%s" %
            (city, config.openweather_token)
        ).text
    )
    return [resp,]

def get_weather(city, period):
    if period == (0, 1):
        return get_current_weather(city)
    resp = json.loads(
        requests.get(
            "http://api.openweathermap.org/data/2.5/forecast?q=%s&units=metric&APPID=%s" %
            (city, config.openweather_token)
        ).text
    )
    #print(list(range(40)))
    return resp["list"][(period[0] - 1) * 8+ 4:(period[1] - 1) * 8 + 4:8]

def recognise_audio(audio_path):
    headers = {'Content-type': 'audio/ogg;codecs=opus', 'Content-Length': str(os.path.getsize(audio_path))}
    files = {'audio': ("audio", open(audio_path, 'rb'))}
    r = requests.post(
        "https://asr.yandex.net/asr_xml?uuid=%s&key=%s&topic=queries" % (config.uuid, config.speach_tocken),
        files=files,
        headers=headers
    )
    tree = etree.fromstring(r.text)
    return [var.text for var in tree.findall('variant')]

def clean(text):
    print(text)
    clean_words = [
        " what ", " will ", " be ", " weather ", " temperature ", " temp ", " heat ", " prognosis ", " forecast ",
        " in ", " a ", " is ", " the ", " what's ", " like ", " how's ", ",",
    ]
    text = " " + text + " "
    for word in clean_words:
        text = text.replace(word, " ")
    return text.strip()

def get_city(text):
    return difflib.get_close_matches(text, cities)[0]

if __name__ == "__main__":
    print(get_period("what is the weather in San Francisco in next 2 weeks"))
