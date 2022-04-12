# ОБЯЗАТЕЛЬНО УСТАНОВИТЬ pip install brotli
"""

"""
import traceback
from datetime import datetime
from operator import itemgetter
import requests
import time

import globals


def update_exalt_price():
    """
    На основании 20 первых офферов считается средняя, предварительно отсекает прайсфиксером
    (при сильном отклонении от средней цены)
    :return:
    """
    items_bulk = _get_items_bulk(("exalted",), ("chaos",), 1, 20)

    prices = [item['amount'] for item in items_bulk]
    avg = sum(prices) / len(prices)

    # Вырезаем прайсфиксерные цены
    _prices = prices.copy()
    for _price in _prices:
        if abs((_price - avg) / avg) > 0.05:  # При отклонении больше чем на 5% от среднего - убираем из списка
            prices.remove(_price)  # Удаляет первый совпавший элемент
            avg = sum(prices) / len(prices)  # Пересчет среднеарифметического

    globals.exalt_price = round(sum(prices) / len(prices))
    globals.logger.info(f"Курс экзальта к хаосу: {globals.exalt_price}")


def update_offer_list():

    new_offer_list = []

    # for currency in ["exalted", "chaos"]:
    for item in globals.items:
        _datetime = datetime.now()

        offers = _get_items_bulk((item['name'],), ("chaos",), 1, 5)

        new_offer_list.extend(
            [
                (
                    offer['offer_id'],
                    offer['exchange_id'],
                    (item['bulk_price'] - offer['c_price']) * offer['quantity']
                ) for offer in offers if item['bulk_price'] > offer['c_price']
            ]
        )

        # Уменьшаем интервал на время выполнения прошлого запроса
        _interval = globals.requests_interval - (datetime.now() - _datetime).total_seconds()
        if _interval > 0:
            time.sleep(_interval)

    globals.offer_list = sorted(new_offer_list, key=itemgetter(2), reverse=True)
    globals.last_check_poetrade = datetime.now()
    globals.logger.info("Оффер-лист обновлен.")


def _get_items_bulk(items_i_want: tuple, items_i_have: tuple, minimum: int, qty_offers: int = 0):
    """
    c_price (chaos price) - цена, приведенная к хаосам по курсу, для удобства рассчетов, есть в возвращаемом словаре
    :param items_i_want:
    :param items_i_have:
    :param minimum: Балк не меньше, чем этот параметр
    :param qty_offers: Сколько всего результатов надо по этому запросу (блэклист не учитываются)
    :return:
    """

    # Дефолтные штуки, следить нужно только за POESESSID
    headers = {
        "Host": "www.pathofexile.com",
        "Connection": "keep - alive",
        "Content-Length": "102",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
        "Accept": "*/*",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36",
        "sec-ch-ua-platform": '"Windows"',
        "Origin": "https://www.pathofexile.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.pathofexile.com/trade/exchange/Archnemesis",
        "Accept-Encoding": "gzip,deflate,br",
        "Accept-Language": "q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": f"POESESSID={globals.POESESSID}; ga=GA1.2.1526205301.1648748654; gid=GA1.2.1802044350.1648748654"
    }

    # Ссылка для запроса к странице с балком
    url = r"https://www.pathofexile.com/api/trade/exchange/Archnemesis"

    # Запрос поиска
    data = {
        "exchange": {
            "status": {
                "option": "online"
            },
            "want": items_i_want,
            "have": items_i_have,
            "minimum": minimum
        }
    }

    # 1) Получаем результат поиска по запросу
    # Если не работает, значит не установлен pip install brotli
    response_request = requests.post(url, headers=headers, json=data)
    response = response_request.json()

    # В пое в АПИ постоянно меняется правило "сколько можно делать запросов в какое кол-во времени"
    # requests_interval = float(response_request.headers['X-Rate-Limit-Account'].split(":")[1])/float(
    #     response_request.headers['X-Rate-Limit-Account'].split(":")[0])
    # response_request.headers['X-Rate-Limit-Ip'] = "7:15:60,15:90:120,45:300:1800" - несколько правил через запятую,
    # для простоты отталкиваюсь от последнего (самое ебаное), в дальнейшем можно переосмыслить:)
    interval_rule = response_request.headers['X-Rate-Limit-Ip'].split(",")[-1].split(":")
    globals.requests_interval = float(interval_rule[1]) / float(interval_rule[0])

    try:
        if response['error']['code'] == 3:  # Код ошибки "Лимит запросов за промежуток времени (меняется динамически)"
            while response['error']['code'] == 3:
                time.sleep(float(response_request.headers['Retry-After']))  # Время "блокировки" при нарушении частоты
                response_request = requests.post(url, headers=headers, json=data)
                response = response_request.json()
    except Exception:
        pass

    # Как в браузере QLV8W9efw - это айди из https://www.pathofexile.com/trade/exchange/Archnemesis/QLV8W9efw
    exchange_id = response["id"]

    # Список айдишников результатов поиска
    results = response["result"]

    results = _func_chunks_generators(results, 10)  # Только пачками по 10 штук, иначе не работает апи

    items_bulk = []

    for result_part in results:

        # Из списка получаем строку, разделенную запятой
        result_part = ','.join(result_part)

        # 2) Собираем инфу по результатам
        # Дефолтные штуки, можно не менять
        headers = {
            "Host": "www.pathofexile.com",
            "Connection": "keep-alive",
            "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "text/plain"
        }

        # Ссылка для получения инфы по результатам
        url = f"https://www.pathofexile.com/api/trade/fetch/{result_part}?query={exchange_id}"

        response = requests.get(url, headers=headers)
        response = response.json()

        # Список с инфой в json, примерно такого вида:
        """
    [
        {
            "id": "adadf51a8ad01c328bcf134b8b4955295b662643c645630c8f2890051f2102a7",
            "item": {
                "baseType": "Fragment of Terror",
                "descrText": "Can be used in a personal Map Device.",
                "extended": {
                    "text": "SXRlbSBDbGFzczogTWFwIEZyYWdtZW50cw0KUmFyaXR5OiBOb3JtYWwNCkZyYWdtZW50IG9mIFRlcnJvcg0KLS0tLS0tLS0NClN0YWNrIFNpemU6IDc2LzEwDQotLS0tLS0tLQ0KRmVhciBkcml2ZXMgc3Vydml2YWwuDQotLS0tLS0tLQ0KQ2FuIGJlIHVzZWQgaW4gYSBwZXJzb25hbCBNYXAgRGV2aWNlLg0KLS0tLS0tLS0NCk5vdGU6IH5wcmljZSAyLzkgZXhhbHRlZA0K"
                },
                "flavourText": [
                    "Fear drives survival."
                ],
                "frameType": 0,
                "h": 1,
                "icon": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvTWFwcy9VYmVyRWxkZXIwMSIsInciOjEsImgiOjEsInNjYWxlIjoxfV0/061cd63c5e/UberElder01.png",
                "id": "adadf51a8ad01c328bcf134b8b4955295b662643c645630c8f2890051f2102a7",
                "identified": true,
                "ilvl": 0,
                "league": "Archnemesis",
                "maxStackSize": 10,
                "name": "",
                "note": "~price 2/9 exalted",
                "properties": [
                    {
                        "displayMode": 0,
                        "name": "Stack Size",
                        "type": 32,
                        "values": [
                            [
                                "76/10",
                                0
                            ]
                        ]
                    }
                ],
                "stackSize": 76,
                "typeLine": "Fragment of Terror",
                "verified": true,
                "w": 1
            },
            "listing": {
                "account": {
                    "language": "ru_RU",
                    "lastCharacterName": "barttik",
                    "name": "yavorov2020",
                    "online": {
                        "league": "Archnemesis"
                    }
                },
                "indexed": "2022-03-31T20:12:43Z",
                "method": "psapi",
                "price": {
                    "amount": 0.22222222,
                    "currency": "exalted",
                    "type": "~price"
                },
                "stash": {
                    "name": "15",
                    "x": 81,
                    "y": 0
                },
                "whisper": "@barttik \u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435, \u0445\u043e\u0447\u0443 \u043a\u0443\u043f\u0438\u0442\u044c \u0443 \u0432\u0430\u0441 \u0424\u0440\u0430\u0433\u043c\u0435\u043d\u0442 \u0443\u0436\u0430\u0441\u0430 \u0437\u0430 0.22222222 exalted \u0432 \u043b\u0438\u0433\u0435 \u0412\u043e\u0437\u043c\u0435\u0437\u0434\u0438\u0435 (\u0441\u0435\u043a\u0446\u0438\u044f \"15\"; \u043f\u043e\u0437\u0438\u0446\u0438\u044f: 82 \u0441\u0442\u043e\u043b\u0431\u0435\u0446, 1 \u0440\u044f\u0434)"
            }
        },
        {СЛЕДУЮЩИЙ},
        ...........
        {СЛЕДУЮЩИЙ}  
    ]
    
    # Чисто для себя выписал временно
    "baseType": "Fragment of Terror",
    "maxStackSize": 10,
    "note": "~price 2/9 exalted",
    "stackSize": 76,
    "lastCharacterName": "barttik",
    "price": {
        "amount": 0.22222222,
        "currency": "exalted",
        "type": "~price"
    },
    "stash": {
        "name": "15",
        "x": 81,
        "y": 0
    },
    "whisper": "@barttik \u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435, \u0445\u043e\u0447\u0443 \u043a\u0443\u043f\u0438\u0442\u044c \u0443 \u0432\u0430\u0441 \u0424\u0440\u0430\u0433\u043c\u0435\u043d\u0442 \u0443\u0436\u0430\u0441\u0430 \u0437\u0430 0.22222222 exalted \u0432 \u043b\u0438\u0433\u0435 \u0412\u043e\u0437\u043c\u0435\u0437\u0434\u0438\u0435 (\u0441\u0435\u043a\u0446\u0438\u044f \"15\"; \u043f\u043e\u0437\u0438\u0446\u0438\u044f: 82 \u0441\u0442\u043e\u043b\u0431\u0435\u0446, 1 \u0440\u044f\u0434)"
        """

        full_info = response["result"]

        for info_part in full_info:
            # Проверка на блэклист (БЛ), будет добирать нужное количество с учетом того, что кто-то будет в БЛ
            # if info_part['listing']['account']['lastCharacterName'] in globals.blacklist:
            #     continue

            necessary_info = {}

            necessary_info.update({'icon_link': info_part['item']['icon']})
            necessary_info.update({'offer_id': info_part['id']})
            necessary_info.update({'exchange_id': exchange_id})
            necessary_info.update({'type_line': info_part['item']['typeLine']})
            necessary_info.update({'base_type': info_part['item']['baseType']})
            try:  # Не всегда есть
                necessary_info.update({'note': info_part['item']['note']})
            except KeyError:
                necessary_info.update({'note': ""})
            necessary_info.update({'quantity': info_part['item']['stackSize']})
            necessary_info.update({'max_stack_size': info_part['item']['maxStackSize']})
            necessary_info.update({'indexed': info_part['listing']['indexed']})
            necessary_info.update({'whisper': info_part['listing']['whisper']})
            try:
                necessary_info.update({'stash_info': info_part['listing']['stash']})
            except KeyError:
                necessary_info.update({'stash_info': {}})
            # necessary_info.update({'account_info': info_part['listing']['account']})
            necessary_info.update({'character_name': info_part['listing']['account']['lastCharacterName']})
            # necessary_info.update({'price_info': info_part['listing']['price']})
            necessary_info.update({'amount': info_part['listing']['price']['amount']})
            necessary_info.update({'currency': info_part['listing']['price']['currency']})
            necessary_info.update({'c_price': info_part['listing']['price']['amount'] * (
                globals.exalt_price if info_part['listing']['price']['currency'] == "exalted" else 1)})

            items_bulk.append(necessary_info)

            if qty_offers and len(items_bulk) >= qty_offers:
                break

        if len(items_bulk) >= qty_offers:
            break

        #  Чтобы заценить в удобочитаемом виде, а не в одну строку
        # import json
        # print(json.dumps(results, sort_keys=True, indent=4))

    return items_bulk


def get_offer_by_id(offer_id, exchange_id):
    headers = {
        "Host": "www.pathofexile.com",
        "Connection": "keep-alive",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "text/plain"
    }

    # Ссылка для получения инфы по результатам
    url = f"https://www.pathofexile.com/api/trade/fetch/{offer_id}?query={exchange_id}"

    response = requests.get(url, headers=headers)
    response = response.json()

    try:
        info_part = response["result"][0]
    except IndexError:
        return {}

    offer_info = {}

    offer_info.update({'icon_link': info_part['item']['icon']})
    offer_info.update({'offer_id': info_part['id']})
    offer_info.update({'exchange_id': exchange_id})
    offer_info.update({'type_line': info_part['item']['typeLine']})
    offer_info.update({'base_type': info_part['item']['baseType']})
    try:  # Не всегда есть
        offer_info.update({'note': info_part['item']['note']})
    except KeyError:
        offer_info.update({'note': ""})
    offer_info.update({'quantity': info_part['item']['stackSize']})
    offer_info.update({'max_stack_size': info_part['item']['maxStackSize']})
    offer_info.update({'indexed': info_part['listing']['indexed']})
    offer_info.update({'whisper': info_part['listing']['whisper']})
    try:
        offer_info.update({'stash_info': info_part['listing']['stash']})
    except KeyError:
        offer_info.update({'stash_info': {}})
    # offer_info.update({'account_info': info_part['listing']['account']})
    offer_info.update({'character_name': info_part['listing']['account']['lastCharacterName']})
    # offer_info.update({'price_info': info_part['listing']['price']})
    try:
        offer_info.update({'amount': info_part['listing']['price']['amount']})
    except Exception as err:
        globals.logger.error("Ошибка в currency_counting: " + str(err) + "\n" + traceback.format_exc())
        globals.logger.error(info_part['listing'])
        print(info_part['listing'])
        """
            Traceback (most recent call last):
          File "C:\ProgramData\Anaconda3\lib\threading.py", line 932, in _bootstrap_inner
            self.run()
          File "C:\ProgramData\Anaconda3\lib\threading.py", line 870, in run
            self._target(*self._args, **self._kwargs)
          File "D:/PycharmProjects/poe_trade_bot/main.py", line 146, in trading_loop
            self.make_offer(current_offer)
          File "D:/PycharmProjects/poe_trade_bot/main.py", line 149, in make_offer
            current_offer_info = poe_trade.get_offer_by_id(current_offer[0], current_offer[1])
          File "D:\PycharmProjects\poe_trade_bot\poe_trade.py", line 371, in get_offer_by_id
            offer_info.update({'amount': info_part['listing']['price']['amount']})
        TypeError: 'NoneType' object is not subscriptable
        
        Process finished with exit code -1
        """
    offer_info.update({'currency': info_part['listing']['price']['currency']})
    offer_info.update({'c_price': info_part['listing']['price']['amount'] * (
        globals.exalt_price if info_part['listing']['price']['currency'] == "exalted" else 1)})

    offer_info.update({'exalt_qty': round(offer_info['c_price'] // globals.exalt_price)})
    offer_info.update({'chaos_qty': round(offer_info['c_price'] % globals.exalt_price)})
    return offer_info


def _func_chunks_generators(lst, n):
    """
    Разбивает список на список списков по n элементов. Последний список - сколько осталось элементов (не обязательно n)
    :param lst: Список
    :param n: Сколько элементов будет в каждом списке
    :return: Список списков по n элементов
    """
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


if __name__ == "__main__":  # Для теста
    # _get_items_bulk(("fragment-of-terror",), ("exalted", "chaos",), 5)
    update_offer_list()
