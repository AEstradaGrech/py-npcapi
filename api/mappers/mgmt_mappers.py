
from typing import Any

from api.infrastructure.models.db_schemas import SystemMessageDoc
from api.models.schemas import SystemMessageDto


def toSystemMessageDto(record:Any) -> SystemMessageDto:
    print("VALIDATING SYS MSG", record)
    doc = SystemMessageDoc.model_validate(record)
    return SystemMessageDto(id=str(doc.id), type=doc.type, description=doc.description, message=doc.message, tag=doc.tag)