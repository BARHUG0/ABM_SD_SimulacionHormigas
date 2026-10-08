from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from hormiguero.errors import ApiError
from hormiguero.schemas.common import ErrorBody, ErrorResponse

ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Recurso no encontrado"},
    409: {"model": ErrorResponse, "description": "Conflicto con el estado actual"},
    422: {"model": ErrorResponse, "description": "Solicitud inválida"},
}


def error_response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=jsonable_encoder(details)))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
        return error_response(error.status_code, error.code, error.message, error.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(422, "validation_error", "La solicitud no cumple el esquema", error.errors())

    @app.exception_handler(HTTPException)
    async def handle_http_error(_: Request, error: HTTPException) -> JSONResponse:
        return error_response(error.status_code, "http_error", str(error.detail))
