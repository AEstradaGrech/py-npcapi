from bson import ObjectId
from loguru import logger

from api.infrastructure.models.db_schemas import ChatPromptDoc, SessionDoc
from api.infrastructure.repositories.mongo.chat_prompts import GameCharDoc
from api.mappers.character_mappers import gameCharToDto
from api.models.character_schemas import PraiseCharacterDto
from api.models.prompting_schemas import BotInfoDto, ChatDocDto, ChatInitDto, ConversationDto, GenerateCharacterRequest, SessionDto


def chatDocToDto(doc: ChatPromptDoc) -> ChatDocDto:
    doc = ChatPromptDoc.model_validate(doc)
    return ChatDocDto(
        id=str(doc.id),
        sessionId=doc.session_id,
        model=doc.model,
        maxTokens=doc.max_tokens,
        temperature=doc.temperature,
        username=doc.user_name,
        creationDate=doc.creation_date,
        messages=doc.messages_to_chat_history()
    )

def sessionDocToDto(doc: SessionDoc) -> SessionDto:
    doc = SessionDoc.model_validate(doc)
    return SessionDto(
        id=str(doc.id),
        username=doc.username,
        tag=doc.tag,
        summary=doc.current_chat_summary,
        currentChatId=doc.current_chat_id,
        currentChatOngoing=doc.current_chat_ongoing,
        characterId=doc.character_id
    )

def sessionDocToChatInitDto(doc: SessionDoc, npc: GameCharDoc, conversation: ConversationDto, sysmsg: str) -> ChatInitDto:
    doc = SessionDoc.model_validate(doc)
    logger.info(f"--DOC--")
    char_dto = gameCharToDto(npc)
    logger.info(f"--CHAR--")
    dto = ChatInitDto(
        id=str(doc.id),
        username=doc.username,
        tag=doc.tag,
        summary=doc.current_chat_summary,
        characterId=str(doc.character_id),
        currentChatId=doc.current_chat_id,
        currentChatOngoing=doc.current_chat_ongoing,
        npc=char_dto,
        conversation=conversation,
        sysmsg=sysmsg
    )
    return dto

def botInfoToGenRequest(dto: BotInfoDto) -> GenerateCharacterRequest:
    return GenerateCharacterRequest(
        charName=dto.charName,
        charAge=dto.charAge,
        charRole=dto.charRole,
        factionName=dto.factionName,
        personalities=dto.personalities,
        traits=dto.traits,
        actualContext=dto.actualContext)

def charDtoToDoc(dto: PraiseCharacterDto) -> GameCharDoc:
    return GameCharDoc(
        id=ObjectId(dto) if dto.id is not None and dto.id != "" else ObjectId(),
        name=dto.name,
        age=dto.age,
        role=dto.role,
        faction=dto.faction,
        personalities=dto.personalities,
        traits=dto.traits,
        motivations=dto.motivations,
        background_story=dto.backgroundStory,
        typical_routines=dto.typicalRoutines,
        goal=dto.goal
    )