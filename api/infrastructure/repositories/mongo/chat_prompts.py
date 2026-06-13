from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from api.infrastructure.repositories.mongo.base_repo import MongoRepository, PyObjectId
from api.infrastructure.models.db_schemas import ChatDetailsDoc, ChatDocDto, ChatPromptDoc, SessionDoc

class ChatPromptsRepository(MongoRepository[ChatPromptDoc]):
    def __init__(self, db_name:str, col_name:str = "ChatPrompts"):
        super().__init__(db_name=db_name, col_name=col_name)
        
    async def find_by_session_id(self, session_id: str) -> List[ChatPromptDoc]:
        return [ChatPromptDoc.model_validate(doc) for doc in self.collection.find({"sessionId": session_id})]
    
class ChatSessionsRepository(MongoRepository[SessionDoc]):
    def __init__(self, db_name:str, col_name:str = "ChatSessions"):
        super().__init__(db_name=db_name, col_name=col_name)
    async def get_user_sessions_containing_tag(self, username:str, tag:str) -> List[SessionDoc]:
        return [doc for doc in self.collection.find({"$and":[{"username": username},{"tag": {'$regex': tag}}]})]
    
class ChatDetailsRepository(MongoRepository[ChatDetailsDoc]):
    def __init__(self, db_name:str, col_name:str = "ChatDetails"):
        super().__init__(db_name=db_name, col_name=col_name)


class GameCharDoc(BaseModel):
    id:Optional[PyObjectId] = Field(description="Db identifier for a user chat session", alias="_id", default_factory=ObjectId)
    name:str = Field(description="Character name.Optionally with nickname")
    age: str = Field(description="Age of the character in numeric format or an approximation (example: 'mid-thirties' or 'around forty years')")
    faction: str = Field(description="Game faction the character belongs to")
    role:str = Field(description="Character's game role or profession")
    traits: List[str] = Field(description="Character personality traits or facets for this character")
    personalities: List[str] = Field(description="Psychological traits defining the character's emotional profile")
    background_story: str = Field(description="Historical context and origin story (100-200 words). Include key life events that shaped the character.")
    typical_routines: str = Field(description="Day-to-day activities and habits  Includes professional duties, personal habits, social interactions, and pastimes.")
    motivations: str = Field(description="Core driving forces and desires. Includes ideological (beliefs), professional (career goals), personal (relationships), and psychological (internal needs) motivations.")
    goal: Optional[str] = Field(description="Current character goal in life (if any). It might generate (or help to generate) a game QUEST event depending on it's relationship with the player")

