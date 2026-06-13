from typing import Any

from loguru import logger

from api.infrastructure.models.char_db_schemas import CharacterMoodDoc, CharacterPersonalityDoc, CharacterRoleDoc, CharacterTraitDoc
from api.infrastructure.repositories.mongo.chat_prompts import GameCharDoc
from api.models.character_schemas import CharacterTraitDto, PraiseCharacterDto, CharacterMoodDto, CharacterPersonalityDto, CharacterRoleDto

def toRoleDto(record:Any) -> CharacterRoleDto:
    doc = CharacterRoleDoc.model_validate(record)
    return CharacterRoleDto(id=doc.id, name=doc.name, gameClassId=doc.game_class_id, description=doc.description, systemMessage=doc.sys_msg_text, outputActions=doc.output_actions)
def toPersonalityDto(record:Any) -> CharacterPersonalityDto:
    doc = CharacterPersonalityDoc.model_validate(record)
    return CharacterPersonalityDto(id=doc.id, name=doc.name, systemMessage=doc.sys_msg_text, exclusions=doc.exclusions)
def toTraitDto(record:Any) -> CharacterTraitDto:
    doc = CharacterTraitDoc.model_validate(record)
    return CharacterTraitDto(id=doc.id, name=doc.name, description=doc.description, systemMessage=doc.sys_msg_text, exclusions=doc.exclusions)
def toMoodDto(record:Any) -> CharacterMoodDto:
    doc = CharacterMoodDoc.model_validate(record)
    return CharacterMoodDto(id=doc.id, name=doc.name, systemMessage=doc.sys_msg_text)
def gameCharToDto(record: Any) -> PraiseCharacterDto:
    doc = GameCharDoc.model_validate(record)
    logger.info(f"--GAME CHAR TO DTO-")
    return PraiseCharacterDto(
        id=str(doc.id),
        name=doc.name,
        age=doc.age,
        role=doc.role,
        faction=doc.faction,
        traits=doc.traits,
        personalities=doc.personalities,
        backgroundStory=doc.background_story,
        motivations=doc.motivations,
        typicalRoutines=doc.typical_routines,
        goal=doc.goal
    )