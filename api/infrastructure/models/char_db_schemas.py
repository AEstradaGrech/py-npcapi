from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from api.infrastructure.repositories.mongo.base_repo import PyObjectId


class CharacterRoleDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    game_class_id:int = Field(description="Unreal Engine Game Class. It is used to filter by the bot role")
    name:str = Field(description="Display name for the role / game class")
    description: str = Field(description="A more descriptive definition of the role")
    sys_msg_text: str = Field(description="Text to pass to the llm as part of the sys_msg")
    output_actions: List[str] = Field(description="Available OutputActions for this role")

class CharacterMoodDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    name:str = Field(description="Display name for the role / game class")
    sys_msg_text: str = Field(description="Text to pass to the llm as part of the sys_msg")

class CharacterPersonalityDoc(CharacterMoodDoc):
    exclusions: List[str] = Field(description="Array of personalities that are mutually exclusive")

class CharacterTraitDoc(CharacterPersonalityDoc):
    description: str = Field(description="A more descriptive definition of the Trait")
