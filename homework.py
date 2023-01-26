import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import find_dotenv, load_dotenv

import exceptions

load_dotenv(find_dotenv())

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка на наличие необходимых токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Функция для отправки сообщений в Telegram."""
    try:
        logging.debug(f'Начинаю отправку сообщения: "{message:10}"')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as e:
        logging.error(
            f'Ошибка отправки сообщения: "{message:10}". Ошибка: {e}'
        )
    else:
        logging.debug(f'Успешно отправлено сообщение: "{message:10}"')


def get_api_answer(current_timestamp):
    """Обращаемся по API к ЯП, чтобы получить данные о домашней работе."""
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Ошибка! Код ответа сервера: {response.status_code}'
            )
            raise exceptions.HTTPStatusCodeError(
                f'Ошибка код: {response.status_cod}'
            )
        return response.json()

    except requests.exceptions.RequestException as e:
        raise exceptions.NoConnectionError(
            f'Ошибка при получении данных: {e}'
        )


def check_response(response):
    """Проверка API ответа на корректность данных."""
    logging.debug("Начинаю проверку данных ответа")
    if not isinstance(response, dict):
        logging.error('Ответ не содержит словаря!')
        raise TypeError('Ответ не содержит словаря!')
    api_response = response.get('homeworks')
    if api_response is None:
        logging.error('В ответе нет ключа "homeworks')
        raise KeyError('В ответе нет ключа "homeworks"')
    if not isinstance(api_response, list):
        logging.error('Ответ не содержит в себе листа!')
        raise TypeError('Ответ не содержит в себе листа!')
    logging.debug("Данные прошли проверку")
    return api_response


def parse_status(homework):
    """Парсинг ответа от сервера ЯП."""
    if 'status' not in homework:
        raise KeyError('Ключ "status" отсутствует в ответе!')
    if 'homework_name' not in homework:
        raise KeyError('Ключ "homework_name" отсутствует в ответе!')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError('Статус задания неизвестен, либо отсутвует')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS.get(homework['status'])
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Бот начал процедуру запуска!')
    if not check_tokens():
        logging.critical('Крит. ошибка, отсутствует токен!')
        raise SystemExit('Отсутствуют токены, работа невозможна!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    status_flag = ''
    while True:
        current_timestamp = int(time.time())
        try:
            response = get_api_answer(current_timestamp)
            if not check_response(response):
                send_message(
                    bot, 'Проверка завершена, статус работы не изменился!'
                )
                logging.debug(
                    'Проверка завершена, статус работы не изменился!'
                )
                continue
            homeworks = response.get('homeworks')[0]
            msg = parse_status(homeworks)
            if status_flag != msg:
                send_message(bot, msg)
                status_flag = msg

        except Exception as e:
            error_msg = f'Сбой в работе программы: {e}'
            send_message(bot, error_msg)

        finally:
            time.sleep(RETRY_PERIOD)
    else:
        raise SystemExit("I'll be back!")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='YP_bot_telegram.log',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    main()
