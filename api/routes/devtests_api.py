from typing import Any, List, Optional

from pydantic import BaseModel

from api.models.schemas import SpacyNER
from api.services.mood_analysis_service import MoodAnalysisService
from fastapi import APIRouter

router = APIRouter(prefix="/dev-tests")

class TestVaderDto(BaseModel):
    user_prompt:str
    prev_llm:Optional[str] = None
    ctx_upd:Optional[str] = None

@router.post(
    "/test-vader",
    summary="Simulates the on-stream-end update request and analyzes the sentiment with NLTK.Vader",
    responses={
        200 : {"description": "Succesful response with the polarity_scores() result"}
    }
)
async def analyze_test_req(req:TestVaderDto) -> Any:
    service = MoodAnalysisService()
    return service.vader_analyze_current_prompt_sentiment(user_prompt=req.user_prompt,prev_llm_res=req.prev_llm, context_update=req.ctx_upd)

@router.post(
    "/spacy/ner",
    summary="Named Entity Recognition using python's spaCy package",
    responses={
        200 : {"description": "Succesful response with the polarity_scores() result"}
    }
)
async def extract_named_entities(req:TestVaderDto) -> List[SpacyNER]:
    service = MoodAnalysisService()
    return service.spacy_ner(user_prompt=req.user_prompt)

class TestMoodHandler(BaseModel):
    current_mood:str
    personalities: list[str]
    sentiment: Optional[str] = None

@router.post(
    "/test-mood-handler",
    summary="Simulates the Bot Mood Transition system",
    responses={
        200 : {"description": "Succesful response with the polarity_scores() result"}
    }
)
async def analyze_test_req(req:TestMoodHandler) -> Any:
    service = MoodAnalysisService()
    if(req.sentiment is not None):
        return service.handle_chat_mood_transition(current_bot_mood=req.current_mood, bot_personalities=req.personalities, chat_sentiment=req.sentiment)
    return service.handle_personality_mood_transition(current_bot_mood=req.current_mood, bot_personalities=req.personalities)
