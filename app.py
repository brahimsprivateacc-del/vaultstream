from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, session
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import json

app = Flask(__name__)
app.secret_key = 'vaultstream-secret-change-this-later'

VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'mov', 'avi', 'webm'}
MAX_UPLOAD_MB = 4096
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://wweckerzweqjrrrbqysq.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_publishable_cxxK6Id-_Ttl18yWep2oNQ_BgO2rghG')

os.makedirs(VIDEOS_FOLDER, exist_ok=True)

def supabase_headers(token=None):
    h = {'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'}
    if token:
        h['Authorization'] = f'Bearer {token}'
    else:
        h['Authorization'] = f'Bearer {SUPABASE_KEY}'
    return h

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(filepath):
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def get_current_user():
    return session.get('user')

# ── ROUTES ──

@app.route('/')
def index():
    user = get_current_user()
    # Get all videos from Supabase
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username,avatar_url)&order=created_at.desc',
        headers=supabase_headers()
    )
    videos = r.json() if r.ok else []
    return render_template('index.html', videos=videos, user=user)

@app.route('/watch/<video_id>')
def watch(video_id):
    user = get_current_user()
    # Get video info
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&select=*,profiles(username,avatar_url)',
        headers=supabase_headers()
    )
    videos = r.json()
    if not videos:
        return redirect(url_for('index'))
    video = videos[0]

    # Get comments
    r2 = requests.get(
        f'{SUPABASE_URL}/rest/v1/comments?video_id=eq.{video_id}&select=*,profiles(username)&order=created_at.asc',
        headers=supabase_headers()
    )
    comments = r2.json() if r2.ok else []

    # Get like count
    r3 = requests.get(
        f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&select=id',
        headers=supabase_headers()
    )
    likes = len(r3.json()) if r3.ok else 0

    # Check if user liked
    user_liked = False
    if user:
        r4 = requests.get(
            f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}',
            headers=supabase_headers()
        )
        user_liked = len(r4.json()) > 0 if r4.ok else False

    return render_template('watch.html', video=video, comments=comments, likes=likes, user=user, user_liked=user_liked)

@app.route('/videos/<filename>')
def serve_video(filename):
    response = send_from_directory(VIDEOS_FOLDER, secure_filename(filename))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Disposition'] = 'inline'
    return response

@app.route('/profile/<username>')
def profile(username):
    user = get_current_user()
    # Get profile
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/profiles?username=eq.{username}&select=*',
        headers=supabase_headers()
    )
    profiles = r.json()
    if not profiles:
        return redirect(url_for('index'))
    profile_user = profiles[0]

    # Get their videos
    r2 = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?user_id=eq.{profile_user["id"]}&order=created_at.desc',
        headers=supabase_headers()
    )
    user_videos = r2.json() if r2.ok else []
    return render_template('profile.html', profile_user=profile_user, videos=user_videos, user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')

        # Sign up with Supabase Auth
        r = requests.post(
            f'{SUPABASE_URL}/auth/v1/signup',
            headers=supabase_headers(),
            json={'email': email, 'password': password}
        )
        data = r.json()
        if r.ok and data.get('user'):
            user_id = data['user']['id']
            token = data.get('access_token')
            # Create profile
            requests.post(
                f'{SUPABASE_URL}/rest/v1/profiles',
                headers=supabase_headers(token),
                json={'id': user_id, 'username': username}
            )
            session['user'] = {'id': user_id, 'username': username, 'token': token}
            return redirect(url_for('index'))
        else:
            error = data.get('msg') or data.get('error_description') or 'Signup failed'
            return render_template('signup.html', error=error)
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        r = requests.post(
            f'{SUPABASE_URL}/auth/v1/token?grant_type=password',
            headers=supabase_headers(),
            json={'email': email, 'password': password}
        )
        data = r.json()
        if r.ok and data.get('access_token'):
            user_id = data['user']['id']
            token = data['access_token']
            # Get profile
            r2 = requests.get(
                f'{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}',
                headers=supabase_headers(token)
            )
            profiles = r2.json()
            username = profiles[0]['username'] if profiles else email
            session['user'] = {'id': user_id, 'username': username, 'token': token}
            return redirect(url_for('index'))
        else:
            error = data.get('error_description') or 'Invalid email or password'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Please log in to upload'}), 401
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    file = request.files['video']
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(VIDEOS_FOLDER, filename)
    file.save(filepath)

    title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
    ext = filename.rsplit('.', 1)[1].upper()
    size = get_file_size(filepath)

    # Save to Supabase
    requests.post(
        f'{SUPABASE_URL}/rest/v1/videos',
        headers=supabase_headers(user['token']),
        json={'user_id': user['id'], 'filename': filename, 'title': title, 'size': size, 'extension': ext}
    )
    return jsonify({'success': True, 'message': f'"{filename}" uploaded!'})

@app.route('/like/<video_id>', methods=['POST'])
def like(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    # Check if already liked
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}',
        headers=supabase_headers()
    )
    if r.json():
        # Unlike
        requests.delete(
            f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}',
            headers=supabase_headers(user['token'])
        )
        liked = False
    else:
        # Like
        requests.post(
            f'{SUPABASE_URL}/rest/v1/likes',
            headers=supabase_headers(user['token']),
            json={'user_id': user['id'], 'video_id': video_id}
        )
        liked = True
    # Get new count
    r2 = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}', headers=supabase_headers())
    count = len(r2.json()) if r2.ok else 0
    return jsonify({'success': True, 'liked': liked, 'count': count})

@app.route('/comment/<video_id>', methods=['POST'])
def comment(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    content = request.json.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'error': 'Comment cannot be empty'}), 400
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/comments',
        headers={**supabase_headers(user['token']), 'Prefer': 'return=representation'},
        json={'user_id': user['id'], 'video_id': video_id, 'content': content}
    )
    return jsonify({'success': True, 'username': user['username'], 'content': content})

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('.', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    file = request.files['avatar']
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in {'jpg', 'jpeg', 'png', 'gif', 'webp'}:
        return jsonify({'success': False, 'error': 'Invalid image type'}), 400

    # Upload to Supabase Storage
    filename = f"{user['id']}.{ext}"
    file_data = file.read()
    r = requests.put(
        f"{SUPABASE_URL}/storage/v1/object/avatars/{filename}",
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f"Bearer {user['token']}",
            'Content-Type': f'image/{ext}',
            'x-upsert': 'true'
        },
        data=file_data
    )
    if r.ok:
        avatar_url = f"{SUPABASE_URL}/storage/v1/object/public/avatars/{filename}"
        # Update profile
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}",
            headers=supabase_headers(user['token']),
            json={'avatar_url': avatar_url}
        )
        return jsonify({'success': True, 'url': avatar_url})
    return jsonify({'success': False, 'error': 'Upload failed'}), 500

if __name__ == '__main__':
    print("\n🎬 VAULTSTREAM — http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
