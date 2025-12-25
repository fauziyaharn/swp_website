from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import time

app = Flask(__name__)
CORS(app)

# Ensure transformers_swp package is importable from repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TS_PATH = os.path.join(ROOT, 'transformers_swp')
if TS_PATH not in sys.path:
    sys.path.insert(0, TS_PATH)

try:
    import importlib
    ts_app = importlib.import_module('app')
except Exception as e:
    try:
        ts_app = importlib.import_module('transformers_swp.app')
    except Exception as ex:
        ts_app = None
        print('Failed to import transformers_swp.app:', e, ex)


@app.route('/api/process', methods=['POST'])
def process_endpoint():
    if ts_app is None:
        return jsonify({'error': 'backend_unavailable', 'message': 'transformers_swp module could not be imported'}), 500

    data = request.get_json(force=True)
    text = data.get('text', '') if isinstance(data, dict) else ''
    if not text:
        return jsonify({'error': 'text_empty'}), 400

    initialized = ts_app.ensure_initialized(sync=True)
    if not initialized:
        return jsonify({'error': 'initializing', 'message': 'AI is still initializing, try again shortly'}), 503

    start = time.time()
    try:
        ai_pipeline = getattr(ts_app, 'ai_pipeline', None)
        recommendation_engine = getattr(ts_app, 'recommendation_engine', None)
        package_planner = getattr(ts_app, 'package_planner', None)
        wedding_dataset = getattr(ts_app, 'wedding_dataset', None)

        if ai_pipeline is None or recommendation_engine is None or wedding_dataset is None:
            return jsonify({'error': 'not_ready', 'message': 'AI pipeline or resources not ready'}), 503

        ai_result = ai_pipeline.predict(text) if hasattr(ai_pipeline, 'predict') else ai_pipeline(text)

        items = wedding_dataset
        try:
            import pandas as _pd
            if isinstance(wedding_dataset, _pd.DataFrame):
                items = wedding_dataset.to_dict(orient='records')
        except Exception:
            pass

        clustering_result = recommendation_engine.cluster_items(items, ai_result.get('slots', {}))

        if package_planner:
            try:
                package = package_planner.create_package_recommendations(ai_result.get('slots', {}))
            except Exception:
                package = None
        else:
            package = None

        assistant_reply = None
        if hasattr(ts_app, 'generate_assistant_reply'):
            assistant_reply = ts_app.generate_assistant_reply(ai_result, clustering_result, [])

        response = {
            'user_text': text,
            'intent': ai_result.get('intent_pred'),
            'slots': ai_result.get('slots'),
            'probabilities': ai_result.get('probs'),
            'recommendations': clustering_result,
            'wedding_package': package,
            'assistant_reply': assistant_reply,
        }

        response['_processing_time_ms'] = int((time.time() - start) * 1000)
        return jsonify(response)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print('Error in serverless wrapper:', tb)
        return jsonify({'error': 'internal_error', 'message': str(e), 'trace': tb}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
