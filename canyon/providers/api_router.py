import litellm
import os

class APIRouter:
    """
    Black-box router for calling external APIs and local endpoints (Ollama, vLLM) via LiteLLM.
    """
    def __init__(self, default_model: str = "gpt-4o", temperature: float = 0.1, max_tokens: int = 512, api_base: str = None, api_key: str = None, timeout: float = None):
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_base = api_base
        self.api_key = api_key
        # Per-request timeout (seconds); None leaves LiteLLM's default. Used to keep
        # multi-model benchmarks from hanging on a slow/cold model endpoint.
        self.timeout = timeout
        # Disable verbose logging from LiteLLM
        litellm.set_verbose = False

    def generate(self, prompt: str, model: str = None, temperature: float = None, max_tokens: int = None) -> str:
        target_model = model or self.default_model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        kwargs = {"num_retries": 0}  # we run our own retry loop below
        if self.timeout is not None:
            kwargs["timeout"] = self.timeout
        custom_base = self.api_base or os.environ.get("OPENAI_API_BASE")
        custom_key = self.api_key or os.environ.get("OPENAI_API_KEY")

        if (target_model.startswith("openai/") and 
            ("gemma" in target_model.lower() or "llama" in target_model.lower() or target_model.endswith(".gguf"))):
            kwargs["api_base"] = custom_base or "http://127.0.0.1:18083/v1"
            kwargs["api_key"] = custom_key or "local-key"
        elif custom_base:
            kwargs["api_base"] = custom_base
            if custom_key:
                kwargs["api_key"] = custom_key
            
        max_retries = getattr(self, "max_retries", 5)
        delay = 2.0
        backoff_factor = 2.0
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = litellm.completion(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temp,
                    max_tokens=tokens,
                    **kwargs
                )
                msg = response.choices[0].message
                content = (msg.content or "").strip()
                if not content:
                    # Reasoning models (e.g. DeepSeek V4, R1) may leave `content` empty
                    # when the token budget is spent thinking; fall back to the CoT text
                    # so the answer is still scorable instead of looking like an error.
                    content = (getattr(msg, "reasoning_content", None) or "").strip()
                return content
            except Exception as e:
                last_exception = e
                err_msg = str(e).lower()
                is_transient = any(x in err_msg for x in ["rate limit", "ratelimit", "timeout", "service unavailable", "503", "429", "temp", "busy"])
                
                if not is_transient and attempt == 0:
                    if any(x in err_msg for x in ["auth", "key", "bad request", "400", "not found"]):
                        return f"Error during LiteLLM generation: {str(e)}"
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    break
                    
        return f"Error during LiteLLM generation (after {max_retries} attempts): {str(last_exception)}"
