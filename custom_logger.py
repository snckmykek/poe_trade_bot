import logging


class CustomFormatter(logging.Formatter):

    blue = "\x1b[0;34m"
    grey = "\x1b[0;37m"
    purple = "\x1b[0;35m"
    red = "\x1b[0;31m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    format = "%(asctime)s - [%(levelname)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: purple + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(debugging=False):
    # logger - Механизм вывода логов в файл или консоль
    logger = logging.getLogger("poe_trade_bot")  # Просто рандомное имя
    logger.setLevel(logging.DEBUG)  # Уровень обработки логов (от этого и выше)
    """
    Все уровни:
    CRITICAL
    ERROR
    WARNING
    INFO
    DEBUG
    NOTSET
    """

    # Форматтер - КАК выводить логи. Кастомный = цветной
    cf = CustomFormatter()

    # Хендлер - КУДА выводить логи.
    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # В консоль выводим все уровни (от дебага и выше)
    if debugging:
        console_handler.setFormatter(cf)  # Добавляем кастомный форматтер
    else:
        console_handler.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s]: %(message)s"))  # Дефолтный
    logger.addHandler(console_handler)  # Добавляем логгеру хендлер

    # Файловый хендлер
    file_handler = logging.FileHandler('poe_trade_bot_logging.log')
    file_handler.setLevel(logging.WARNING)  # В консоль выводим все уровни (от дебага и выше)
    # Добавляем дефолтный, т.к. в файле цвета не поменять
    file_handler.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s]: %(message)s"))
    logger.addHandler(file_handler)  # Добавляем логгеру еще один хендлер, то есть будет и в файл и в консоль печатать

    return logger
