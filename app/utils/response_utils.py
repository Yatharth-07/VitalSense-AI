from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    message: str = "Operation completed successfully",
    status_code: int = 200
) -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(
    message: str,
    status_code: int = 400,
    errors: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    content = {
        "success": False,
        "message": message,
        "errors": errors or {}
    }
    return JSONResponse(status_code=status_code, content=content)
