
from typing import Any, List, override
from fastapi import HTTPException
from langchain_ollama import ChatOllama
from loguru import logger
from api.infrastructure.llm.llm_config import LLM_Config
from api.infrastructure.llm.llm_provider import LLM_Provider
from api.models.schemas import ChatPromptDto


""" OLLAMA CHECK:
    mirostat: Optional[int] = None
    Enable Mirostat sampling for controlling perplexity.
    (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0)

    mirostat_eta: Optional[float] = None
    Influences how quickly the algorithm responds to feedback
    from the generated text. A lower learning rate will result in
    slower adjustments, while a higher learning rate will make
    the algorithm more responsive. (Default: 0.1)

    mirostat_tau: Optional[float] = None
    Controls the balance between coherence and diversity
    of the output. A lower value will result in more focused and
    coherent text. (Default: 5.0)
"""
class Ollama_Provider(LLM_Provider):
    
    def __init__(self):
        super().__init__()
        self.display_name = "ollama"
        self._available_models = ["llama3.1-lexi-v2", "hermes3","qwen2.5:7b", "llama3.1:8b", "qwen:2.5:14b",  "DarkIdol-llama3.1-8B", "Peach-9B-Roleplay", "MN-DARKEST-UNIVERSE-29B-Q3m", "Dark-Champion-MOE-21B-uncen-ablit-Q5"]
        if self._config is None:
            self._config = LLM_Config()

    @override
    def chat_request(self, request: ChatPromptDto, excluded_events: List[str] = [], guidance_token: str = '') -> str:
        dyn_model = self.fresh_model_instance(model=request.model_name, temperature=request.temperature, max_tokens=request.max_tokens) 
        response = ""
        if self._use_chat_template:
            prompt = self.chat_history_to_template(chat_history=request.chat_history, assistant_guidance_token=guidance_token) #TODO: excluir eventos sys seleccionados o añadir todos (#WIP: sistema eventos chat)
            print(">> CHAT REQUEST >>\n\n", prompt)
            response = dyn_model.invoke(input=prompt)
        else:  
           # response = self._model.invoke(input=request.chat_history, temperature=request.temperature, max_tokens=request.max_tokens) #TODO: hay que pasarlo como tupla
            response = dyn_model.invoke(input=request.chat_history)
        return response.content
    @override
    def direct_prompt(self, prompt, temperature:float = 0.7, max_tokens: int = 600, ctx_len:int = 2048) -> str:
        llm = ChatOllama(
            model=self._mode_name,
            temperature = temperature,
            num_predict = max_tokens,
            num_ctx=ctx_len,
            num_thread=self._config.n_threads,
            num_gpu=self._config.ngl,
            top_k=self._config.top_k,
            top_p=self._config.top_p,
            repeat_last_n=self._config.repeat_last_n,
            repeat_penalty=self._config.repeat_penalty,
            verbose=True)
        return llm.invoke(prompt).content
    
    @override
    def fresh_model_instance(self, model:str = None, temperature:float = 0.7, max_tokens: int = 600, ctx_len:int = 2048) -> Any:
        llm = ChatOllama(
            model=model if model is not None and model in self._available_models else self._mode_name,
            temperature = temperature,
            num_predict = max_tokens,
            num_ctx=ctx_len,
            num_thread=self._config.n_threads,
            num_gpu=self._config.ngl,
            top_k=self._config.top_k,
            top_p=self._config.top_p,
            #tfs_z=2,
            repeat_last_n=self._config.repeat_last_n,
            repeat_penalty=self._config.repeat_penalty,
            mirostat_tau=4.0,
            mirostat=1,
            verbose=True)
        return llm   