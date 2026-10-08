from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic.json_schema import models_json_schema

from hormiguero.schemas.messages import ClientMessage, ServerMessage

REF_TEMPLATE = "#/components/schemas/{model}"


def build_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    _, message_schemas = models_json_schema(
        [(ServerMessage, "serialization"), (ClientMessage, "validation")], ref_template=REF_TEMPLATE
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for name, definition in message_schemas.get("$defs", {}).items():
        components.setdefault(name, definition)
    app.openapi_schema = schema
    return schema
