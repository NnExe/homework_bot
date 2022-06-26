import os
import sys
import time
import requests
import telegram
import logging
from exceptions import (
    InaccessibilityEndpointException,
    EmptyAnswerException,
    WrongAnswerException,
)
from typing import Union, List, Dict, Type

from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DEBUG_LEVEL = os.getenv('DEBUG_LEVEL') or 'INFO'

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_SCHEME = {
    "id": int,
    "status": str,
    "homework_name": str,
    "reviewer_comment": str,
    "date_updated": str,
    "lesson_name": str,
}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

DEBUG_DICT = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

LOGGING_FORMAT = '%(asctime)s  %(levelname)s: %(message)s'

last_error: str = ''


def handler_init(handler_type: Type[logging.Handler],
                 level: int, format: str, *args, **kwargs) -> logging.Handler:
    """Инициализация хендлера логирования."""
    handler = handler_type(*args, **kwargs)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format))
    return handler


bot_logger = logging.getLogger()
handler_console = handler_init(
    logging.StreamHandler,
    DEBUG_DICT[DEBUG_LEVEL],
    LOGGING_FORMAT,
    stream=sys.stdout
)
bot_logger.addHandler(handler_console)


class TelegramBotHandler(logging.Handler):
    """Хэндлер для отправки логов в телеграмм."""

    def __init__(self, bot: telegram.Bot):
        """Добавилась переменная bot."""
        super().__init__()
        self.bot = bot

    def emit(self, record: logging.LogRecord):
        """
        Собственно отправка сообщения в телеграмм.
        Если уровень логгирования ERROR или выше и
        при этом последняя ошибка не совпадает с текущей.
        """
        global last_error
        if last_error != record.message:
            send_message(self.bot, self.format(record))
        last_error = record.message


def send_message(bot: telegram.Bot, message: str) -> None:
    """Функция отправки сообщений в телеграмм."""
    global bot_logger
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        bot_logger.error(f'Ошибка "{error}" при попытке отправки сообщения')
    else:
        bot_logger.info(f"Сообщение '{message}' отправлено")


def get_api_answer(current_timestamp: int) -> Union[List[dict], dict]:
    """Функция получения ответа от яндекс API."""
    global bot_logger
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    try:
        answer = requests.get(ENDPOINT, headers=headers, params=params)
    except Exception as error:
        bot_logger.error(f'Ошибка "{error}" при попытке подключения к яндексу')
    else:
        if answer.status_code != 200:
            raise InaccessibilityEndpointException(
                f'Яндекс вернул код {answer.status_code}, отличный от 200'
            )
        return answer.json()


def check_response(response: Union[List[dict], dict]
                   ) -> List[Dict[str, Union[str, int]]]:
    """Функция проверки полученного ответа на корректность."""
    global bot_logger
    if isinstance(response, list):
        response = response[0]
    if response == {} or response is None:
        raise EmptyAnswerException(
            'Яндекс вернул пустой ответ'
        )
    if 'homeworks' in response:
        homeworks = response.get('homeworks')
        if not isinstance(homeworks, list):
            raise WrongAnswerException(
                'Тип homeworks отличен от списка'
            )
        for work in homeworks:
            for key in work:
                if key not in HOMEWORK_SCHEME:
                    bot_logger.error(f'Ключ "{key}" не соответствует схеме')
                elif not isinstance(work[key], HOMEWORK_SCHEME[key]):
                    bot_logger.error(
                        f'Тип ключа "{key}" не соответствует схеме')
        return homeworks
    raise KeyError(
        'Отсутствует ключ homeworks'
    )


def parse_status(homework: Dict[str, Union[str, int]]) -> str:
    """Функция получает строку для отправки в телеграмм на базе ответа."""
    global bot_logger
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        bot_logger.error(
            f'Недокументированный статус работы: "{homework_status}"')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Функция проверки того, что токены непустые."""
    global bot_logger
    tokens = all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))
    if not tokens:
        bot_logger.critical(
            "Не заданы переменные окружения (токены/telegram_id)")
    return tokens


def main() -> None:
    """Основная логика работы бота."""
    global bot_logger
    if not check_tokens():
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    handler_telegramm = handler_init(
        TelegramBotHandler,
        logging.ERROR,
        LOGGING_FORMAT,
        bot=bot
    )
    bot_logger.addHandler(handler_telegramm)
    current_timestamp = int(time.time())
    old_statuses = {}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks != []:
                statuses = {}
                for work in homeworks:
                    statuses[work['id']] = work['status']
                    if (work['id'] in old_statuses
                            and old_statuses[work['id']] == work['status']):
                        logging.debug(
                            f"Статус сообщения {work[id]} не изменился")
                    else:
                        message = parse_status(work)
                        send_message(bot, message)
                old_statuses = statuses
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
