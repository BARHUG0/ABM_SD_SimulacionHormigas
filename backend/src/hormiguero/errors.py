from typing import Any


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def not_found(resource: str, resource_id: str | int) -> ApiError:
    return ApiError(404, f"{resource}_not_found", f"Recurso '{resource}' con id '{resource_id}' no encontrado")


def conflict(code: str, message: str, details: Any = None) -> ApiError:
    return ApiError(409, code, message, details)


def unprocessable(code: str, message: str, details: Any = None) -> ApiError:
    return ApiError(422, code, message, details)
