from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, Response
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static')
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'mov', 'avi', 'webm'}
MAX_UPLOAD_MB = 4096
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

os.makedirs(VIDEOS_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(filepath):
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def get_all_videos():
    videos = []
    for filename in os.listdir(VIDEOS_FOLDER):
        if allowed_file(filename):
            filepath = os.path.join(VIDEOS_FOLDER, filename)
            videos.append({
                'filename': filename,
                'title': os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' '),
                'size': get_file_size(filepath),
                'extension': filename.rsplit('.', 1)[1].upper(),
                'added': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d'),
            })
    videos.sort(key=lambda v: os.path.getctime(os.path.join(VIDEOS_FOLDER, v['filename'])), reverse=True)
    return videos


@app.route('/')
def index():
    videos = get_all_videos()
    return render_template('index.html', videos=videos)

@app.route('/watch/<filename>')
def watch(filename):
    filepath = os.path.join(VIDEOS_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return redirect(url_for('index'))
    video = {
        'filename': filename,
        'title': os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' '),
        'size': get_file_size(filepath),
        'extension': filename.rsplit('.', 1)[1].upper(),
    }
    return render_template('watch.html', video=video)

@app.route('/videos/<filename>')
def serve_video(filename):
    response = send_from_directory(VIDEOS_FOLDER, secure_filename(filename))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Range'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Disposition'] = 'inline'
    return response

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('.', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': f'File type not allowed. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(VIDEOS_FOLDER, filename))
    return jsonify({'success': True, 'filename': filename, 'message': f'"{filename}" uploaded successfully!'})

@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    filepath = os.path.join(VIDEOS_FOLDER, secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'File not found'}), 404

@app.route('/api/videos')
def api_videos():
    return jsonify(get_all_videos())

@app.route('/api/status')
def api_status():
    return jsonify({'status': 'online', 'video_count': len(get_all_videos())})


if __name__ == '__main__':
    print("\n🎬 VAULTSTREAM — http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
