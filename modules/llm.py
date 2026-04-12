"""Ollama LLM connection for OpsMind."""
import json

import ollama

from config import OLLAMA_MODEL


def get_response(prompt, system_prompt=None, context=None, format=None):
    """Get a response from the local Ollama LLM.

    Args:
        prompt: The user's question or instruction.
        system_prompt: Optional system prompt to set context.
        context: Optional list of previous messages for conversation history.
        format: Optional output format. Use "json" for structured JSON responses.
    """
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    if context:
        for msg in context:
            messages.append(msg)
    messages.append({'role': 'user', 'content': prompt})

    try:
        kwargs = {'model': OLLAMA_MODEL, 'messages': messages}
        if format:
            kwargs['format'] = format
        response = ollama.chat(**kwargs)
        return response['message']['content']
    except Exception as e:
        return f"LLM Error: {e}. Make sure Ollama is running (`ollama serve`) and model '{OLLAMA_MODEL}' is pulled (`ollama pull {OLLAMA_MODEL}`)."


def get_json_response(prompt, system_prompt=None, context=None):
    """Get a structured JSON response from the LLM. Always returns valid JSON."""
    raw = get_response(prompt, system_prompt=system_prompt, context=context, format="json")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"error": "Failed to parse JSON", "raw": raw}


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


def call_with_tools(prompt, tools, system_prompt=None):
    """Call the LLM with function/tool definitions. Returns the tool call the LLM chose.

    Args:
        prompt: The user's question.
        tools: List of tool definitions (OpenAI-compatible format).
        system_prompt: Optional system prompt.

    Returns:
        dict with 'tool_calls' if the LLM chose a function, or 'content' if it responded directly.
    """
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=tools,
        )
        msg = response['message']
        if msg.get('tool_calls'):
            return {
                'tool_calls': [
                    {
                        'function': tc['function']['name'],
                        'arguments': tc['function']['arguments'],
                    }
                    for tc in msg['tool_calls']
                ]
            }
        return {'content': msg.get('content', '')}
    except Exception as e:
        return {'error': str(e)}


def get_embeddings(text, model="nomic-embed-text"):
    """Get vector embeddings for text using Ollama's embedding models.

    Args:
        text: String or list of strings to embed.
        model: Embedding model name (default: nomic-embed-text).

    Returns:
        List of embedding vectors.
    """
    try:
        if isinstance(text, str):
            text = [text]
        response = ollama.embed(model=model, input=text)
        return response['embeddings']
    except Exception as e:
        return {'error': str(e)}


FACTORY_SYSTEM_PROMPT = """You are OpsMind, a factory AI. Be concise (2-4 sentences). Use UK units (kg, GBP). Flag problems. Reference BRC/HACCP for compliance. Never make up data."""


# Tool definitions for OpsMind function calling (Level 3)
OPSMIND_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_production_data",
            "description": "Get production output, waste, and yield data for a product over a time period",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product name or species (e.g., salmon, cod)"},
                    "days": {"type": "integer", "description": "Number of days to look back (default: 7)"}
                },
                "required": ["product"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_temperature_logs",
            "description": "Get temperature readings and excursions for a storage location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Storage location name (e.g., cold storage, chiller 1)"}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get order information for a customer or product",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer": {"type": "string", "description": "Customer name or code"},
                    "product": {"type": "string", "description": "Product name (optional)"}
                },
                "required": ["customer"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_staff_hours",
            "description": "Get employee working hours and overtime data",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee": {"type": "string", "description": "Employee name (optional, omit for all staff)"},
                    "period": {"type": "string", "description": "Time period: this_week, last_week, this_month"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_compliance",
            "description": "Run compliance checks: batch traceability, allergen matrix, temperature excursions",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_type": {"type": "string", "description": "Type: traceability, allergens, temperature, all"},
                    "batch_code": {"type": "string", "description": "Batch code to trace (for traceability checks)"}
                },
                "required": ["check_type"]
            }
        }
    },
]
