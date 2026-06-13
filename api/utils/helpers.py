import base64
import io
from typing import Any, List
from PIL import Image
from fastapi import HTTPException, Request
from loguru import logger
import pandas as pd
from api.infrastructure.models.db_schemas import ChatDetailsDoc
from api.models.prompting_schemas import ChatMessageDto, SessionHistoryUpdateRequest, UnrealChatUpdateRequest
from api.utils.statics import max_ctx_len, default_db_name, praise_db_name

class HTTPLoggedException(HTTPException):
    def __init__(self,status_code:int, detail:str):
        logger.error(f"-- APP EXCEPTION >> {status_code} >> {detail}")
        super().__init__(status_code=status_code, detail=detail)

def pil_to_base64(image, format:str='png') -> str:
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue())

def base64_to_pil(img_base64):
    base64_decoded = base64.b64decode(img_base64)
    byte_stream = io.BytesIO(base64_decoded)
    pil_image = Image.open(byte_stream)
    return pil_image

def chat_history_to_standard_kvp(chat_history:List[dict[str,str]]) -> List[dict[str,str]]:
    results = []
    for kvp in chat_history:
        key = list(kvp.keys())[0]
        results.append({"role": key , "content": kvp.get(key)})
    return results

def dataset_to_json(dataset) -> [Any]:
    results=[]
    for i in range(0, len(dataset)):
        dto ={}
        for key in dataset[i].keys():
            dto[f'{key}'] = dataset[i][key]
        results.append(dto)
    return results

def dataset_row_to_json(row) -> Any:
    dto = {}
    for key in row.keys():
        dto[key]=row[key]
    return ""

def join_strings(strings: List[str], separator:str=",", prefix:str="", substring:int=-1) -> str:
    result = ""
    for string in strings:
        result += f"{prefix}{string}{separator}"
    return result

def get_history_messages_by_key(key:str, chat_history: List[dict[str, str]], only_last_one: bool = False) -> List[str]:
        df = pd.DataFrame(chat_history)
        print("DATA FRAME", df)
        try:
            if only_last_one:
                return [df[key][df[key].notna()].tolist()[-1]]
            else: 
                return df[key][df[key].notna()].tolist()
        except:
            return []
    
def update_memo_cache_value(details:ChatDetailsDoc, key:str, value:str, isAppend=True):
    memo = "" if details.botMemory.get(key) is None else details.botMemory.get(key)
    memo = memo + value if isAppend else value
    details.botMemory[key] = memo

def update_memo_cache(details:ChatDetailsDoc, values: List[dict[str,str]]):
    for kvp in values:
        key = kvp.keys()[0]
        update_memo_cache_value(details=details, key=key, value=kvp[key], isAppend=True)

def filter_array_by_key(key:str, values:List[str]) -> List[str]:
    results = []
    for value in values:
        print("--  ARRAY VALUE --", value)
        if key in value:
            results.append(value)
    return results

def filter_objects_by_kvp(key:str, value:Any, objects: List[Any]) -> List[Any]:
    results:List[Any] = []
    for item in objects:
        itemvars = vars(item)
        if itemvars[key] == value:
            results.append(item)
    return results

def streamEndReqToUnreal(req: SessionHistoryUpdateRequest) -> UnrealChatUpdateRequest:
    chats: List[ChatMessageDto]=[]
    for kvp in req.chatHistory:
        k = kvp.keys()[0]
        chats.append(ChatMessageDto(role=k, message=kvp[k]))
    return UnrealChatUpdateRequest(sessionId=req.sessionId, chatHistory=chats)

def chat_history_to_unreal(history: List[dict[str,str]]) -> List[ChatMessageDto]:
    messages: List[ChatMessageDto] = []
    if len(history) == 0:
        return messages
    for kvp in history:
        k = list(kvp.keys())[0]
        messages.append(ChatMessageDto(role=k, message=kvp[k]))
    return messages

def unreal_messages_to_history(messages: List[ChatMessageDto]) -> List[dict[str,str]]:
    history:List[dict[str,str]] = []
    for message in messages:
        history.append({f"{message.role}": f"{message.message}"})
    return history

def get_ctx_num_for_text(text:str, offset: int = 100) -> int:
    return len(text) + offset if len(text) + offset <= max_ctx_len else max_ctx_len

def replace_values(text:str, kvp:dict[str,str], tag_separators:List[str] = ["",""]) -> str:
    for key in kvp.keys():
        text = text.replace(f"{tag_separators[0]}{key}{tag_separators[1]}", kvp[key])
    return text

def get_request_db_name(request:Request) -> str:
    client_header = request.headers.get("app-username")
    return praise_db_name if client_header is not None and "PRAISE" in client_header.upper() else default_db_name 
