import json
import re


def safe_parse_json(text: str) -> dict:
    """
    Robustly parse a JSON object from any AI provider's raw response.

    Handles:
    - Markdown fences  (```json ... ``` or ``` ... ```)
    - Leading/trailing prose before or after the JSON block
    - Gemini edge cases (fence wrapping even with response_mime_type set)
    - Finds the first matching { ... } block by brace depth
    """
    text = text.strip()

    # 1. Strip leading/trailing markdown fences (Gemini sometimes adds them
    #    even when response_mime_type="application/json" is set)
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # 2. If still fenced (e.g. inner fence pair), extract the fenced content
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fenced:
        text = fenced.group(1).strip()

    # 3. Find the first '{' and walk to its matching '}'
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]!r}")

    depth = 0
    end = -1
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        raise ValueError(f"Unmatched braces in JSON response: {text[:200]!r}")

    return json.loads(text[start : end + 1])
