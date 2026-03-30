"""Ollama LLM connection for OpsMind."""
import ollama
from config import OLLAMA_MODEL


def get_response(prompt, system_prompt=None, context=None):
    """Get a response from the local Ollama LLM."""
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    if context:
        for msg in context:
            messages.append(msg)
    messages.append({'role': 'user', 'content': prompt})

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        return response['message']['content']
    except Exception as e:
        return f"LLM Error: {e}. Make sure Ollama is running (`ollama serve`) and model '{OLLAMA_MODEL}' is pulled (`ollama pull {OLLAMA_MODEL}`)."


def get_streaming_response(prompt, system_prompt=None, context=None):
    """Get a streaming response from the local Ollama LLM."""
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    if context:
        for msg in context:
            messages.append(msg)
    messages.append({'role': 'user', 'content': prompt})

    try:
        stream = ollama.chat(model=OLLAMA_MODEL, messages=messages, stream=True)
        for chunk in stream:
            yield chunk['message']['content']
    except Exception as e:
        yield f"LLM Error: {e}"


FACTORY_SYSTEM_PROMPT = """You are OpsMind, a factory AI. Be concise (2-4 sentences). Use UK units (kg, GBP). Flag problems. Reference BRC/HACCP for compliance. Never make up data."""
