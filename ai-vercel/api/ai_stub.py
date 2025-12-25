import re
import json
import os
import csv
from typing import List, Dict

INTENT_LIST = [
    "cari_rekomendasi_paket","estimasi_budget","cari_venue","tanya_kemungkinan","cari_dekor","cari_vendor","cari_catering"
]

_initialized = False
_dataset_rows: List[Dict] = []
_vocab: Dict[str, int] = {}
_doc_vectors: List[List[int]] = []
_clusters: Dict[int, List[int]] = {}
_centroids: List[List[float]] = []
_sk_model = None
_sk_model_loaded = False

def ensure_initialized(sync=True):
    global _initialized
    if _initialized:
        return True
    # lightweight init: load intent labels if present
    # try to load dataset_pertanyaan_wedding.csv to improve matching
    try:
        candidates = [
            os.path.join(os.path.dirname(__file__), 'data', 'dataset_pertanyaan_wedding.csv'),
            os.path.join(os.path.dirname(__file__), '..', 'dataset_pertanyaan_wedding.csv'),
            os.path.join(os.getcwd(), 'dataset_pertanyaan_wedding.csv'),
        ]
        for p in candidates:
            if p and os.path.exists(p):
                with open(p, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        text = (r.get('text') or '').strip()
                        if not text:
                            continue
                        norm = re.sub(r'[^0-9a-zA-Z\s]', ' ', text.lower()).strip()
                        tokens = [t for t in norm.split() if t]
                        r['_norm'] = norm
                        r['_tokens'] = tokens
                        _dataset_rows.append(r)
                break
        # build simple vocabulary and document count vectors
        if _dataset_rows:
            vocab = {}
            vectors = []
            for i, r in enumerate(_dataset_rows):
                counts = {}
                for t in r.get('_tokens', []):
                    counts[t] = counts.get(t, 0) + 1
                for t in counts:
                    if t not in vocab:
                        vocab[t] = len(vocab)
                # create vector later after vocab complete
                vectors.append(counts)
            # finalize vectors with fixed vocab size
            V = len(vocab)
            docvecs = []
            for counts in vectors:
                vec = [0] * V
                for t, c in counts.items():
                    vec[vocab[t]] = c
                docvecs.append(vec)
            _vocab.update(vocab)
            _doc_vectors.extend(docvecs)
            # train lightweight k-means to cluster similar questions
            try:
                def _train_kmeans(docvecs, k=8, iters=40, seed=42):
                    import random
                    random.seed(seed)
                    n = len(docvecs)
                    if n == 0:
                        return {}, []
                    k = min(k, n)
                    # initialize centroids by random sampling
                    centroids = [list(map(float, docvecs[i])) for i in random.sample(range(n), k)]
                    for _ in range(iters):
                        clusters = {i: [] for i in range(len(centroids))}
                        # assign
                        for idx, v in enumerate(docvecs):
                            best_i = 0
                            best_d = None
                            for ci, c in enumerate(centroids):
                                # squared euclidean
                                d = 0.0
                                for a, b in zip(v, c):
                                    diff = a - b
                                    d += diff * diff
                                if best_d is None or d < best_d:
                                    best_d = d
                                    best_i = ci
                            clusters[best_i].append(idx)
                        # recompute centroids
                        changed = False
                        for ci in range(len(centroids)):
                            members = clusters[ci]
                            if not members:
                                continue
                            newc = [0.0] * len(centroids[ci])
                            for m in members:
                                mv = docvecs[m]
                                for j in range(len(newc)):
                                    newc[j] += mv[j]
                            inv = 1.0 / len(members)
                            for j in range(len(newc)):
                                newc[j] *= inv
                            centroids[ci] = newc
                        # no explicit convergence check to keep simple
                    return clusters, centroids
                clusters, centroids = _train_kmeans(_doc_vectors, k=min(12, max(2, int(len(_doc_vectors)**0.5))))
                # map cluster member indices from local docvec indices to dataset row indices
                # local docvec index i corresponds to dataset row index i (we appended in same order)
                _clusters.clear()
                for ci, members in clusters.items():
                    _clusters[ci] = members[:]  # indices in _dataset_rows
                _centroids.clear()
                _centroids.extend(centroids)
            except Exception:
                # if clustering fails, leave clusters empty
                _clusters.clear()
                _centroids.clear()
        # attempt to load a saved sklearn joblib model (TF-IDF + LogisticRegression) from common locations
        try:
            # import joblib lazily so a missing dependency doesn't crash module import
            try:
                import joblib
            except Exception:
                joblib = None
            global _sk_model, _sk_model_loaded
            candidate_model_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'models', 'intent_tfidf_logreg.joblib'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'intent_tfidf_logreg.joblib'),
                os.path.join(os.getcwd(), 'models', 'intent_tfidf_logreg.joblib'),
            ]
            if joblib is not None:
                for mp in candidate_model_paths:
                    if mp and os.path.exists(mp):
                        try:
                            _sk_model = joblib.load(mp)
                            _sk_model_loaded = True
                            break
                        except Exception:
                            _sk_model = None
                            _sk_model_loaded = False
            else:
                _sk_model = None
                _sk_model_loaded = False
        except Exception:
            _sk_model = None
            _sk_model_loaded = False
    except Exception:
        pass
    _initialized = True
    return True

def extract_slots_by_rule(text: str):
    lower = text.lower()
    slots = {
        "tema": None,
        "lokasi": None,
        "budget_min": None,
        "budget_max": None,
        "jumlah_tamu": None,
        "tipe_acara": None,
        "venue": None,
        "waktu": None,
    }
    # simple tema & lokasi (support multiple locations joined by 'dan', 'atau', ',', '&')
    city_candidates = ["bandung","jakarta","bali","surabaya","yogyakarta","bogor","bekasi","bogor","malang","makassar","padang","garut","cirebon","depok","semarang","solo","tasikmalaya","medan","puncak","pekanbaru"]
    found = []
    for k in city_candidates:
        if k in lower:
            found.append(k)
    if found:
        # keep order and unique
        uniq = []
        for c in found:
            if c not in uniq:
                uniq.append(c)
        if len(uniq) == 1:
            slots['lokasi'] = uniq[0]
        else:
            slots['lokasi'] = uniq
    # budget — support variants like '500juta', '500 jt', '50 juta', '30-40 juta'
    try:
        budget_matches = re.findall(r"(\d+(?:[\.,]\d+)?)\s*(?:juta|jt)\b", lower)
        if budget_matches:
            amounts = []
            for x in budget_matches:
                x2 = x.replace(',', '.').strip()
                try:
                    v = float(x2)
                    amounts.append(int(v * 1_000_000))
                except Exception:
                    try:
                        amounts.append(int(int(x2) * 1_000_000))
                    except Exception:
                        pass
            if amounts:
                slots["budget_min"] = min(amounts)
                slots["budget_max"] = max(amounts)
        else:
            # also support thousands/ribu forms like '30rb' or '30 ribu'
            small_matches = re.findall(r"(\d+)\s*(?:ribu|rb)\b", lower)
            if small_matches:
                amounts = [int(x) * 1_000 for x in small_matches]
                slots["budget_min"] = min(amounts)
                slots["budget_max"] = max(amounts)
    except Exception:
        pass

    # jumlah tamu — only capture when units like 'orang', 'tamu', or 'pax' are present
    try:
        m2 = re.search(r"(?:untuk|buat|kapasitas)?\s*(\d{1,5})\s*(orang|tamu|pax)\b", lower)
        if m2:
            n = m2.group(1).replace('.', '').replace(',', '')
            try:
                val = int(n)
                # sanity check: treat plausible guest counts only
                if 0 < val <= 5000:
                    slots["jumlah_tamu"] = val
            except Exception:
                pass
    except Exception:
        pass
    return slots

def predict(text: str):
    # naive keyword-based intent detection
    lower = text.lower()
    # try dataset matching first (token overlap / simple fuzzy)
    try:
        # normalize numeric forms like '500juta' or '500jt' -> '500 juta'
        pre = text.lower()
        pre = re.sub(r"(\d+)\s*jt\b", r"\1 juta", pre)
        pre = re.sub(r"(\d+)juta\b", r"\1 juta", pre)
        norm = re.sub(r'[^0-9a-zA-Z\s]', ' ', pre).strip()
        tokens = set([t for t in norm.split() if t])
        # build quick vector for query (same vocab)
        qvec = None
        if _vocab:
            qvec = [0] * len(_vocab)
            for t in tokens:
                if t in _vocab:
                    qvec[_vocab[t]] += 1
        # If a trained sklearn intent model is available, use it first
        try:
            global _sk_model, _sk_model_loaded
            if _sk_model_loaded and _sk_model is not None:
                try:
                    pred_label = _sk_model.predict([text])[0]
                    probs = {}
                    try:
                        proba = _sk_model.predict_proba([text])[0]
                        classes = list(_sk_model.classes_)
                        probs = {str(c): float(p) for c, p in zip(classes, proba)}
                    except Exception:
                        probs = {str(pred_label): 1.0}
                    # extract user slots and fill missing from best dataset match (if available)
                    slots = extract_slots_by_rule(text) or {}
                    # quick best-match search to fill missing slots (non-destructive)
                    best2 = None
                    best_score2 = 0.0
                    for idx in range(len(_dataset_rows)):
                        r = _dataset_rows[idx]
                        rtoks = set(r.get('_tokens', []))
                        if not rtoks:
                            continue
                        inter = tokens.intersection(rtoks)
                        union = tokens.union(rtoks)
                        score = len(inter) / (len(union) or 1)
                        if score > best_score2:
                            best_score2 = score
                            best2 = r
                    if best2 and best_score2 >= 0.25:
                        for k in ('tema', 'lokasi', 'budget_min', 'budget_max', 'jumlah_tamu', 'tipe_acara', 'venue', 'waktu'):
                            if (slots.get(k) is None or slots.get(k) == []) and best2.get(k):
                                try:
                                    if k in ('budget_min', 'budget_max', 'jumlah_tamu') and best2.get(k):
                                        slots[k] = int(best2.get(k))
                                    else:
                                        slots[k] = best2.get(k)
                                except Exception:
                                    slots[k] = best2.get(k)
                    return {
                        'text': text,
                        'intent_pred': str(pred_label),
                        'probs': probs,
                        'slots': slots,
                        'overridden': False,
                        'override_reason': 'model_pred',
                    }
                except Exception:
                    # on model failure, fall back to dataset matching below
                    pass
        except Exception:
            pass
        best = None
        best_score = 0.0
        # choose which rows to compare: nearest cluster if available
        candidate_rows = list(range(len(_dataset_rows)))
        try:
            if qvec is not None and _centroids:
                # find nearest centroid
                best_ci = None
                best_d = None
                for ci, c in enumerate(_centroids):
                    # compute squared euclidean but only up to min(len(qvec), len(c))
                    d = 0.0
                    for a, b in zip(qvec, c):
                        diff = a - b
                        d += diff * diff
                    if best_d is None or d < best_d:
                        best_d = d
                        best_ci = ci
                if best_ci is not None and _clusters.get(best_ci):
                    candidate_rows = _clusters.get(best_ci)
        except Exception:
            candidate_rows = list(range(len(_dataset_rows)))

        for idx in candidate_rows:
            r = _dataset_rows[idx]
            rtoks = set(r.get('_tokens', []))
            if not rtoks:
                continue
            inter = tokens.intersection(rtoks)
            union = tokens.union(rtoks)
            score = len(inter) / (len(union) or 1)
            if score > best_score:
                best_score = score
                best = r
        # if sufficiently similar, use dataset intent and populate slots
        # lower threshold to accept more fuzzy matches from the dataset
        if best and best_score >= 0.25:
            slots = {
                'tema': best.get('tema') or None,
                'lokasi': best.get('lokasi') or None,
                'budget_min': int(best['budget_min']) if best.get('budget_min') else None,
                'budget_max': int(best['budget_max']) if best.get('budget_max') else None,
                'jumlah_tamu': int(best['jumlah_tamu']) if best.get('jumlah_tamu') else None,
                'tipe_acara': best.get('tipe_acara') or None,
                'venue': best.get('venue') or None,
                'waktu': best.get('waktu') or None,
            }
            # prefer slots explicitly present in the user's text (don't overwrite user-provided values)
            user_slots = {}
            try:
                user_slots = extract_slots_by_rule(text) or {}
                for k, v in user_slots.items():
                    if v is not None:
                        slots[k] = v
            except Exception:
                user_slots = {}
            # if user did NOT specify guest count explicitly, don't force a dataset-provided guest count
            try:
                if user_slots.get('jumlah_tamu') is None:
                    slots['jumlah_tamu'] = None
            except Exception:
                pass
            return {
                'text': text,
                'intent_pred': best.get('intent') or 'cari_rekomendasi_paket',
                'probs': {best.get('intent') or 'cari_rekomendasi_paket': 1.0},
                'slots': slots,
                'overridden': True,
                'override_reason': f'matched_dataset:{best_score:.2f}',
            }
    except Exception:
        pass
    probs = {lbl: 0.0 for lbl in INTENT_LIST}
    intent = 'cari_rekomendasi_paket'
    if any(w in lower for w in ['berapa','estimasi','estimasi budget','budget']):
        intent = 'estimasi_budget'
    elif any(w in lower for w in ['venue','tempat','lokasi']):
        intent = 'cari_venue'
    elif any(w in lower for w in ['dekor','dekorasi']):
        intent = 'cari_dekor'
    elif any(w in lower for w in ['vendor','penyedia']):
        intent = 'cari_vendor'
    elif any(w in lower for w in ['catering','makanan','menu']):
        intent = 'cari_catering'
    elif any(w in lower for w in ['apa','apakah','berapakah','bisa']):
        intent = 'tanya_kemungkinan'
    probs[intent] = 1.0
    slots = extract_slots_by_rule(text)
    return {
        'text': text,
        'intent_pred': intent,
        'probs': probs,
        'slots': slots,
        'overridden': False,
        'override_reason': None,
    }
