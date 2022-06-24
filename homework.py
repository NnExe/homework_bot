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

LAST_ERROR = ''


class TelegramBotHandler(logging.Handler):
    """Хэндлер для отправки логов в телеграмм."""

    def __init__(self, bot):
        """Добавилась переменная bot."""
        super().__init__()
        self.bot = bot

    def emit(self, record: logging.LogRecord):
        """
        Собственно отправка сообщения в телеграмм.
        Если уровеньлоггирования ERROR или выше и
        при этом последняя ошибка не ошибка подключения, или это 1
        по счету ошибка подключения.
        """
        global LAST_ERROR
        if (record.levelno >= logging.ERROR
           and LAST_ERROR != record.message):
            send_message(self.bot, self.format(record))
        LAST_ERROR = record.message


def send_message(bot, message):
    """Функция отправки сообщений в телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Ошибка "{error}" при попытке отправки сообщения')
    else:
        logging.info(f"Сообщение '{message}' отправлено")


def get_api_answer(current_timestamp):
    """Функция получения ответа от яндекс API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    try:
        answer = requests.get(ENDPOINT, headers=headers, params=params)
    except Exception as error:
        logging.error(f'Ошибка "{error}" при попытке подключения к яндексу')
    else:
        if answer.status_code != 200:
            raise InaccessibilityEndpointException(
                f'Яндекс вернул код {answer.status_code}, отличный от 200'
            )
        return answer.json()


def check_response(response):
    """Функция проверки полученного ответа на корректность."""
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
                    logging.error(f'Ключ "{key}" не соответствует схеме')
                elif not isinstance(work[key], HOMEWORK_SCHEME[key]):
                    logging.error(
                        f'Тип ключа "{key}" не соответствует схеме')
        return homeworks
    raise KeyError(
        'Отсутствует ключ homeworks'
    )


def parse_status(homework):
    """Функция получает строку для отправки в телеграмм на базе ответа."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(
            f'Недокументированный статус работы: "{homework_status}"')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверки того, что токены непустые."""
    tokens = all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))
    if not tokens:
        logging.critical(
            "Не заданы переменные окружения (токены/telegram_id")
    return tokens


def main():
    """Основная логика работы бота."""
    bot_logger = logging.getLogger()
    bot_logger.setLevel(DEBUG_DICT[DEBUG_LEVEL])
    handler_console = logging.StreamHandler(stream=sys.stdout)
    handler_console.setFormatter(
        logging.Formatter('%(asctime)s, %(levelname)s, %(message)s'))
    bot_logger.addHandler(handler_console)
    if not check_tokens():
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    handler_telegramm = TelegramBotHandler(bot)
    handler_telegramm.setFormatter(
        logging.Formatter('%(asctime)s, %(levelname)s, %(message)s'))
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
