from api.infrastructure.models.db_schemas import ChatSummaryDoc
from api.infrastructure.repositories.mongo.base_repo import MongoRepository


class ChatSummariesRepository(MongoRepository[ChatSummaryDoc]):
    
    def __init__(self, db_name:str, col_name:str = "ChatSummaries"):
        super().__init__(db_name=db_name, col_name=col_name)

    async def get_chat_summary(self, chat_id:str) -> ChatSummaryDoc:
        docs =[ doc for doc in self.collection.aggregate([
            {"$match" : {"chat_collection_id": {'$regex': chat_id}}},
            {"$sort" : {"creation_date": -1}}
        ])]
        return None if len(docs) <= 0 else ChatSummaryDoc.model_validate(docs[0])