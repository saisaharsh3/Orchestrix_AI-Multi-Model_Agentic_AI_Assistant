from models.local_llm import local_generate
from models.gemini_llm import gemini_generate

def generate_llm(prompt, model_type="api"):
    if model_type == "local":
        return local_generate(prompt)
    return gemini_generate(prompt)
def generate_llm(prompt: str, model_type: str):
    try:
        if model_type == "api":
            return gemini_generate(prompt)
        else:
            return local_generate(prompt)

    except Exception as e:
        # Auto fallback if API quota is exceeded
        if "RESOURCE_EXHAUSTED" in str(e):
            print(" API quota exhausted — switching to LOCAL model")
            return local_generate(prompt)

        raise e
