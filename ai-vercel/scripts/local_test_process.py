from api import ai_stub
import json, os, random

text = 'butuh paket akad saja tema sunda di bandung untuk 50 orang budget 15 juta'
ai_result = ai_stub.predict(text)
slots = ai_result.get('slots') or {}
# replicate process logic (budget safe int)
def _safe_int(v):
    try:
        if v is None:
            return None
        iv = int(v)
        return iv if iv > 0 else None
    except Exception:   
        return None

bmin_slot = _safe_int(slots.get('budget_min'))
bmax_slot = _safe_int(slots.get('budget_max'))
if bmin_slot is None and bmax_slot is not None:
    bmin = max(1_000_000, int(bmax_slot * 0.5))
else:
    bmin = bmin_slot if bmin_slot is not None else 5_000_000
bmax = bmax_slot if bmax_slot is not None else 20_000_000

vendors_path = os.path.join(os.path.dirname(__file__), '..', 'api', 'data', 'vendors.json')
with open(vendors_path, 'r', encoding='utf-8') as f:
    vendors_data = json.load(f)

wo_list = vendors_data.get('wo') or []
mua_list = vendors_data.get('mua') or []
decor_list = vendors_data.get('decoration') or vendors_data.get('decor') or []
doc_list = vendors_data.get('documentation') or []
entert_list = vendors_data.get('entertainment') or []
catering_list = vendors_data.get('catering') or []

def _normalize(lst):
    out = []
    for item in lst:
        if isinstance(item, dict):
            out.append({'name': item.get('name'), 'url': item.get('url'), 'image': item.get('image'), 'contact': item.get('contact')})
        else:
            out.append({'name': item, 'url': None, 'image': None, 'contact': None})
    return out

wo_list = _normalize(wo_list)
M = len(wo_list)

# shuffle
random.shuffle(wo_list)
random.shuffle(mua_list)
random.shuffle(decor_list)
random.shuffle(doc_list)
random.shuffle(entert_list)
random.shuffle(catering_list)

locations = slots.get('lokasi') if isinstance(slots.get('lokasi'), list) else [slots.get('lokasi') or 'Bandung']

# sample budgets
seen = set()
recs = []
for loc in locations:
    desired_per_location = min(8, max(1, len(wo_list), len(mua_list), len(decor_list), len(doc_list), len(entert_list), len(catering_list)))
    attempts = 0
    created = 0
    while created < desired_per_location and attempts < desired_per_location * 6:
        attempts += 1
        wo_item = random.choice(wo_list)
        mua_item = random.choice(_normalize(mua_list)) if mua_list else {'name': None, 'url': None, 'image': None, 'contact': None}
        decor_item = random.choice(_normalize(decor_list)) if decor_list else {'name': None, 'url': None, 'image': None, 'contact': None}
        catering_item = random.choice(_normalize(catering_list)) if catering_list else {'name': None, 'url': None, 'image': None, 'contact': None}
        key = (wo_item.get('name'), mua_item.get('name'), decor_item.get('name'), catering_item.get('name'))
        if key in seen:
            continue
        seen.add(key)
        def _sample_budget(bmin_val, bmax_val):
            try:
                if bmin_val is None and bmax_val is None:
                    return None, None
                if bmin_val is None:
                    bmin_val = int(max(1_000_000, int(bmax_val * 0.5)))
                if bmax_val is None:
                    bmax_val = int(max(bmin_val, 20_000_000))
                if bmin_val == bmax_val:
                    low = int(bmin_val * 0.85)
                    high = int(bmax_val * 1.15)
                else:
                    low = max(1, int(bmin_val * random.uniform(0.8, 1.05)))
                    high = int(bmax_val * random.uniform(0.95, 1.25))
                if low > high:
                    low, high = high, low
                return int(low), int(high)
            except Exception as e:
                print('budget sample error', e)
                return bmin_val, bmax_val
        lbmin, lbmax = _sample_budget(bmin, bmax)
        recs.append({'wo': wo_item.get('name'), 'lokasi': loc, 'budget_min': lbmin, 'budget_max': lbmax})
        created += 1

import pprint
pprint.pprint({'slots': slots, 'sample_recs': recs})
