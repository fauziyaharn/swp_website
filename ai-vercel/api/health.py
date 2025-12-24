from flask import Flask, jsonify
import os
import sys

app = Flask(__name__)

# Ensure transformers_swp is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TS_PATH = os.path.join(ROOT, 'transformers_swp')
if TS_PATH not in sys.path:
    sys.path.insert(0, TS_PATH)

try:
    import importlib
    ts_app = importlib.import_module('app')
except Exception:
    try:
        ts_app = importlib.import_module('transformers_swp.app')
    except Exception:
        ts_app = None


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    if ts_app is None:
        return jsonify({'status': 'ok', 'initialized': False, 'initializing': False, 'note': 'transformers_swp module not available'}), 200
    try:
        initialized = getattr(ts_app, 'ai_pipeline', None) is not None
        initializing = getattr(ts_app, 'init_in_progress', False)
        return jsonify({'status': 'ok', 'initialized': bool(initialized), 'initializing': bool(initializing)}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
