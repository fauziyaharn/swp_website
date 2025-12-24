import os
import sys
import urllib.request

MODEL_URL = os.environ.get("MODEL_URL")
MODEL_DIR = os.path.join(os.getcwd(), "transformers_swp", "models", "local_transformer_intent")
os.makedirs(MODEL_DIR, exist_ok=True)

if not MODEL_URL:
    print("No MODEL_URL provided; skipping download.")
    sys.exit(0)

target = os.path.join(MODEL_DIR, "model.pt")
print("Downloading model from", MODEL_URL)
try:
    urllib.request.urlretrieve(MODEL_URL, target)
    print("Saved to", target)
except Exception as e:
    print("Failed to download model:", e)
    sys.exit(2)
