import os

from custom_logger import get_logger

# На время отладки, пока тестишь сам с собой, некоторые отличия от реальной работы. Например, в реальных
# условиях бот не будет ждать паузу, если уже в процессе итерации торговли (после виспера и до совершения трейда)
debugging: bool = False

bot_name = "КВДТ_Тётя"
cells = [(14, 11), (14, 64), (14, 116), (14, 169), (14, 222), (67, 11), (67, 63), (67, 116), (67, 169), (67, 221),
         (120, 11), (120, 63), (120, 116), (120, 169), (120, 221), (172, 11), (172, 64), (172, 116), (172, 169),
         (172, 222), (225, 11), (225, 63), (225, 116), (225, 169), (225, 221), (278, 11), (278, 63), (278, 116),
         (278, 169), (278, 221), (330, 11), (330, 64), (330, 116), (330, 169), (330, 222), (383, 11), (383, 63),
         (383, 116), (383, 169), (383, 221), (436, 11), (436, 63), (436, 116), (436, 169), (436, 221), (488, 11),
         (488, 64), (488, 116), (488, 169), (488, 222), (541, 11), (541, 63), (541, 116), (541, 169), (541, 221),
         (594, 11), (594, 63), (594, 116), (594, 169), (594, 221)]
logs_path = r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt"
POESESSID = "86df337a72bca4d866865c0fd76e6bc4"  # Чтобы снять лимит с количества результатов (есть в браузере в куках)
tesseract_exe_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
testing_usernames = [
    # "КВДТ_Тётя",
    "чифтейн"
]

# Времмено ввод вручную. При каждом запуске попросит ввести вручную, если только тут не установлено значение (т.е. = 0).
# Для тестов (или если часто перезапускаем бота) можно тут ввести, чтобы каждый раз не инпутить
exalt_qty: int = 0
chaos_qty: int = 0

# При минимальном значении экзов останавливается
exalt_minimum: int = 3
# При минимальном значении хаосов - докупает их (значение в идеале около exalt_minimum в хаосах по прайсу экза)
chaos_minimum: int = 500

# region Хоткеи
pause_hotkey = "f12"  # Установки/снятия паузы
close_hotkey = "ctrl + f12"  # Мгновенное завершение
close_after_trade_hotkey = "ctrl + shift + f12"  # Завершение программы, но с ожиданием завершения текущей торговли
# endregion

# region Глобальные переменные

# Словарь с игнорщиками, при превышении qty_ignores попадает в блэклист
badlist: dict = dict()  # {'Имя': Количество_игноров}

# Блэклист, периодически переформируется из бэдлиста
blacklist: list = list()

exalt_price: int = 173

invite_waiting_time = 30

items = [
    # {
    #     'name': "fragment-of-terror",
    #     'bulk_price': 33
    # },
    # {
    #     'name': "fragment-of-emptiness",
    #     'bulk_price': 33
    # },
    {
        'name': "fragment-of-shape",
        'bulk_price': 86
    },
    {
        'name': "fragment-of-knowledge",
        'bulk_price': 86
    },

]

# Причины незаконченности трейда (каждый вызов continue в трейд-цикле должен сопровождаться причиной, для анализа)
failure_reasons = {
    'party_timeout': "party_timeout",
    'teleport_problem': "teleport_problem",
    'trade_timeout': "trade_timeout",
    'trade_bad_deal': "trade_bad_deal",  # Когда продавец положил не то, что надо (+ надо сделать скрин трейда)
    'trade_other_problem': "trade_other_problem"
}

last_check_poetrade = None

logger = get_logger(debugging)

offer_list: list = list()

# Как часто делать обновление списка с поетрейда
poetrade_info_update_frequency = 300

# В пое в АПИ постоянно меняется правило "сколько можно делать запросов в какое кол-во времени", пересчитывается
# в процессе запросов к апи
requests_interval: float = 6.67

# Статусы текущего состояния бота
statuses = {
    'finding_new_offer': "finding_new_offer",
    'waiting_party_request': "waiting_party_request",
    'waiting_trade_request': "waiting_trade_request",
    'trading': "trading"
}

# Пути к шаблонам
templates = {
    'accept_button': {'image': r"images\templates\accept_button.png", 'size': (180, 40)},
    'chaos orb': {'image': r"images\templates\chaos orb.png", 'size': (50, 31)},
    'chaos_orb_in_stash_tab': {'image': r"images\templates\chaos_orb_in_stash_tab.png", 'size': (40, 30)},
    'close_tab': {'image': r"images\templates\close_tab.png", 'size': (30, 30)},
    'empty_cell': {'image': r"images\templates\empty_cell.png", 'size': (48, 47)},
    'exalted orb': {'image': r"images\templates\exalted orb.png", 'size': (50, 32)},
    'inventory_tab': {'image': r"images\templates\inventory_tab.png", 'size': (215, 75)},
    'stash_tab': {'image': r"images\templates\stash_tab.png", 'size': (220, 70)},
    'stash': {'image': r"images\templates\stash.png", 'size': (70, 22)},
    'trade_tab': {'image': r"images\templates\trade_tab.png", 'size': (180, 56)},

    'Fragment of Terror': {'image': r"images\templates\Fragment of Terror.png", 'size': (50, 30)},
    'Fragment of Emptiness': {'image': r"images\templates\Fragment of Emptiness.png", 'size': (50, 30)},
    'Fragment of Shape': {'image': r"images\templates\Fragment of Shape.png", 'size': (50, 30)},
    'Fragment of Knowledge': {'image': r"images\templates\Fragment of Knowledge.png", 'size': (50, 30)}

}

# Время ожидания трейда после ТП в хайдаут к продавцу
trade_waiting_time = 120

qty_ignores = 10  # Сколько раз надо проигнорить трейд, чтобы быть в ЧС


# endregion

# region Общие функции
def update_blacklist():
    global blacklist
    blacklist = [key for key, val in badlist.items() if val >= qty_ignores]


def trade_info_pattern():
    return dict.fromkeys(
        ['offer_id', 'result', 'failure_reason', 'trade_screen', ])  # Додумать по статистике, дополнить
# endregion
