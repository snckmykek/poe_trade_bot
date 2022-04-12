import os
import traceback

import pyautogui
import globals
import time
import random
import cv2
import pyperclip
import numpy as np

currency_stash = {
    'chaos orb': {
        # 'stack': globals.chaos_qty,
        # 'stack_size': 10,
        'x': 544,  # 529
        'y': 252  # 237
    },
    'exalted orb': {
        # 'stack': globals.exalt_qty,
        # 'stack_size': 10,
        'x': 300,  # 285
        'y': 252  # 237
    }
}


def currency_counting(amount, item):
    # 1. Активация (проведение мышкой) ячеек в окне трейда
    region = (300, 195, 652, 282)
    non_empty_cells = get_non_empty_cells(region)
    for cell in non_empty_cells:
        pyautogui.moveTo(region[0] + cell[0] + (50 / 2), region[1] + cell[1] + (50 / 2))  # w,h
    pyautogui.moveTo(1, 1)
    time.sleep(.1)

    # 2. Поиск нужных итемов, расчет количества
    pyautogui.moveTo(1, 1)
    pyautogui.screenshot(r"images\screenshots\_currency_counting.png", region=(300, 195, 652, 282))
    img_rgb = cv2.imread(r"images\screenshots\_currency_counting.png")
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template_item = cv2.imread(globals.templates[item]['image'], 0)

    res = cv2.matchTemplate(img_gray, template_item, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(res >= threshold)
    xy = list(zip(*loc[::-1]))
    count = 0
    if xy:
        xy_fixed = [xy[0]]
        for i in xy:
            matched = False
            for j in xy_fixed:
                if abs(i[0] - j[0]) < 15 and abs(i[1] - j[1]) < 15:
                    matched = True
                    break
            if not matched:
                xy_fixed.append(i)

        threshold = 0.66
        for i in xy_fixed:
            x_numbers = []
            result = 0
            for j in range(10):
                try:
                    amount_img = img_gray[i[1] - 16:i[1] + 7, i[0] - 3:i[0] + 40]
                    template_num = cv2.imread(f"images/numbers/{j}.png", 0)
                    res_num = cv2.matchTemplate(amount_img, template_num, cv2.TM_CCOEFF_NORMED)
                except Exception as err:
                    globals.logger.error("Ошибка в currency_counting: " + str(err) + "\n" + traceback.format_exc())
                    amount_img = img_gray[i[1] - 16:i[1] + 7, i[0]:i[0] + 40]
                    template_num = cv2.imread(f"images/numbers/{j}.png", 0)
                    res_num = cv2.matchTemplate(amount_img, template_num, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res_num >= threshold)[-1]
                if loc.size > 0:
                    result = j
                    x_numbers.append([j, *loc])
            if len(x_numbers) == 1:
                result = result
            if len(x_numbers) > 1:
                if x_numbers[0][1] < x_numbers[1][1]:
                    result = x_numbers[0][0] * 10 + x_numbers[1][0]
                else:
                    result = x_numbers[1][0] * 10 + x_numbers[0][0]
            count += result

    if count >= amount:
        return True
    else:
        return False


def currency_from_stash(amount, currency, extra_cells=0):
    if is_tab_active('stash', (221, 19, 220, 70)):
        stack_size = 10
        stack = globals.chaos_qty if currency == "chaos orb" else globals.exalt_qty

        if stack - amount == 0:
            pyautogui.moveTo(currency_stash[currency]['x'], currency_stash[currency]['y'], random.uniform(.1, .2))
            pyautogui.keyDown('ctrl')
            pyautogui.click(clicks=(amount // stack_size + 1 if amount != stack_size else amount // stack_size),
                            interval=.2)
            pyautogui.keyUp('ctrl')
            return

        pyautogui.moveTo(currency_stash[currency]['x'], currency_stash[currency]['y'], random.uniform(.1, .2))
        pyautogui.keyDown('ctrl')
        pyautogui.click(clicks=round(amount // stack_size), interval=.2)
        pyautogui.keyUp('ctrl')
        if amount % stack_size != 0:
            x, y = 1300, 615 - 52.5
            for i in range(
                    (amount // stack_size if amount % stack_size == 0 else amount // stack_size + 1) + extra_cells):
                y += 52.5
                if y > 830:
                    y = 615
                    x += 52.5
            pyautogui.keyDown('Shift')
            pyautogui.click()
            pyautogui.write(f'{amount % stack_size}')
            pyautogui.keyUp('Shift')
            pyautogui.press('Enter')
            pyautogui.moveTo(x, y, random.uniform(.2, .3))  # 1560 773
            time.sleep(.2)
            pyautogui.click()
    else:
        # open_stash(f"currency_from_stash(amount={amount},currency='{currency}',extra_cells={extra_cells})")
        open_stash(lambda: currency_from_stash(amount, currency, extra_cells))


def currency_put_in(is_trade=False):
    region = (1892, 781, 30, 30)
    while is_tab_active("close", region):
        pyautogui.moveTo(region[0] + (globals.templates['close_tab']['size'][0] / 2),
                         region[1] + (globals.templates['close_tab']['size'][1] / 2))  # w,h
        pyautogui.click()
        time.sleep(.2)

    region = (1260, 580, 655, 280)

    attempts = 3
    while attempts:
        non_empty_cells = get_non_empty_cells(region)

        if not non_empty_cells:
            return True

        pyautogui.keyDown('ctrl')
        for cell in non_empty_cells:
            pyautogui.moveTo(region[0] + cell[0] + (globals.templates['empty_cell']['size'][0] / 2),
                             region[1] + cell[1] + (globals.templates['empty_cell']['size'][1] / 2))  # w,h
            pyautogui.click()
        pyautogui.keyUp('ctrl')

        if is_trade:
            return True

        attempts -= 1

    return False


def get_non_empty_cells(region):
    non_empty_cells = []
    pyautogui.moveTo(1, 1)
    pyautogui.screenshot(r"images\screenshots\_cells_region.png", region)  # (1260, 580, 655, 280) - inventory
    img_rgb = cv2.imread(r"images\screenshots\_cells_region.png")
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(globals.templates['empty_cell']['image'], 0)

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.7
    loc = np.where(res >= threshold)
    xy = list(zip(*loc[::-1]))
    xy_fixed = []
    if xy:
        xy_fixed = [xy[0]]
        for i in xy:
            matched = False
            for j in xy_fixed:
                if abs(i[0] - j[0]) < 15 and abs(i[1] - j[1]) < 15:
                    matched = True
                    break
            if not matched:
                xy_fixed.append(i)
    for cell in globals.cells:
        for empty_cell in xy_fixed:
            if abs(empty_cell[0] - cell[0]) < 10 and abs(empty_cell[1] - cell[1]) < 10:
                break
        else:
            non_empty_cells.append(cell)

    return non_empty_cells


def is_tab_active(tab, region):  # str tab, couple region, stash=(221, 19, 220, 70), trade=(536, 69, 180, 56)
    pyautogui.moveTo(1, 1)
    pyautogui.screenshot(f"images/screenshots/_is_{tab}_active.png", region=region)
    img_rgb = cv2.imread(f"images/screenshots/_is_{tab}_active.png")
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(globals.templates[f'{tab}_tab']['image'], 0)
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    if res >= 0.70:
        return True
    else:
        return False


def open_stash(func=None):
    pyautogui.press('space')
    pyautogui.moveTo(1, 1)
    pyautogui.screenshot(r"images\screenshots\_finding_stash.png")
    img_rgb = cv2.imread(r"images\screenshots\_finding_stash.png")
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(globals.templates['stash']['image'], 0)

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.9
    loc = np.where(res >= threshold)
    xy = list(zip(*loc[::-1]))
    if not xy:
        globals.logger.critical("Не нашел стеш на экране.")
        os._exit(0)
        return
    x, y = xy[0][0] + (globals.templates['stash']['size'][0] / 2), xy[0][1] + (
            globals.templates['stash']['size'][1] / 2)
    pyautogui.moveTo(x, y, .2)
    pyautogui.click()

    time.sleep(2)

    if func:
        func()
