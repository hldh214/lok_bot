class ApiException(Exception):
    pass


class NoAuthException(ApiException):
    pass


class NeedCaptchaException(ApiException):
    pass


class DuplicatedException(ApiException):
    pass


class ExceedLimitPacketException(ApiException):
    pass


class OtherException(ApiException):
    pass
