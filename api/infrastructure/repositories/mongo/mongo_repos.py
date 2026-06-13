from api.infrastructure.models.char_db_schemas import CharacterMoodDoc, CharacterPersonalityDoc, CharacterRoleDoc, CharacterTraitDoc
from api.infrastructure.repositories.mongo.base_repo import MongoRepository
from api.infrastructure.repositories.mongo.chat_prompts import GameCharDoc


class CharacterRolesRepository(MongoRepository[CharacterRoleDoc]):
    def __init__(self, db_name:str, col_name:str = "CharacterRoles"):
        super().__init__(db_name=db_name, col_name=col_name)
class CharacterPersonalitiesRepository(MongoRepository[CharacterPersonalityDoc]):
    def __init__(self, db_name:str, col_name:str = "CharacterPersonalities"):
        super().__init__(db_name=db_name, col_name=col_name)
class CharacterTraitsRepository(MongoRepository[CharacterTraitDoc]):
    def __init__(self, db_name:str, col_name:str = "CharacterTraits"):
        super().__init__(db_name=db_name, col_name=col_name)
class CharacterMoodsRepository(MongoRepository[CharacterMoodDoc]):
    def __init__(self, db_name:str, col_name:str = "CharacterMoods"):
        super().__init__(db_name=db_name, col_name=col_name)
class GameCharsRepository(MongoRepository[GameCharDoc]):
    def __init__(self, db_name:str, col_name:str = "GameCharacters"):
        super().__init__(db_name=db_name, col_name=col_name)