from api import ai_stub
import json
print('init', ai_stub.ensure_initialized())
res = ai_stub.predict('butuh paket akad saja tema sunda di bandung untuk 50 orang budget 15 juta')
print(json.dumps(res, indent=2, ensure_ascii=False))
