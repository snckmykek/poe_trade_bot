import shutil
from datetime import datetime
import math
# import pytesseract

import globals
from old_bot import *

# pytesseract.pytesseract.tesseract_cmd = globals.tesseract_exe_path


def party_accepted(username):
    """
    :return: True, если пати кинули или False, если прошло время settings.party_waiting_time и не кинули
    """
    _datetime = datetime.now()

    while True:
        if (datetime.now() - _datetime).total_seconds() > globals.invite_waiting_time * \
                (0.3 if username in globals.blacklist else 1):
            return False
        elif _invited(username):  # Проверить кинули ли пати
            return True


def _invited(username):
    pyautogui.screenshot(f"images/screenshots/_accept_button.png", region=(1535, 765, 180, 40))
    img_rgb = cv2.imread(f"images/screenshots/_accept_button.png")
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(globals.templates['accept_button']['image'], 0)
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    if res < 0.70:
        time.sleep(1)
        return False

    if not username:
        return False

    # pyautogui.screenshot(r"images\screenshots\_username.png", region=(1575, 695, 200, 25))
    # img = cv2.imread(r"images\screenshots\_username.png")
    # _username = pytesseract.image_to_string(img)
    # if username in _username:
    pyautogui.moveTo(1625, 785)
    pyautogui.click()
    time.sleep(.5)
    return True


def go_home():
    _send_to_chat(f'/kick {globals.bot_name}')
    _send_to_chat('/hideout')
    time.sleep(5)


def put_take_from_stash(c_price):

    if is_tab_active('stash', (221, 19, 220, 70)):
        currency_put_in()

        exalt_qty = c_price // globals.exalt_price
        chaos_qty = c_price % globals.exalt_price

        if exalt_qty:
            currency_from_stash(exalt_qty, 'exalted orb')

        currency_from_stash(chaos_qty, 'chaos orb', math.ceil(exalt_qty/10))

    else:
        open_stash(lambda: put_take_from_stash(c_price))


def send_whisper(whisper, additional_whisper):
    _send_to_chat(whisper)

    if additional_whisper:
        time.sleep(1)
        _send_to_chat(additional_whisper)


def teleported(username):
    _send_to_chat(f'/hideout {username}')
    time.sleep(1)
    return True


def trade_completed(currency_quant, item_quant, item_name, username):
    _datetime = datetime.now()
    attempts = 2
    trade_error = False
    while True:
        if (datetime.now() - _datetime).total_seconds() > globals.trade_waiting_time:
            return {'completed': False, 'trade_screen': _save_trade_screen()}
        if trade_error:
            if trade_accepted(username):
                if attempts:
                    attempts -= 1
                    _datetime = datetime.now()
                trade_error = False
            else:
                continue

        # Чтобы лишний раз не делать currency_put_in
        trade_status = get_trade_status()
        if trade_status == 'accepted':
            return {'completed': True, 'trade_screen': ""}

        if not currency_put_in(True):
            trade_error = True
            continue

        while True:
            # Чтобы надолго не застрять в цикле
            trade_status = get_trade_status()
            if trade_status == 'accepted':
                return {'completed': True, 'trade_screen': ""}
            elif trade_status == 'cancelled':
                trade_error = True
                continue

            if is_tab_active('trade', (536, 69, 180, 56)):
                if currency_counting(item_quant, item_name):
                    break
            else:
                if trade_accepted(username):
                    continue
            if (datetime.now() - _datetime).total_seconds() > globals.trade_waiting_time:
                return {'completed': False, 'trade_screen': _save_trade_screen()}

        if not is_tab_active('trade', (536, 69, 180, 56)):  # олдовый шаблон сохранен именно на этот регион
            trade_error = True
            continue

        pyautogui.moveTo(378, 836, .2)  # accept trade
        pyautogui.click()
        time.sleep(2)

        # Перенес в цикл, если всё ок, удаляем это
        # trade_status = get_trade_status()
        # if trade_status == 'accepted':
        #     return {'completed': True, 'trade_screen': ""}
        # elif trade_status == 'cancelled':
        #     trade_error = True


def _save_trade_screen():
    screen_path = shutil.copy(
        r"images/screenshots/_currency_counting.png",
        f"images/screenshots/errors/_currency_counting_{datetime.now().strftime('%Y-%m-%d_%H.%M.%S')}.png")
    return screen_path


def get_trade_status():
    with open(globals.logs_path, 'r', encoding="utf-8") as f:
        for line in f:
            if 'Trade accepted.' in line:
                return 'accepted'
            elif 'Trade cancelled.' in line:
                return 'cancelled'


def trade_accepted(character_name, is_first=False):
    """
    :return: True, если трейд кинули или False, если прошло время settings.trade_waiting_time и не кинули
    """
    _datetime = datetime.now()

    while True:
        if (datetime.now() - _datetime).total_seconds() > globals.invite_waiting_time + \
                (globals.trade_waiting_time if is_first else 0):
            return False
        elif _invited(character_name):  # _trade_invited():  # Проверить кинули ли трейд
            open(globals.logs_path, 'w').close()
            return True


def _send_to_chat(message):
    pyperclip.copy(message)
    pyautogui.press('enter')
    time.sleep(.02)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(.02)
    pyautogui.press('enter')
    time.sleep(.02)


def ty(username):
    _send_to_chat(f'@{username} ty')
