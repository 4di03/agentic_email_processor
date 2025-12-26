import requests
import json 
MODEL = 'llama3.1:8b'
STREAM = True
# assumes ollama is running with `ollama serve` and the above model is downloaded `ollama pull <MODEL>`
url = "http://localhost:11434/api/generate"
payload = {
    "model": MODEL,
    "prompt": "what is your name, and what do you do?",
    "stream": STREAM
}

r = requests.post(url, json=payload, stream=STREAM)
for line in r.iter_lines():
    print(json.loads(line)["response"],end = '' , flush=True)