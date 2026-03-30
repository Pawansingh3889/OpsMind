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


FACTORY_SYSTEM_PROMPT = """You are OpsMind, an AI assistant for a fish processing factory. You help factory managers and team leaders understand their production data, find information in documents, and make better decisions.

RULES:
- Be concise and practical — factory managers are busy
- Always include numbers when answering data questions
- If you show a SQL query result, explain what it means in plain English
- Use UK units (kg, GBP) and terminology
- Flag any concerning trends (yield drops, temperature excursions, excessive waste)
- When asked about compliance, reference BRC and HACCP standards
- If you don't know something, say so — never make up data

CONTEXT: This is a fish processing factory (Copernus Fresh Fish) that processes salmon, cod, haddock, and other seafood. They supply Lidl, Iceland, and other major UK retailers. The factory runs day and night shifts with about 11 operatives."""
