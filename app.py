from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ─────────────────────────────────────────
# SETTINGS — change these if you want!
# ─────────────────────────────────────────
VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'mov', 'avi', 'webm'}
MAX_UPLOAD_MB = 4096  # 4 GB max upload
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Make sure the videos folder exists
os.makedirs(VIDEOS_FOLDER, exist_ok=True)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_size(filepath):
    """Return a human-readable file size like '1.2 GB' or '340 MB'."""
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_all_videos():
    """Scan the videos folder and return a list of video info dicts."""
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
    # Newest first
    videos.sort(key=lambda v: os.path.getctime(os.path.join(VIDEOS_FOLDER, v['filename'])), reverse=True)
    return videos


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    """Home page — show all videos."""
    videos = get_all_videos()
    return render_template('index.html', videos=videos)


@app.route('/watch/<filename>')
def watch(filename):
    """Video player page."""
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
    """Serve a video file from the videos folder."""
    return send_from_directory(VIDEOS_FOLDER, secure_filename(filename))


@app.route('/upload', methods=['POST'])
def upload():
    """Handle video file uploads."""
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': f'File type not allowed. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(VIDEOS_FOLDER, filename)
    file.save(save_path)

    return jsonify({'success': True, 'filename': filename, 'message': f'"{filename}" uploaded successfully!'})


@app.route('/delete/<filename>', methods=['POST'])
def delete(filename):
    """Delete a video file."""
    filepath = os.path.join(VIDEOS_FOLDER, secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'File not found'}), 404


@app.route('/api/videos')
def api_videos():
    """JSON API — returns all videos (useful for future features)."""
    return jsonify(get_all_videos())


@app.route('/api/status')
def api_status():
    """Server status check."""
    return jsonify({
        'status': 'online',
        'mode': 'local',
        'video_count': len(get_all_videos()),
        'videos_folder': VIDEOS_FOLDER,
    })


# ─────────────────────────────────────────
# START THE SERVER
# ─────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  🎬 VAULTSTREAM — Local Video Platform")
    print("="*50)
    print(f"  Videos folder: {VIDEOS_FOLDER}")
    print(f"  Open your browser and go to:")
    print(f"  👉  http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
