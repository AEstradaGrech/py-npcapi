from api.models.schemas import ModelIntegrationSettingsDto


"""

- Use a smaller N_BATCH to reduce the amount of data transferred between CPU and GPU during training. 
  This will also help to minimize the number of iterations required to complete training, which can further improve performance.

- Reduce the MAX_TOKENS parameter in your LLMConfig object to limit the maximum length of generated responses. 
  This will reduce the amount of memory required for storing intermediate results during inference and also help to prevent out-of-memory errors.

- Use a lower value for the TEMP parameter in your LLMConfig object to control the randomness of the sampling process used by the LLM to generate responses. 
  A lower temperature will result in more deterministic and predictable results, which can further improve performance and reduce memory usage during inference.

- Use a smaller value for the TOP_K parameter in your LLMConfig object to control the number of highest-scoring tokens that are considered when generating responses.
  A smaller top k will result in fewer intermediate calculations being performed, which can further improve performance and reduce memory usage during inference.

- Use a lower value for the TOP_P parameter in your LLMConfig object to control the cumulative probability of token selections up to that point. 
  A lower top p will result in more diverse responses being generated, but also require fewer intermediate calculations being performed, which can further 
  improve performance and reduce memory usage during inference.

- Use a smaller value for the N_PREDICT parameter in your LLMConfig object to control the number of tokens that are predicted at each step during generation.
  A smaller n predict will result in fewer intermediate calculations being performed, which can further improve performance and reduce memory usage during inference.

- Implement lazy loading or caching mechanisms for frequently used models (like GPT4All) to minimize data transfer between CPU and GPU during model initialization. 
  This can significantly reduce the amount of time required to load a model into memory and also help to prevent out-of-memory errors during training or inference.

- Use a lower value for the REPEAT_LAST_N parameter in your LLMConfig object to control how many times previous tokens are repeated during generation. 
  A smaller repeat last n will result in fewer intermediate calculations being performed, which can further improve performance and reduce memory usage during inference.

- Implement memory management techniques like double buffering or lazy evaluation of intermediate results to minimize data transfer between CPU and GPU during model execution. 
  This can significantly reduce the amount of time required to complete a single inference request and also help to prevent out-of-memory errors during training or inference, 
  especially when dealing with very large batch sizes or complex prompts. (WTF?!)

"""
class LLM_Config:
    temp:           int   
    top_p:          float = 0.5
    top_k:          int   = 10
    n_batch:        int   = 8
    n_predict:      int   #n_predict: Equivalent to max_tokens, exists for backwards compatibility.
    max_tokens:     int   
    repeat_last_n:  int   = -1
    repeat_penalty: float = 1.1
    n_threads:      int   = 6  #number of CPU processor threads to use in parallel computations
    ngl:            int   = 32 #number of NN Layers to load in the GPU
    ctx_len:        int   = 4096 #Max for LLama 8B = 4,096

    
    def __init__(self, temp=2.0, max_tokens=300, ctx_len = 4096):
        self.temp = temp
        self.max_tokens = max_tokens
        self.n_predict = max_tokens
        self.ctx_len = ctx_len

    def map_from_request(self, req: ModelIntegrationSettingsDto):
        if req.temp is not None:
            self.temp = req.temp
        if req.max_tokens is not None:
            self.max_tokens = req.max_tokens
            self.n_predict = req.max_tokens
        if req.top_k is not None:
            self.top_k = req.top_k
        if req.top_p is not None:
            self.top_p = req.top_p
        if req.repeat_last_n is not None:
            self.repeat_last_n = req.repeat_last_n
        if req.repeat_penalty is not None:
            self.repeat_penalty = req.repeat_penalty
        if req.ctx_len is not None:
            self.ctx_len = req.ctx_len
        if req.n_threads is not None:
            self.n_threads = req.n_threads
        if req.ngl is not None:
            self.ngl = req.ngl
        return self
    
    def to_dict(self):
        return {
            "temp": self.temp,         
            "top_p":self.top_p,
            "top_k": self.top_k,
            "n_batch":self.n_batch,
            "n_predict": self.n_predict,
            "max_tokens": self.max_tokens,
            "repeat_last_n": self.repeat_last_n,
            "repeat_penalty": self.repeat_penalty,
            "n_threads": self.n_threads,
            "ngl": self.ngl,
            "ctx_len": self.ctx_len 
        }
    