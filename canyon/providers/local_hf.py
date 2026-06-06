import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import numpy as np

class LocalHFProvider:
    """
    White-box provider for local Hugging Face models.
    Supports registering PyTorch forward hooks to extract hidden states (activations)
    and training basic linear probes.
    """
    def __init__(self, model_name_or_path: str, device: str = "cuda", torch_dtype: str = "bfloat16", load_in_8bit: bool = False, load_in_4bit: bool = False):
        self.model_name_or_path = model_name_or_path
        self.device = device
        self.torch_dtype = getattr(torch, torch_dtype) if hasattr(torch, torch_dtype) else torch.float16
        self.load_in_8bit = load_in_8bit
        self.load_in_4bit = load_in_4bit
        
        self.model = None
        self.tokenizer = None
        self.activations = {}
        self.hooks = []

    def load_model(self):
        if self.model is not None:
            return
        
        print(f"Loading local model {self.model_name_or_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name_or_path)
        
        kwargs = {
            "device_map": {"": "cuda:0"} if self.device == "cuda" else None
        }
        if self.load_in_8bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
        elif self.load_in_4bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=self.torch_dtype
            )
        else:
            kwargs["torch_dtype"] = self.torch_dtype
            
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name_or_path,
            **kwargs
        )
        if self.device != "cuda" and not (self.load_in_8bit or self.load_in_4bit):
            self.model = self.model.to(self.device)
        self.model.eval()

    def _get_hook(self, name):
        def hook(model, input, output):
            # output is typically a tuple for attention/decoder layers
            # the first element is the hidden state tensor (batch, seq_len, hidden_dim)
            if isinstance(output, tuple):
                self.activations[name] = output[0].detach().cpu().numpy()
            else:
                self.activations[name] = output.detach().cpu().numpy()
        return hook

    def register_layer_hooks(self, layer_indices):
        self.load_model()
        self.remove_hooks()
        
        # Identify decoder layers for common architectures (Gemma, Llama, Qwen)
        if hasattr(self.model, "model") and hasattr(self.model.model, "layers"):
            layers = self.model.model.layers
        elif hasattr(self.model, "transformer") and hasattr(self.model.transformer, "h"):
            layers = self.model.transformer.h
        else:
            raise AttributeError("Could not identify decoder layers in model architecture.")

        for idx in layer_indices:
            if idx < len(layers):
                name = f"layer_{idx}"
                hook_handle = layers[idx].register_forward_hook(self._get_hook(name))
                self.hooks.append(hook_handle)

    def remove_hooks(self):
        for h in self.hooks:
            h.remove()
        self.hooks = []
        self.activations = {}

    def generate_with_activations(self, prompt: str, layer_indices: list, max_new_tokens: int = 50):
        self.load_model()
        self.register_layer_hooks(layer_indices)
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                output_hidden_states=True,
                return_dict_in_generate=True
            )
        
        generated_text = self.tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)
        
        # Gather captured activations
        captured = {k: v.tolist() for k, v in self.activations.items()}
        self.remove_hooks()
        
        return generated_text, captured

    def train_linear_probe(self, layer_idx: int, positive_prompts: list, negative_prompts: list):
        """
        Train a simple linear classifier (Logistic Regression) over the hidden states
        of a specific layer to detect concepts like "truthfulness" or "physical plausibility".
        """
        self.load_model()
        self.register_layer_hooks([layer_idx])
        
        X = []
        y = []
        
        # Collect positive samples
        for p in positive_prompts:
            inputs = self.tokenizer(p, return_tensors="pt").to(self.device)
            with torch.no_grad():
                self.model(**inputs)
            # Take activation of the last token in sequence
            act = self.activations[f"layer_{layer_idx}"][0, -1, :]
            X.append(act)
            y.append(1)
            
        # Collect negative samples
        for p in negative_prompts:
            inputs = self.tokenizer(p, return_tensors="pt").to(self.device)
            with torch.no_grad():
                self.model(**inputs)
            act = self.activations[f"layer_{layer_idx}"][0, -1, :]
            X.append(act)
            y.append(0)
            
        self.remove_hooks()
        
        X = np.array(X)
        y = np.array(y)
        
        # Simple Gradient Descent for Logistic Regression
        n_samples, n_features = X.shape
        weights = np.zeros(n_features)
        bias = 0.0
        lr = 0.01
        
        def sigmoid(z):
            return 1 / (1 + np.exp(-np.clip(z, -20, 20)))
            
        for _ in range(100):
            model_preds = sigmoid(np.dot(X, weights) + bias)
            dw = (1 / n_samples) * np.dot(X.T, (model_preds - y))
            db = (1 / n_samples) * np.sum(model_preds - y)
            weights -= lr * dw
            bias -= lr * db
            
        return {"weights": weights.tolist(), "bias": bias, "layer_idx": layer_idx}
