from api import process
app = process.app
with app.test_client() as client:
    resp = client.post('/api/process', json={'text':'butuh paket akad saja tema sunda di bandung untuk 50 orang budget 15 juta'})
    print('status', resp.status_code)
    print(resp.get_data(as_text=True))
