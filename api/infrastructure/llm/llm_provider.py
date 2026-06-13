from abc import ABC, abstractmethod
from typing import Any, List

from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger

from api.infrastructure.llm.llm_config import LLM_Config
from api.infrastructure.models.reasoning_schemas import ChatMoodAnalysis
from api.models.prompting_schemas import ChatPromptRequest

from api.utils.helpers import get_history_messages_by_key
from api.utils.statics import chat_summary_template_tag, summary_role_tags
    
class LLM_Provider(ABC):
    did_init = False
    display_name = "unset"
    _use_chat_template:bool = True
    _model_name:str = None
    _available_models = []
    _config: LLM_Config = LLM_Config()
    _model_prompt_templates = {
        "default": {
            "system" : "### System:",
            "user" : "### Human:",
            "assistant" : "### Assistant:"
        },  
        "praise": {
            "system" : "### System:",
            "user" : "### <<USERNAME>>:",
            "assistant" : "### <<BOTNAME>>:"
        },  
        "game": {
            "system" : "### System:",
            "user" : "### PLAYER:",
            "assistant" : "### NON-PLAYER:"
        },  
        "llama":{
            "system" : "<|im_start|>system\n-[[content]]-\n<|im_end|>",
            "user" : "<|im_start|>user\n-[[content]]-<|im_end|>",
            "assistant" : "<|im_start|>assistant\n-[[content]]-<|im_end|>"
        }
    } 
    _model_stopping_tokens = {
        "default" : ["User:", "### Human:", "### User:", "### System:"]
    }

    def __init__(self):
        self._model = None
        self._model_name = None
        self.did_init = False
        self._available_models = []

    #expects a dto with a setted up chat_history PODRIA AÑADIR EL SETUP EN BASE_MTHD Y NO HACERLO ABSTRACTO
    @abstractmethod
    def chat_request(self, request: ChatPromptRequest, excluded_events: List[str] = [], guidance_token: str = '') -> str:
        pass
    
    @abstractmethod
    def direct_prompt(self, prompt, temperature:float = 0.7, max_tokens: int = 600, ctx_len:int = 2048) -> str:
        pass

    @abstractmethod
    def fresh_model_instance(self, model:str = None, temperature:float = 0.7, max_tokens: int = 600, ctx_len:int = 2048) -> Any:
        pass
    
    def settings_summary(self) -> Any:
        settings = {
            "initialized":self.did_init,
            "current_model": self._model_name,
            "current_provider": self.display_name,
            "available_models": self.available_models(),
            "current_config":{}
        }
        if self.did_init:
            print(self._integration)
            settings["current_config"] = self.config_as_dict()
        return settings
    
    def model_config(self) -> LLM_Config:
        return self.config()

    def current_model(self) -> str:
        return self._model_name
    
    def available_models(self) -> list:
        return self._available_models
        
    def add_available_model(self, model_name):
        if model_name not in self._available_models:
            self._available_models.append(model_name)

    def get_prompt_template(self, model="default"):
        if model not in list(self._model_prompt_templates.keys()):
            model = "default"
        return self._model_prompt_templates.get(model)
    
    def get_model_stopping_tokens(self, model:str = "default"):
        if model not in list(self._model_stopping_tokens.keys()):
            model = "default"
        return self._model_stopping_tokens.get(model)
    
    def append_default_sys_message(self,chat_history: List[dict[str, str]]) -> List[dict[str, str]]:
        results = [{"system" : "You are a helpful assistant"}]
        for turn in chat_history:
            results.append(turn)
        return results
    
    def setup_chat_request(self, prompt_request: ChatPromptRequest) -> ChatPromptRequest:
        if prompt_request.system_message == "":
            prompt_request.system_message = None
        if len(prompt_request.chat_history) == 0:
            if prompt_request.system_message is None:
                prompt_request.chat_history = self.append_default_sys_message(chat_history=prompt_request.chat_history)
            else:
                prompt_request.chat_history.append({"system" : prompt_request.system_message})
                print(prompt_request)
        else:
            last_sys_msg = get_history_messages_by_key(key="system", chat_history=prompt_request.chat_history, only_last_one=True)
            if len(last_sys_msg) == 0:
                if prompt_request.system_message is None:
                    prompt_request.chat_history = self.append_default_sys_message(chat_history=prompt_request.chat_history)
                else:
                    chats = [{"system" : prompt_request.system_message}]
                    for chat in prompt_request.chat_history:
                        chats.append(chat)
                    prompt_request.chat_history = chats
            else:
                if prompt_request.system_message is not None and prompt_request.system_message != last_sys_msg[0]:
                    prompt_request.chat_history.append({"system" : prompt_request.system_message})
        prompt_request.chat_history.append({"user": prompt_request.message})
        return prompt_request
    
    def replace_final_prompt_keys(self, prompt:str, new_keys:dict[str,str]) -> str:
        new_prompt = prompt
        for key in new_keys.keys():
            new_prompt = new_prompt.replace(key, new_keys[key])
        return new_prompt

    def chat_history_to_template(self, chat_history: List[dict[str,str]], exclude_sys_message:bool=False, exlude_sys_updates:bool=False, assistant_guidance_token:str = '', template_key = "default") -> str:
        prompt = ""
        if template_key != "default":
            if template_key not in self._model_prompt_templates.keys():
                template_key = "default"
        else:
            if self._model_name in list(self._model_prompt_templates.keys()):
                template_key = self._model_name
            if self._model_name not in list(self._model_prompt_templates.keys()):
                template_key = "default"
        for kvp in chat_history:
            message_key = list(kvp.keys())[0]
            if kvp[message_key] == '':
                continue
            match message_key:
                case "system":
                    if exclude_sys_message == False:                       
                        prompt += (self._model_prompt_templates[template_key][message_key] + "\n" + (kvp[message_key] + "\n"))
                case "context":
                    if exlude_sys_updates == False:
                        #TODO [ctx-update-env] <- actualizacion sobre entorno conversacion, (en principio no son relevantes para otros chats. no persisten)
                        #     [ctx-update-action] <- actualizacion cosas que HACEN (objetos que muestra, tiran, guardan) <- diferenciar acciones que persisten (obtiene objeto, porta X VS personaje recibe guantazo)
                        #     [ctx-update-mood] <- actualizacion ESTADO personajes (se añade a proximos sys_prompts o al actual)
                         #TODO: marcar estos eventos + instruccion en sys_msg (task?chat_rule?). #TODO-v2:Entrenar modelo para reconocerlos / generarlos
                        prompt += (self._model_prompt_templates[template_key]["system"] + "\n" + (kvp[message_key] + "\n"))
                case "user":
                    prompt += (self._model_prompt_templates[template_key][message_key] + "\n" + (kvp[message_key] + "\n"))
                case "assistant":
                    prompt += (self._model_prompt_templates[template_key][message_key] + "\n" + (kvp[message_key] + "\n"))
        if assistant_guidance_token != '':
            prompt += assistant_guidance_token
            logger.info("-- adding guidance token :" + assistant_guidance_token)
        return prompt
    
    def config_as_dict(self) -> Any:
        return self._config.to_dict()
    
    def config(self) -> LLM_Config:
        return self._config
    
    def chat_summary(self, chat_history: List[dict[str,str]], sys_msg:str, temperature:float = 0.5, max_tokens:int = 800, ctx_len:int = 4096,exclude_sys_msg:bool = True, exclude_sys_updates:bool = True) -> (str, str):
        prompt = self.chat_history_to_template(chat_history=chat_history, exclude_sys_message=exclude_sys_msg, exclude_sys_updates=exclude_sys_updates) 
        model_prompt_template = self.get_prompt_template(self._current_model)
        processed_prompt = prompt.replace(model_prompt_template["system"], "-role=" + summary_role_tags["system"]) #
        processed_prompt = processed_prompt.replace(model_prompt_template["assistant"], "-role=" + summary_role_tags["assistant"]) # TODO: + (CharName)
        processed_prompt = processed_prompt.replace(model_prompt_template["user"], "-role="+summary_role_tags["user"]) #TODO: + (CharName)
        final_prompt = ""
        if chat_summary_template_tag in sys_msg:
          final_prompt = sys_msg.replace(chat_summary_template_tag, f"\n{processed_prompt}") #const
        else:
            final_prompt = sys_msg + "\n" + processed_prompt
        logger.info("-- summary prompt --")
        
        
        parser = PydanticOutputParser(pydantic_object=ChatMoodAnalysis)
        parser_instrucion = parser.get_format_instructions();
        logger.warning("-- MEMO MOOD ANALYSIS --")
        #final_instruction = f"{final_prompt}\n{parser_instrucion}" 
        #print(final_instruction)
        final_instruction = final_prompt
        llm = self._integration.fresh_model_instance(model="llama3.1-lexi-v2",temperature=temperature, max_tokens=max_tokens,ctx_len=len(final_instruction) + 300)
        summary = llm.invoke(f"{final_prompt}\n{parser_instrucion}")
        #summary = parser.invoke(response)
        #summary = self.direct_prompt(prompt=f"{final_prompt}\n{parser_instrucion}", temperature=temperature, max_tokens=max_tokens,ctx_len=ctx_len)
        logger.info("-- summary response")
        print(summary)
        
        logger.warning("-- memo generated --")
        return (final_prompt, summary.content)
    
    #TODO: embeddings(text:str)
