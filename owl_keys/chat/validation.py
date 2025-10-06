import json

def get_output(message):
    """
    Extracts the 'action' value from a model response, which may be a JSON string or a dict.
    Handles both cases where the response is a JSON string or a dict with a 'parts' key (Gemini API).
    """
    text = str(message)

    # Sometimes the model returns extra text before/after the JSON, so try to extract the JSON object
    try:
        # Find the first '{' and last '}' to extract the JSON substring
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            data = json.loads(json_str)
        else:
            # If not found, try to load the whole string
            data = json.loads(text)
    except Exception:
        # If all else fails, return None
        return None

    return data.get("action")