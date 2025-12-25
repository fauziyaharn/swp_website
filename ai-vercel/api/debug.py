from flask import Flask, jsonify
import sys, os

app = Flask(__name__)

@app.route('/api/debug', methods=['GET'])
def debug():
    try:
        info = {
            'python_version': sys.version,
            'cwd': os.getcwd(),
            'listdir': os.listdir('.'),
            'env_sample': {k: os.environ.get(k) for k in ['VERCEL', 'VERCEL_ENV', 'VERCEL_URL', 'PATH']}
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)
