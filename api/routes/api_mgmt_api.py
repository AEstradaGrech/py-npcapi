from typing import Any
from fastapi import APIRouter
from api.infrastructure.llm.ollama_provider import Ollama_Provider

router = APIRouter(prefix="/mgmt/api-settings")

@router.get(
    "/available-models",
    summary="Retrieves all available models to set",
    responses={
        200: {"description": "Returns an array with all the available models you can set"}
    }
)  
async def get_available_models() -> []:
    return Ollama_Provider().available_models()
    
@router.get(
    "/summary",
    summary="Returns a summary of the current settings and the available provider/models",
    responses={
        200: {"description": "Successful response with an object containing a settings summary"}
    }
)
async def setting_summary() -> Any:
    return Ollama_Provider().settings_summary()
