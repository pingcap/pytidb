MODEL_ALIASES = {
    "text-embedding-3-small": "openai/text-embedding-3-small",
    "text-embedding-3-large": "openai/text-embedding-3-large",
    "text-embedding-ada-002": "openai/text-embedding-ada-002",
}


def normalize_model_name(model_name: str) -> str:
    if model_name in MODEL_ALIASES:
        return MODEL_ALIASES[model_name]
    return model_name
