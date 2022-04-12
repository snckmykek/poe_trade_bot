"""
# Нужно установить pip install pywin32==225
# Нужно установить pip install brotli

Общая логика и прочая инфа.
1. Кол-во остатков (пока выключается, если нет остатков) + закупка хаосов
2 . Чек ника (мб разные языки)
3. Сделать в словаре с предметами еще указание курренси за которую есть смысл покупать (не для всех т.к. мб всегда не
выгодно но время на запрос придется тратить)

В далёкой перспективе:
1. Телега
2. Если оффер слишком большой (не влезает в инвернарь), рабивать его на несколько и писать висперы на размер инвентаря
3. Открывать вкладку с курренси, если не открыта в стеше
4. Пропускать афкашных
5. Запихать всё в 1 виспер (то есть заменить количеста на нужные в дефолтном, как на сайте)
6. [CRITICAL]: Список офферов с поетрейда пустой. Жду 300 (globals.poetrade_info_update_frequency) и пробую снова. - Когда
такая хрень, надо не 300 сек ждать, а до обновления (как-то чекать, что обновился список [INFO]: Оффер-лист обновлен.)
"""
import json
import traceback

try:
    import ctypes
    from datetime import datetime
    import keyboard
    import os
    import time
    import threading

    # import py_win_keyboard_layout

    import bot
    import poe_trade
    import globals
    import storage


    class TradeBot:
        current_status: str = None
        need_close_after_trade: bool = False
        paused: bool = False
        trade_info: list = list()  # Статистика

        def __init__(self):
            # Хоткей для установки/снятия паузы
            keyboard.add_hotkey(globals.pause_hotkey, self.change_pause_state)

            # Хоткей для мгновенного завершения программы
            keyboard.add_hotkey(globals.close_hotkey, lambda: instant_exit())

            # Хоткей для завершения программы, но с ожиданием завершения текущей торговли
            keyboard.add_hotkey(globals.close_after_trade_hotkey, self._set_close_after_trade)

            self.upload_settings()

        @staticmethod
        def upload_settings():
            try:
                with open("storage/settings.json", 'r', encoding="Windows-1251") as file:
                    settings = json.load(file)

                    for key, val in settings.items():
                        setattr(globals, key, val)

            except FileNotFoundError:
                pass

        # region Прочие
        def start(self):
            if not _check_kb_layout():
                globals.logger.critical("Нужно сменить раскладку на англ и перезапустить. Завершаю работу.")
                # globals.logger.critical("На момент запуска раскладка была не EN. Раскладка сменена на EN, но "
                #                         "нужно перезапустить заново. Завершаю работу.")
                instant_exit()

            self.input_qty()

            # Снимаем с паузы, если есть
            self.paused = False

            globals.logger.info("Перед запуском проверяю открытую вкладку с курренси в стеше.")
            while not bot.is_tab_active('stash', (221, 19, 220, 70)):
                bot.open_stash()
            if bot.is_tab_active('chaos_orb_in_stash', (530, 260, 40, 30)):
                globals.logger.info("Вкладка с курренси открыта в стеше. Начинаю работу.")
            else:
                globals.logger.critical("Вкладка с курренси не открыта в стеше. Завершаю работу.")
                instant_exit()

            storage.upload_badlist()
            poe_trade.update_exalt_price()

            # Запускаем поток с обновлением инфы по офферам
            t = threading.Thread(target=self.poetrade_loop)
            t.start()

            # Запускаем основной поток с циклом для торговли
            t = threading.Thread(target=self.trading_loop)
            t.start()

        @staticmethod
        def input_qty():
            if not globals.exalt_qty:
                globals.exalt_qty = int(input("Ввести кол-во экзов: "))

            if not globals.chaos_qty:
                globals.chaos_qty = int(input("Ввести кол-во хаосов: "))

        def _check_pause(self):
            # Функция завершится в момент окончании действия паузы
            while self.paused:
                time.sleep(1)
            return

        def change_pause_state(self):
            self.paused = not self.paused
            globals.logger.info(f"{globals.pause_hotkey} - Остановлен: {self.paused}")

        @staticmethod
        def _poetrade_info_is_relevance():
            if not globals.last_check_poetrade:
                return False

            return (datetime.now() - globals.last_check_poetrade).total_seconds() < globals.poetrade_info_update_frequency

        # endregion

        def poetrade_loop(self):

            while True:
                _datetime = datetime.now()

                self._check_pause()

                poe_trade.update_offer_list()

                _interval = globals.poetrade_info_update_frequency - (datetime.now() - _datetime).total_seconds()
                if _interval > 0:
                    time.sleep(_interval)

        # region Трейдинг
        def trading_loop(self):
            """
            Бесконеяный цикл берет из отдельно формирующегося списка офферов самый первый и начинает его отрабатывать
                в трейд-итерации.
            Этапы трейд-итерации:
            1. Получить и проверить оффер на актуальность (повторить запрос на поетрейд по айди сделки)
            1.1. Проверить, хватит ли валюты и ячеек в стеше, чтобы совершить оффер
            2. Сформировать инфу для trade_info
            3. Написать виспер
            4. Принять пати (или дропнуть после globals.party_waiting_time секунд ожидания) (+ проверить кто пати кинул)
            4.1. Очистить инвентарь и взять нужное кол-во валюты на новый трейд
            5. ТП в хайдаут продавца (+ посмотреть, что именно к нужному прыгнул, если в пати несколько человек)
            6. Принять трейд (или дропнуть после globals.trade_waiting_time секунд ожидания) (+ проверить кто трейд кинул)
            7. Замутить трейд, при возникновении проблемы - сделать скрин трейда и сохранить в папку fail_trades_screens.
                В логи прописать масимально инфы по трейду + название скрина (лог сделать уровня globals.logger.critical)
            7.1. Спасибо
            7.2. Пересчитать остатки валюты
            8. Вернуться в свой хайдаут
            """
            while True:
                if (globals.exalt_qty < globals.exalt_minimum) or (globals.chaos_qty < globals.chaos_minimum):
                    globals.logger.critical(f"Экзальтов: {globals.exalt_qty}, хаосов: {globals.chaos_qty}. "
                                            f"Это меньше минимума, выключаюсь.")  # Временно
                    instant_exit()

                if not self._poetrade_info_is_relevance():
                    _interval = len(globals.items) * globals.requests_interval + 1
                    globals.logger.critical(
                        f"Инфа с поетрейда не актуальна. Жду {_interval} "
                        f"(len(globals.items) * globals.requests_interval + 1) и пробую проверяю снова.")
                    time.sleep(_interval)
                    continue
                elif not globals.offer_list:
                    globals.logger.critical(
                        f"Список офферов с поетрейда пустой. Жду {globals.poetrade_info_update_frequency} "
                        f"(globals.poetrade_info_update_frequency) и пробую снова.")
                    time.sleep(globals.poetrade_info_update_frequency)
                    continue

                self._check_pause()

                # 1. Получить и проверить оффер на актуальность (повторить запрос на поетрейд по айди сделки)
                current_offer = globals.offer_list.pop(0)  # Возвращает и удаляет первый элемент списка
                globals.logger.info(
                    f"Начал трейд-итерацию. Проверяю offer_id: {current_offer[0]}, exchange_id: {current_offer[1]}")

                self.make_offer(current_offer)

        def make_offer(self, current_offer):
            current_offer_info = poe_trade.get_offer_by_id(current_offer[0], current_offer[1])
            if not current_offer_info:
                globals.logger.info(f"Оффер не актуален, завершаю трейд-итерацию.")
                return

            if current_offer_info['quantity'] * current_offer_info['c_price'] == 0:
                globals.logger.info(
                    f"Проблема с приведённой ценой: {current_offer_info['c_price']},"
                    f"количество: {current_offer_info['quantity']}, "
                    f"цена: {current_offer_info['amount']},"
                    f"валюта: {current_offer_info['currency']}. Завершаю трейд-итерацию.")
                return

            globals.logger.info(f"Оффер актуален, отрабатываю. "
                                f"\nНик: {current_offer_info['character_name']}, "
                                f"\nИтем: {current_offer_info['type_line']}, "
                                f"\nКоличество: {current_offer_info['quantity']}, "
                                f"\nЦена: {current_offer_info['c_price']}")

            # 1.1. Проверить, хватит ли валюты и ячеек в стеше, чтобы совершить оффер
            if not self.trade_possibility(current_offer_info):
                globals.logger.info(f"Трейд невозможен из-за нехватки валюты или места в инвентаре. "
                                    f"Завершаю трейд-итерацию.")
                self.check_buy_chaos()
                return

            # Пропуск "нетестовых" юзеров при отладке
            if globals.debugging:
                if globals.testing_usernames and not current_offer_info[
                                                         'character_name'] in globals.testing_usernames:
                    globals.logger.debug(f"Персонаж {current_offer_info['character_name']} не входит "
                                         f"в список тестовых globals.testing_usernames. Иду некст")
                    time.sleep(5)
                    return

            # 2. Сформировать инфу для trade_info
            current_trade_info = globals.trade_info_pattern()
            current_trade_info['offer_id'] = current_offer_info['offer_id']

            self._check_pause()

            # 3. Написать виспер
            additional_whisper = self.get_additional_whisper(current_offer_info)
            bot.send_whisper(current_offer_info['whisper'], additional_whisper)

            # 4. Принять пати (или дропнуть после globals.party_waiting_time секунд ожидания)
            #    (+ проверить кто пати кинул)
            if globals.debugging:
                self._check_pause()

            if not bot.party_accepted(current_offer_info['character_name']):
                # Если сюда попали, то пати не кинули, идем некст
                globals.logger.info(f"Не дождался пати, завершаю трейд-итерацию.")

                current_trade_info['result'] = False
                current_trade_info['failure_reason'] = globals.failure_reasons['party_timeout']
                self.trade_info.append(current_trade_info)

                # Записываем в бэдлист
                try:
                    globals.badlist[current_offer_info['character_name']] += 1
                except KeyError:
                    globals.badlist.update({current_offer_info['character_name']: 1})
                storage.save_badlist()
                return
            globals.logger.debug("Принял пати.")

            # 4.1. Очистить инвентарь и взять нужное кол-во валюты на новый трейд
            bot.put_take_from_stash(current_offer_info['quantity'] * current_offer_info['c_price'])
            globals.logger.debug("Взял валюту.")

            # 5. ТП в хайдаут продавца (+ посмотреть, что именно к нужному прыгнул, если в пати несколько человек)
            if globals.debugging:
                self._check_pause()

            if not bot.teleported(current_offer_info['character_name']):
                # Если сюда попали, то проблема с ТП, идем некст
                globals.logger.info(f"Не удалось телепортироваться, завершаю трейд-итерацию.")
                current_trade_info['result'] = False
                current_trade_info['failure_reason'] = globals.failure_reasons['teleport_problem']
                self.trade_info.append(current_trade_info)

                return
            globals.logger.debug("Телепортнулся в хайдаут.")

            # 6. Принять трейд (или дропнуть после globals.trade_waiting_time секунд ожидания)
            #    (+ проверить кто трейд кинул)
            if globals.debugging:
                self._check_pause()

            if not bot.trade_accepted(current_offer_info['character_name'], True):
                # Если сюда попали, то трейд не кинули, идем некст
                globals.logger.info(f"Не дождался трейда, завершаю трейд-итерацию.")
                current_trade_info['result'] = False
                current_trade_info['failure_reason'] = globals.failure_reasons['trade_timeout']
                self.trade_info.append(current_trade_info)

                bot.go_home()
                return
            globals.logger.debug("Принял трейд.")

            # 7. Замутить трейд, при возникновении проблемы - сделать скрин трейда и сохранить в папку
            #    fail_trades_screens. В логи прописать масимально инфы по трейду + название скрина
            #    (лог сделать уровня globals.logger.critical)
            if globals.debugging:
                self._check_pause()

            trade_result = bot.trade_completed(
                current_offer_info['c_price'], current_offer_info['quantity'],
                current_offer_info['type_line'], current_offer_info['character_name'])
            if not trade_result['completed']:
                # Если сюда попали, то в трейде что-то пошло не так
                globals.logger.critical(
                    f"Что-то пошло не так во время трейда, скрин: {trade_result['trade_screen']}, "
                    f"trade_id: {current_offer_info['offer_id']}. "
                    f"\nЗавершаю трейд-итерацию.")
                current_trade_info['result'] = False
                current_trade_info['failure_reason'] = globals.failure_reasons['trade_timeout']
                current_trade_info['trade_screen'] = trade_result['trade_screen']
                self.trade_info.append(current_trade_info)

                bot.go_home()
                return
            globals.logger.debug("Завершил тред.")

            # Записываем в бэдлист с минусов (т.к. иногда челам тупить позволено, хотя бы через раз)
            try:
                globals.badlist[current_offer_info['character_name']] -= 1
            except KeyError:
                globals.badlist.update({current_offer_info['character_name']: -1})
            storage.save_badlist()

            # 7.1. Спасибо
            bot.ty(current_offer_info['character_name'])

            # 7.2. Пересчитать остатки валюты
            self.recalculate_currencies(current_offer_info['exalt_qty'], current_offer_info['chaos_qty'])

            # 8. Вернуться в свой хайдаут
            if globals.debugging:
                self._check_pause()

            bot.go_home()

            current_trade_info['result'] = True
            self.trade_info.append(current_trade_info)
            globals.logger.info(f"Закончил трейд-итерацию успешно.")

            if self.need_close_after_trade:
                globals.logger.info("Остановился после окончания трейд-итерации.")
                instant_exit()

        @staticmethod
        def check_buy_chaos():
            globals.logger.info("Проверяю возможность докупить хаосы за экзы.")
            if globals.chaos_qty < globals.chaos_minimum:
                # Переводим экзальты в хаосы
                exalt_in_chaos = globals.exalt_qty * globals.exalt_price
                minimum_exalt_in_chaos = globals.exalt_minimum * globals.exalt_price
                # Считаем сколько всего хаосов и в экзах и в хаосах
                total_chaos = exalt_in_chaos + globals.chaos_qty
                # Хаосов нужно примерно столько же, сколько экзов по прайсу
                need_chaos = total_chaos / 2

                # Если в хаосы нужно перевести экзальтов столько, что останется меньше минимума, то нужно скорректировать
                if total_chaos - need_chaos < minimum_exalt_in_chaos:
                    need_chaos = total_chaos - minimum_exalt_in_chaos

                # не больше 5000 в конечном счете
                if need_chaos > 5000:
                    need_chaos = 5000

                need_buy_chaos = need_chaos - globals.chaos_qty

                # while need_buy_chaos > 0:

        @staticmethod
        def get_additional_whisper(current_offer_info):
            if (  # 1 штука за хаосы
                    (current_offer_info['quantity'] == 1) and (current_offer_info['currency'] == 'chaos')
            )\
                    or (  # 1 штука за целое кол-во экзов
                    (current_offer_info['quantity'] == 1)
                    and (current_offer_info['currency'] == 'exalted')
                    # exalt_qty - за всё, amount - за одну шт
                    and (current_offer_info['exalt_qty'] == current_offer_info['amount'])
            ):
                return ""

            c_price = current_offer_info['quantity'] * current_offer_info['c_price']
            exalt_qty = round(c_price // globals.exalt_price)
            chaos_qty = round(c_price % globals.exalt_price)

            additional_whisper = f"@{current_offer_info['character_name']} {current_offer_info['quantity']} for "
            if exalt_qty and not chaos_qty:
                additional_whisper += f"{exalt_qty} exalted"
            elif not exalt_qty and chaos_qty:
                additional_whisper += f"{chaos_qty} chaos"
            else:
                additional_whisper += f"{exalt_qty} exalted and {chaos_qty} chaos"

            return additional_whisper

        @staticmethod
        def recalculate_currencies(exalt_qty, chaos_qty):
            globals.exalt_qty -= exalt_qty
            globals.chaos_qty -= chaos_qty

        def _set_close_after_trade(self):
            self.need_close_after_trade = True

        def _set_current_status(self, new_status):
            # Такой сложный механизм нужен для контроля статусов, чтобы избежать ошибки в коде
            self.current_status = globals.statuses[new_status]

        @staticmethod
        def trade_possibility(current_offer_info):
            if current_offer_info['exalt_qty'] > globals.exalt_qty\
                    or current_offer_info['chaos_qty'] > globals.chaos_qty:
                return False

            if False:  # Добавить проверку стеша, влезает ли
                return False

            return True

        # endregion


    def instant_exit():
        # storage.save_badlist()
        os._exit(0)


    def _check_kb_layout():
        u = ctypes.windll.LoadLibrary("user32.dll")
        pf = getattr(u, "GetKeyboardLayout")
        if hex(pf(0)) == '0x4090409':  # en
            return True
        else:
            # Меняем на en, но нужен перезапуск
            # py_win_keyboard_layout.change_foreground_window_keyboard_layout(0x04090409)
            return False


    if __name__ == "__main__":
        TradeBot().start()

except Exception as err:
    print(str(err) + "\n" + traceback.format_exc())
    input()
