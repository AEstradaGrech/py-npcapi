from typing import List

from api.infrastructure.models.db_schemas import SystemMessageDoc
from api.infrastructure.repositories.mongo.base_repo import T, MongoRepository


class SysMessagesRepository(MongoRepository[SystemMessageDoc]):
    
    def __init__(self, db_name:str, col_name:str = "SystemMessages"):
        super().__init__(db_name=db_name, col_name=col_name)

    async def get_by_type_and_tag(self, type:int, tag:str) ->T:
        entity = self.collection.find_one({"$and": [{"type": type},{"tag": tag }]})
        return None if entity is None else entity
    
    async def get_many_by_type_containing_tag(self, type:int, tag:str) -> List[SystemMessageDoc]:
        return [doc for doc in self.collection.find({"$and":[{"type": type},{"tag": {'$regex': tag}}]})]