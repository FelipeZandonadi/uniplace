from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class ApiError(APIException):
    def __init__(self, status_code, detail, code):
        self.status_code = status_code
        super().__init__(detail, code)


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and "detail" in response.data:
        response.data.setdefault("code", getattr(response.data["detail"], "code", "error"))
    return response
