
from typing import override

from api.infrastructure.llm.settings.llm_config import LLM_Config
from dataclasses import dataclass

@dataclass
class Ollama_Config(LLM_Config):
    mirostat: int = 1
    mirostat_eta: float = 0.3
    mirostat_tau: float = 4.0
    tfs_z: int = 2

    @override
    def get_settings_preset(self, name = "default", ctx_len: int = 4096):
        print("OLLAMA CONFIG >> GETTING PRESET")
        match name:
            case "default":
                return Ollama_Config(
                    temp=1.0, 
                    max_tokens=450, 
                    top_p=0.5, 
                    top_k=10, 
                    mirostat=1,
                    ctx_len=ctx_len if ctx_len is not None else self._config.num_ctx, 
                    mirostat_eta=0.3, 
                    mirostat_tau=5.0, 
                    repeat_last_n=-1, 
                    repeat_penalty=1.3)
            case "characters":
                return Ollama_Config(
                    temp=0.8, 
                    max_tokens=600, 
                    top_p=0.7, 
                    top_k=10, 
                    mirostat=1,
                    ctx_len=ctx_len if ctx_len is not None else self._config.num_ctx, 
                    mirostat_eta=0.2, 
                    mirostat_tau=4.0, 
                    repeat_last_n=-1, 
                    repeat_penalty=1.1)
            case "chat":
                return Ollama_Config(
                    temp=1.0, 
                    max_tokens=450, 
                    top_p=0.8, 
                    top_k=10, 
                    mirostat=1,
                    ctx_len=ctx_len if ctx_len is not None else self._config.num_ctx, 
                    mirostat_eta=0.3, 
                    mirostat_tau=5.0, 
                    repeat_last_n=-1, 
                    repeat_penalty=1.3)
            case "analysis":
                print("RETURNING ANALYSIS SETTINGS")
                return Ollama_Config(
                    temp=0.7, 
                    max_tokens=600, 
                    top_p=0.7, 
                    top_k=10, 
                    mirostat=1, 
                    mirostat_eta=0.2, 
                    mirostat_tau=3.0, 
                    repeat_last_n=-1, 
                    repeat_penalty=1.1)
            case "summary":
                return Ollama_Config(
                    temp=0.6, 
                    max_tokens=600, 
                    top_p=0.5, 
                    top_k=10, 
                    mirostat=1, 
                    mirostat_eta=0.3, 
                    mirostat_tau=3.0, 
                    repeat_last_n=-1, 
                    repeat_penalty=1.1)
        return super().get_settings_preset(name)