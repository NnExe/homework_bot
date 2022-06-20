class InaccessibilityEndpointException(Exception):
    """Недоступен endpoint яндекса."""

    pass


class EmptyAnswerException(Exception):
    """Ответ яндекса вернул пустой json."""

    pass


class WrongAnswerException(Exception):
    """Ответ яндекса вернул некооректный json."""

    pass


class NoTokensException(Exception):
    """Отсутствуют один или несколько токенов."""

    pass
