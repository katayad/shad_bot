import re
import datetime
import os
import requests
import config
import json
import xml.etree.ElementTree as etree
import difflib
import urllib.request
import http.client, urllib.parse
import random
from pprint import pprint
from geotext import GeoText

cities_list = json.load(open("data/city.list.min.json", "r"))
cities = []
for city in cities_list:
    cities.append(city["name"].lower())


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

for_n_days = re.compile(r'(for |in the next |next )?(\w+) day(s|time)?')
for_n_days2 = re.compile(r'(\w+)-day')
on_day = re.compile(r'(on )?(a )?(%s)(\'s)?' % days)


current = re.compile(r'(now|right now|like|current)')
today = re.compile(r'(for )?today')
tommorrow = re.compile(r'(for )?(tomorrow|the next day)')
aftertommorrow = re.compile(r'(for )?(the )?day after tomorrow')
def get_period(text):
    text = text.lower()
    res = aftertommorrow.search(text)
    if (res):
        print("aftertommorrow")
        return (res.start(), res.end()), (2, 3)
    res = tommorrow.search(text)
    if (res):
        print("tommorrow")
        return (res.start(), res.end()), (1, 2)
    res = today.search(text)
    if (res):
        print("today")
        return (res.start(), res.end()), (0, 1)
    res = current.search(text)
    if (res):
        print("current")
        return (res.start(), res.end()), (0, 1)

    res = on_day.search(text)
    if (res):
        print("")
        delta = (day_num[res.group(3)] - datetime.datetime.today().weekday() + 7) % 7
        return (res.start(), res.end()), (delta, delta + 1)

    res = for_n_days.search(text)
    if (res):
        print("for_n_days")
        return (res.start(), res.end()), (1, text2int(res.group(2)) + 1)

    res = for_n_days2.search(text)
    if (res):
        print("for_n_days2")
        return (res.start(), res.end()), (1, text2int(res.group(1)) + 1)

    res = this_week.search(text)
    if (res):
        print("this_week")
        return (res.start(), res.end()), (1, 8)

    res = next_week.search(text)
    if (res):
        print("next_week")
        return (res.start(), res.end()), (7 - datetime.datetime.today().weekday(), 7 - datetime.datetime.today().weekday() + 7)

    res = for_n_weeks.search(text)
    if (res):
        print("for_n_weeks")
        if res.group(3) == "":
            return (res.start(), res.end()), (16, 13)
        return (res.start(), res.end()), (1, text2int(res.group(3)) * 7 + 1)


    return (-1, -1), (0, 1)

def translate(to, txt):
    hash_key = 'trnsl.1.1.20171116T145421Z.f3e43b7ad850d650.c614c9dc7e87b4fd7e547042cd517da9f20575a4'
    r = requests.get(
        "https://translate.yandex.net/api/v1.5/tr.json/translate?lang=%s&key=%s&text=%s" % (to, hash_key, txt)
    )
    #return r.text
    return json.loads(r.text)["text"][0].replace("St.", "Saint")

def get_current_weather(city):
    print(city)
    resp = json.loads(
        requests.get(
            "http://api.openweathermap.org/data/2.5/weather?q=%s&units=metric&APPID=%s&lang=ru" %
            (city, config.openweather_token)
        ).text
    )
    return [resp,]

def get_weather(city, period):
    if period == (0, 1):
        return get_current_weather(city)
    resp = json.loads(
        requests.get(
            "http://api.openweathermap.org/data/2.5/forecast?q=%s&units=metric&APPID=%s&lang=ru" %
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
    print(r.text)
    tree = etree.fromstring(r.text)
    return [var.text for var in tree.findall('variant')]

def clean(text):
    print(text)
    clean_words = [
        "forecast-weather", " what ", " will ", " be ", " weather ", " temperature ",
        "temperatures", " temp ", " heat ", " prognosis ", " forecast ", " in ",
        " a ", " is ", " the ", " what's ", " like ", " how's ", ",", "!", "?", ".", ";"
    ]
    text = " " + text + " "
    for word in clean_words:
        text = text.replace(word, " ")
    return text.strip()

def get_city(text):
    print("getting city form: ", text)
    geo = GeoText(text)
    if (len(geo.cities)):
        print("GOT GEO!")
        return geo.cities[0].lower()
    text = clean(text.lower())
    print("getting city form: ", text)
    return difflib.get_close_matches(text, cities)[0]

def BingWebSearch(search):
    print(search)
    host = "api.cognitive.microsoft.com"
    path = "/bing/v7.0/images/search"
    "Performs a Bing Web search and returns the results."

    headers = {'Ocp-Apim-Subscription-Key': config.bing_token}
    conn = http.client.HTTPSConnection(host)
    query = urllib.parse.quote(search)
    conn.request("GET", path + "?q=" + query, headers=headers)
    response = conn.getresponse()
    headers = [k + ": " + v for (k, v) in response.getheaders()
                   if k.startswith("BingAPIs-") or k.startswith("X-MSEdge-")]
    return response.read().decode("utf8")

def GetImage(city, desc):
    print(city + " " + desc)
    res = json.loads(requests.get(
        "https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&q=%s&searchType=image" %
        (config.google_tocken, config.google_cx, "город " + city + " " + desc)
    ).text)["items"]
    #print(res)
    return res[random.randint(0, len(res))]["link"]

def get_query_by_desc_id(ID):
    ID = int(ID)
    if 200 <= ID <= 232:
        return "гроза|шторм|буря"
    if 300 <= ID <= 311 or ID == 500:
        return "моросить|дождик"
    if 502 <= ID <= 531:
        return "дождь||дождик"
    if 600 <= ID <= 602:
        return "снег|снежек|снежёк"
    if 611 <= ID <= 616:
        return "мокрый снег"
    if 620 <= ID <= 622:
        return "снегопад"
    if ID in [741, 701]:
        return "туман"
    if ID == 711:
        return "дымка"
    if ID in [731, 751, 761]:
        return "пыль"
    if ID == 762:
        return "пепел"
    if ID == 771:
        return "шторм|буря"
    if ID == 781:
        return "смерч"
    if ID == 800:
        return "солнце"
    if 801 <= ID <= 804:
        return "облака|облачно"
    if 900 <= ID <= 902:
        return "гроза|шторм|буря|ураган"
    if ID == 903:
        return "холод|холодно|холодок"
    if ID == 904:
        return "жара|жарко"
    if ID == 905:
        return "ветер|ветерок|ветренно"
    if ID == 906:
        return "град"
    return "погода"

def GetPoem(query):
    print(query)
    res = json.loads(requests.get(
        "https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&q=%s" %
        (config.google_tocken, config.google_poem_cx, query)
    ).text)["items"]
    #print(res)snippet
    return res[random.randint(0, len(res))]["snippet"]

if __name__ == "__main__":
    #print(get_period("what is the weather in San Francisco in next 2 weeks"))
    #pprint(GetPoem("дождик"))
    #print(difflib.get_close_matches("st. petersburg", cities))
    print(get_period("3 day forecast in Moscow"))
