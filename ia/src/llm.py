import json

import requests

URL = "http://localhost:11434/api/chat"
MODELO = "qwen2.5:3b"


def perguntar(sistema, usuario):
    r = requests.post(URL, json={
        "model": MODELO,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_ctx": 4096},
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
    }, timeout=180)
    r.raise_for_status()
    return r.json()["message"]["content"]


def como_json(texto):
    try:
        d = json.loads(texto)
        return d if isinstance(d, dict) else None
    except ValueError:
        return None
