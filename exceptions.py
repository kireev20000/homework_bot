class HTTPStatusCodeError(Exception):
    """Ответ от сервера не ОК, !=200"""
    pass

class NoConnectionError(Exception):
    """Ошибка связи с сервером"""
    pass