from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import time
import threading
import urllib.request
import shutil
import json

app = Flask(__name__)
CORS(app)

from api.ai_stub import ensure_initialized, predict as ai_predict
ts_app = None
_model_lock = threading.Lock()
_model_downloading = False
_model_last_error = None
MODEL_DEST = os.environ.get('MODEL_DEST', '/tmp/model.pt')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def _load_json_file(name):
    path = os.path.join(DATA_DIR, name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


@app.route('/api/process', methods=['POST'])
def process_endpoint():
    """Wrapper endpoint suitable for Vercel serverless (Flask WSGI app).

    It delegates to the logic inside `transformers_swp/app.py` while ensuring
    lazy initialization is respected.
    """
    # use lightweight ai_stub regardless of transformers_swp availability

    # support preflight checks from browsers
    if request.method == 'OPTIONS':
        resp = ('', 204)
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }
        return resp, 204, headers

    data = request.get_json(force=True)
    text = data.get('text', '') if isinstance(data, dict) else ''
    if not text:
        r = jsonify({'error': 'text_empty'})
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return r, 400

    # initialize lightweight ai stub
    initialized = ensure_initialized(sync=True)
    if not initialized:
        return jsonify({'error': 'initializing', 'message': 'AI is still initializing, try again shortly'}), 503

    start = time.time()
    try:
        ai_result = ai_predict(text)
        # If using the lightweight stub and the intent is package search,
        # synthesize a few demo recommendations so the frontend shows results.
        recommendations = []
        try:
            intent = ai_result.get('intent_pred')
            # normalize intent: treat related queries as package search
            text_lower = text.lower() if isinstance(text, str) else ''
            if 'paket' in text_lower:
                intent = 'cari_rekomendasi_paket'
            # Also treat venue/vendor/dekor/catering/mua/rekomendasi/cari queries as package searches
            if intent in ('cari_venue', 'cari_dekor', 'cari_vendor', 'cari_catering') or any(k in text_lower for k in ('rekomendasi', 'cari', 'mua', 'venue', 'catering', 'dekor', 'vendor')):
                intent = 'cari_rekomendasi_paket'
            slots = ai_result.get('slots') or {}
            if intent == 'cari_rekomendasi_paket':
                # derive some basic fields from slots
                lokasi_slot = slots.get('lokasi') or 'Bandung'
                # support multiple requested locations (list) -> generate recommendations per-location
                if isinstance(lokasi_slot, list):
                    locations = lokasi_slot
                else:
                    locations = [lokasi_slot]
                tema = slots.get('tema') or 'Classic'
                try:
                    bmin = int(slots.get('budget_min')) if slots.get('budget_min') else 5000000
                except Exception:
                    bmin = 5000000
                try:
                    bmax = int(slots.get('budget_max')) if slots.get('budget_max') else 20000000
                except Exception:
                    bmax = 20000000
                # preserve None if user didn't specify jumlah_tamu
                tamu = slots.get('jumlah_tamu') if slots.get('jumlah_tamu') is not None else None
                # try to load vendor lists shipped with the backend and build
                # composite package recommendations that include one vendor
                # from several categories (WO, MUA, Decoration, Catering, Documentation/Entertainment).
                vendors_data = _load_json_file('vendors.json') or {}
                wo_list = vendors_data.get('wo') or vendors_data.get('wo', []) if isinstance(vendors_data, dict) else []
                mua_list = vendors_data.get('mua') or []
                decor_list = vendors_data.get('decoration') or vendors_data.get('decor') or []
                doc_list = vendors_data.get('documentation') or []
                entert_list = vendors_data.get('entertainment') or []
                catering_list = vendors_data.get('catering') or []

                # fallback defaults if lists are empty
                if not wo_list:
                    wo_list = ['Sepasang Wedding Planner', 'SepasangWP Team', 'SWP Organizer']
                if not mua_list:
                    mua_list = ['Make Up By Yuliana Dewi', 'Giskavina', 'Kemalia Kentina']
                if not decor_list:
                    decor_list = ['GP Florist', 'Sadiqa Decoration', 'Aksen Dekorasi']
                if not doc_list:
                    doc_list = ['Alura Photography', 'The Couple Studio', 'Dearpict']
                if not entert_list:
                    entert_list = ['Bio Music Pro', 'Amazingdays', 'DMT Music']
                if not catering_list:
                    catering_list = ['Sedap Catering', 'Asparagus Catering', 'Kartika Catering']

                # create recommendations: for multiple locations, produce 2 per location
                per_loc = 2
                for loc_idx, loc in enumerate(locations):
                    for sub_idx in range(per_loc):
                    # helper to normalize vendor entry which may be a string or dict
                    def _vendor_fields(item):
                        if isinstance(item, dict):
                            return item.get('name'), item.get('url'), item.get('image'), item.get('contact')
                        return (item, None, None, None)
                    idx = loc_idx * per_loc + sub_idx
                    wo_item = wo_list[idx % len(wo_list)]
                    mua_item = mua_list[idx % len(mua_list)]
                    decor_item = decor_list[idx % len(decor_list)]
                    doc_item = doc_list[idx % len(doc_list)]
                    entert_item = entert_list[idx % len(entert_list)]
                    catering_item = catering_list[idx % len(catering_list)]

                    wo_name, wo_url, wo_image, wo_contact = _vendor_fields(wo_item)
                    mua_name, mua_url, mua_image, mua_contact = _vendor_fields(mua_item)
                    decor_name, decor_url, decor_image, decor_contact = _vendor_fields(decor_item)
                    doc_name, doc_url, doc_image, doc_contact = _vendor_fields(doc_item)
                    entert_name, entert_url, entert_image, entert_contact = _vendor_fields(entert_item)
                    catering_name, catering_url, catering_image, catering_contact = _vendor_fields(catering_item)

                    recommendations.append({
                        'name': f"{wo_name}",
                        'wo': {'name': wo_name, 'url': wo_url, 'image': wo_image, 'contact': wo_contact},
                        'mua': {'name': mua_name, 'url': mua_url, 'image': mua_image, 'contact': mua_contact},
                        'decoration': {'name': decor_name, 'url': decor_url, 'image': decor_image, 'contact': decor_contact},
                        'documentation': {'name': doc_name, 'url': doc_url, 'image': doc_image, 'contact': doc_contact},
                        'entertainment': {'name': entert_name, 'url': entert_url, 'image': entert_image, 'contact': entert_contact},
                        'catering': {'name': catering_name, 'url': catering_url, 'image': catering_image, 'contact': catering_contact},
                        'tema': tema,
                        'lokasi': loc,
                        'budget_min': int(bmin),
                        'budget_max': int(bmax),
                        'jumlah_tamu': tamu,
                        'tipe_acara': 'Resepsi',
                        'venue': f"{wo_name} Venue, {loc}",
                        'waktu': slots.get('waktu') or None,
                        'demo': False,
                    })
        except Exception:
            recommendations = []
        # ensure ai_result reflects any intent/slot overrides so frontend sees them
        try:
            ai_result['intent_pred'] = intent
            ai_result['slots'] = slots
            ai_result['probs'] = {intent: 1.0}
        except Exception:
            pass

        # include model availability diagnostics
        try:
            import torch as _torch  # noqa: F401
            torch_available = True
        except Exception:
            torch_available = False
        model_on_disk = os.path.exists(MODEL_DEST)

        # If no recommendations were produced but the user's text clearly asks
        # for recommendations (keywords), synthesize demo recommendations anyway
        try:
            text_lower = text.lower() if isinstance(text, str) else ''
            if (not recommendations) and any(k in text_lower for k in ('rekomendasi', 'paket', 'mua', 'venue', 'dekor', 'catering', 'vendor', 'cari')):
                # regenerate recommendations using slots (safely recompute local vars)
                try:
                    # compute local slot values with safe defaults
                    lokal_slot = slots.get('lokasi') if slots else None
                    if isinstance(lokal_slot, list):
                        locations = lokal_slot
                    elif lokal_slot:
                        locations = [lokal_slot]
                    else:
                        locations = ['Bandung']
                    tema_local = slots.get('tema') if slots and slots.get('tema') else 'Classic'
                    try:
                        bmin_local = int(slots.get('budget_min')) if slots and slots.get('budget_min') else 5000000
                    except Exception:
                        bmin_local = 5000000
                    try:
                        bmax_local = int(slots.get('budget_max')) if slots and slots.get('budget_max') else 20000000
                    except Exception:
                        bmax_local = 20000000
                    tamu_local = slots.get('jumlah_tamu') if slots and slots.get('jumlah_tamu') is not None else None

                    vendors_data = _load_json_file('vendors.json') or {}
                    wo_list = vendors_data.get('wo') or []
                    mua_list = vendors_data.get('mua') or []
                    decor_list = vendors_data.get('decoration') or vendors_data.get('decor') or []
                    doc_list = vendors_data.get('documentation') or []
                    entert_list = vendors_data.get('entertainment') or []
                    catering_list = vendors_data.get('catering') or []
                    if not wo_list:
                        wo_list = ['Sepasang Wedding Planner', 'SepasangWP Team', 'SWP Organizer']
                    if not mua_list:
                        mua_list = ['Make Up By Yuliana Dewi', 'Giskavina', 'Kemalia Kentina']
                    if not decor_list:
                        decor_list = ['GP Florist', 'Sadiqa Decoration', 'Aksen Dekorasi']
                    if not doc_list:
                        doc_list = ['Alura Photography', 'The Couple Studio', 'Dearpict']
                    if not entert_list:
                        entert_list = ['Bio Music Pro', 'Amazingdays', 'DMT Music']
                    if not catering_list:
                        catering_list = ['Sedap Catering', 'Asparagus Catering', 'Kartika Catering']
                    per_loc = 2
                    for loc_idx, loc in enumerate(locations):
                        for sub_idx in range(per_loc):
                            def _vendor_fields(item):
                                if isinstance(item, dict):
                                    return item.get('name'), item.get('url'), item.get('image'), item.get('contact')
                                return (item, None, None, None)
                            idx = loc_idx * per_loc + sub_idx
                            wo_item = wo_list[idx % len(wo_list)]
                            mua_item = mua_list[idx % len(mua_list)]
                            decor_item = decor_list[idx % len(decor_list)]
                            doc_item = doc_list[idx % len(doc_list)]
                            entert_item = entert_list[idx % len(entert_list)]
                            catering_item = catering_list[idx % len(catering_list)]
                            wo_name, wo_url, wo_image, wo_contact = _vendor_fields(wo_item)
                            mua_name, mua_url, mua_image, mua_contact = _vendor_fields(mua_item)
                            decor_name, decor_url, decor_image, decor_contact = _vendor_fields(decor_item)
                            doc_name, doc_url, doc_image, doc_contact = _vendor_fields(doc_item)
                            entert_name, entert_url, entert_image, entert_contact = _vendor_fields(entert_item)
                            catering_name, catering_url, catering_image, catering_contact = _vendor_fields(catering_item)
                            recommendations.append({
                                'name': f"{wo_name}",
                                'wo': {'name': wo_name, 'url': wo_url, 'image': wo_image, 'contact': wo_contact},
                                'mua': {'name': mua_name, 'url': mua_url, 'image': mua_image, 'contact': mua_contact},
                                'decoration': {'name': decor_name, 'url': decor_url, 'image': decor_image, 'contact': decor_contact},
                                'documentation': {'name': doc_name, 'url': doc_url, 'image': doc_image, 'contact': doc_contact},
                                'entertainment': {'name': entert_name, 'url': entert_url, 'image': entert_image, 'contact': entert_contact},
                                'catering': {'name': catering_name, 'url': catering_url, 'image': catering_image, 'contact': catering_contact},
                                'tema': tema_local,
                                'lokasi': loc,
                                'budget_min': int(bmin_local),
                                'budget_max': int(bmax_local),
                                'jumlah_tamu': tamu_local,
                                'tipe_acara': 'Resepsi',
                                'venue': f"{wo_name} Venue, {loc}",
                                'waktu': slots.get('waktu') or None,
                                'demo': False,
                            })
                except Exception:
                    pass
        except Exception:
            pass

        response = {
            'user_text': text,
            'intent': ai_result.get('intent_pred'),
            'slots': ai_result.get('slots'),
            'probabilities': ai_result.get('probs'),
            'recommendations': recommendations,
            'wedding_package': None,
            'assistant_reply': None,
            'model_on_disk': model_on_disk,
            'torch_available': torch_available,
        }
        response['_processing_time_ms'] = int((time.time() - start) * 1000)
        r = jsonify(response)
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return r
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print('Error in serverless wrapper (stub):', tb)
        return jsonify({'error': 'internal_error', 'message': str(e), 'trace': tb}), 500


@app.route('/api/model-status', methods=['GET'])
def model_status():
    """Return whether model is present on disk and start background download if missing.

    Response JSON keys: model_url, exists, size, downloading, last_error
    """
    global _model_downloading, _model_last_error
    model_url = os.environ.get('MODEL_URL')
    if isinstance(model_url, str):
        model_url = model_url.strip()
    resp = {'model_url': model_url, 'exists': False, 'size': 0, 'downloading': False, 'last_error': _model_last_error}

    try:
        if model_url is None:
            resp['last_error'] = 'MODEL_URL not set'
            return jsonify(resp), 400

        if os.path.exists(MODEL_DEST):
            resp['exists'] = True
            resp['size'] = os.path.getsize(MODEL_DEST)
            return jsonify(resp)

        # if already downloading, return status
        if _model_downloading:
            resp['downloading'] = True
            return jsonify(resp)

        # if sync requested, download inline (may block and risk timeout)
        sync = request.args.get('sync', '').lower() in ('1', 'true', 'yes')
        if sync:
            with _model_lock:
                _model_downloading = True
                _model_last_error = None
            try:
                tmp_dest = MODEL_DEST + '.tmp'
                parent = os.path.dirname(tmp_dest)
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, exist_ok=True)
                with urllib.request.urlopen(model_url, timeout=60) as r:
                    with open(tmp_dest, 'wb') as out_f:
                        shutil.copyfileobj(r, out_f)
                os.replace(tmp_dest, MODEL_DEST)
                resp['exists'] = True
                resp['size'] = os.path.getsize(MODEL_DEST)
                return jsonify(resp)
            except Exception as e:
                _model_last_error = str(e)
                resp['last_error'] = _model_last_error
                return jsonify(resp), 500
            finally:
                _model_downloading = False

        # start background download (may not complete if Vercel kills process)
        def _download():
            global _model_downloading, _model_last_error
            with _model_lock:
                _model_downloading = True
                _model_last_error = None
            try:
                tmp_dest = MODEL_DEST + '.tmp'
                # ensure parent dir exists
                parent = os.path.dirname(tmp_dest)
                if parent and not os.path.exists(parent):
                    os.makedirs(parent, exist_ok=True)

                with urllib.request.urlopen(model_url, timeout=30) as r:
                    with open(tmp_dest, 'wb') as out_f:
                        shutil.copyfileobj(r, out_f)
                # move into place
                os.replace(tmp_dest, MODEL_DEST)
            except Exception as e:
                _model_last_error = str(e)
            finally:
                _model_downloading = False

        t = threading.Thread(target=_download, daemon=True)
        t.start()
        resp['downloading'] = True
        return jsonify(resp)
    except Exception as e:
        _model_last_error = str(e)
        resp['last_error'] = _model_last_error
        return jsonify(resp), 500


@app.route('/api/landing-page', methods=['GET'])
def landing_page_endpoint():
    data = _load_json_file('landing-page.json')
    if data is None:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    return jsonify(data)


@app.route('/api/our-events', methods=['GET'])
def our_events_endpoint():
    data = _load_json_file('our-events.json')
    if data is None:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    return jsonify(data)


@app.route('/api/testimonials', methods=['GET'])
def testimonials_endpoint():
    data = _load_json_file('testimonials.json')
    if data is None:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    return jsonify(data)


# Vercel expects `app` to be the WSGI callable; keep `app` exported
if __name__ == '__main__':
    # local dev helper
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)


@app.route('/', methods=['GET'])
def root_index():
        """Simple root page so visiting the project root doesn't 404 on Vercel.

        Shows links to the API endpoints for quick manual checks.
        """
        html = '''
        <!doctype html>
        <html>
        <head><meta charset="utf-8"><title>ai-sepasangwp</title></head>
        <body>
            <h1>ai-sepasangwp backend</h1>
            <p>Available endpoints:</p>
            <ul>
                <li><a href="/api/health">/api/health</a></li>
                <li><a href="/api/model-status">/api/model-status</a></li>
                <li><a href="/api/process">/api/process</a> (POST)</li>
                <li><a href="/api/landing-page">/api/landing-page</a></li>
                <li><a href="/api/our-events">/api/our-events</a></li>
                <li><a href="/api/testimonials">/api/testimonials</a></li>
            </ul>
            <p>Note: this is a lightweight serverless backend; model inference may be a stub.</p>
        </body>
        </html>
        '''
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
