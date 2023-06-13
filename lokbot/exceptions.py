class ApiException(Exception):
    pass


class RetryableApiException(ApiException):
    pass


class FatalApiException(ApiException):
    pass


class NoAuthException(FatalApiException):
    pass


class NeedCaptchaException(FatalApiException):
    pass


class NotOnlineException(FatalApiException):
    pass


class OtherException(FatalApiException):
    pass


class DuplicatedException(RetryableApiException):
    pass


class ExceedLimitPacketException(RetryableApiException):
    pass
