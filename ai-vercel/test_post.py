import json
import urllib.request

url = 'http://127.0.0.1:5000/api/process'
payload = {'text': 'cari catering di bandung budget 20 juta'}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=30) as f:
        print(f.read().decode())
except Exception as e:
    print('ERROR', e)
    raise
