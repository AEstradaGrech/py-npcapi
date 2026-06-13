
from api.infrastructure.repositories.mongo.base_repo import MongoRepository

class DatasetChatsRepository(MongoRepository):
    def __init__(self, db_name:str, col_name:str = "DatasetChats"):
        super().__init__(db_name=db_name, col_name=col_name)

    