from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, session
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.secret_key = 'vaultstream-secret-change-this-later'

VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'mov', 'avi', 'webm'}
MAX_UPLOAD_MB = 4096
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://wweckerzweqjrrrbqysq.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_publishable_cxxK6Id-_Ttl18yWep2oNQ_BgO2rghG')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind3ZWNrZXJ6d2VxanJycmJxeXNxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjgyNTg5NSwiZXhwIjoyMDg4NDAxODk1fQ.6ZOMljwV5qt7mPPjn_6kpxaQHlt44J89Xdm2eeHET4g')

# Cloudinary config
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', 'dkym11l9b'),
    api_key = os.environ.get('CLOUDINARY_API_KEY', '372954551797955'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', 'l7p9Qa1jY5yJcK_kv4_jJFbIkdo')
)

os.makedirs(VIDEOS_FOLDER, exist_ok=True)

def supabase_headers(token=None):
    h = {'apikey': SUPABASE_KEY, 'Content-Type': 'application/json'}
    h['Authorization'] = f'Bearer {token}' if token else f'Bearer {SUPABASE_KEY}'
    return h

def supabase_service_headers():
    return {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def get_current_user():
    return session.get('user')

# ── ROUTES ──

@app.route('/')
def index():
    user = get_current_user()
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username,avatar_url)&order=created_at.desc',
        headers=supabase_headers()
    )
    videos = r.json() if r.ok else []
    # Get live streams
    r2 = requests.get(
        f'{SUPABASE_URL}/rest/v1/streams?is_live=eq.true&select=*,profiles(username)&order=created_at.desc',
        headers=supabase_service_headers()
    )
    live_streams = r2.json() if r2.ok else []
    return render_template('index.html', videos=videos, user=user, live_streams=live_streams)

@app.route('/watch/<video_id>')
def watch(video_id):
    user = get_current_user()
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&select=*,profiles(username,avatar_url)',
        headers=supabase_headers()
    )
    videos = r.json()
    if not videos:
        return redirect(url_for('index'))
    video = videos[0]

    r2 = requests.get(
        f'{SUPABASE_URL}/rest/v1/comments?video_id=eq.{video_id}&select=*,profiles(username)&order=created_at.asc',
        headers=supabase_headers()
    )
    comments = r2.json() if r2.ok else []

    r3 = requests.get(
        f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&select=id',
        headers=supabase_headers()
    )
    likes = len(r3.json()) if r3.ok else 0

    user_liked = False
    if user:
        r4 = requests.get(
            f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}',
            headers=supabase_headers()
        )
        user_liked = len(r4.json()) > 0 if r4.ok else False

    # Increment view count
    requests.post(
        f'{SUPABASE_URL}/rpc/increment_views',
        headers=supabase_service_headers(),
        json={'video_id': video_id}
    )

    return render_template('watch.html', video=video, comments=comments, likes=likes, user=user, user_liked=user_liked)

@app.route('/profile/<username>')
def profile(username):
    user = get_current_user()
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/profiles?username=eq.{username}&select=*',
        headers=supabase_headers()
    )
    profiles = r.json()
    if not profiles:
        return redirect(url_for('index'))
    profile_user = profiles[0]
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
        r = requests.post(
            f'{SUPABASE_URL}/auth/v1/signup',
            headers=supabase_headers(),
            json={'email': email, 'password': password}
        )
        data = r.json()
        if r.ok and data.get('user'):
            user_id = data['user']['id']
            token = data.get('access_token')
            requests.post(
                f'{SUPABASE_URL}/rest/v1/profiles',
                headers=supabase_headers(token),
                json={'id': user_id, 'username': username}
            )
            session.permanent = True
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
    ext = filename.rsplit('.', 1)[1].upper()
    default_title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
    title = request.form.get('title', '').strip() or default_title
    category = request.form.get('category', 'general')

    # Upload to Cloudinary
    result = cloudinary.uploader.upload(
        file,
        resource_type='video',
        folder='vaultstream',
        public_id=os.path.splitext(filename)[0],
        overwrite=True
    )

    video_url = result.get('secure_url')
    thumbnail_url = result.get('secure_url', '').replace('/upload/', '/upload/so_0,w_400,h_225,c_fill/')
    # Make proper thumbnail
    thumbnail_url = result.get('secure_url', '').rsplit('.', 1)[0].replace('/video/upload/', '/video/upload/so_0,w_400,h_225,c_fill/') + '.jpg'
    size = get_file_size(result.get('bytes', 0))

    # Save to Supabase using service key
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/videos',
        headers=supabase_service_headers(),
        json={
            'user_id': user['id'],
            'filename': filename,
            'title': title,
            'size': size,
            'extension': ext,
            'video_url': video_url,
            'thumbnail_url': thumbnail_url,
            'category': category
        }
    )
    return jsonify({'success': True, 'message': f'"{title}" uploaded!'})

@app.route('/videos/<filename>')
def serve_video(filename):
    response = send_from_directory(VIDEOS_FOLDER, secure_filename(filename))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Disposition'] = 'inline'
    return response

@app.route('/like/<video_id>', methods=['POST'])
def like(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}',
        headers=supabase_headers()
    )
    if r.json():
        requests.delete(
            f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}',
            headers=supabase_headers(user['token'])
        )
        liked = False
    else:
        requests.post(
            f'{SUPABASE_URL}/rest/v1/likes',
            headers=supabase_headers(user['token']),
            json={'user_id': user['id'], 'video_id': video_id}
        )
        liked = True
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
        return jsonify({'success': False, 'error': 'Empty comment'}), 400
    requests.post(
        f'{SUPABASE_URL}/rest/v1/comments',
        headers={**supabase_headers(user['token']), 'Prefer': 'return=representation'},
        json={'user_id': user['id'], 'video_id': video_id, 'content': content}
    )
    return jsonify({'success': True, 'username': user['username'], 'content': content})

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    file = request.files['avatar']
    result = cloudinary.uploader.upload(
        file,
        folder='vaultstream/avatars',
        public_id=user['id'],
        overwrite=True,
        transformation=[{'width': 200, 'height': 200, 'crop': 'fill', 'gravity': 'face'}]
    )
    avatar_url = result.get('secure_url')
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}",
        headers=supabase_headers(user['token']),
        json={'avatar_url': avatar_url}
    )
    return jsonify({'success': True, 'url': avatar_url})

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('.', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response



@app.route('/trending')
def trending():
    user = get_current_user()
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username)&order=views.desc',
        headers=supabase_headers()
    )
    videos = r.json() if r.ok else []
    return render_template('trending.html', videos=videos, user=user)

@app.route('/settings')
def settings():
    user = get_current_user()
    return render_template('settings.html', user=user)

@app.route('/about')
def about():
    user = get_current_user()
    return render_template('about.html', user=user)


@app.route('/update_bio', methods=['POST'])
def update_bio():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    bio = request.json.get('bio', '').strip()
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}",
        headers=supabase_service_headers(),
        json={'bio': bio}
    )
    return jsonify({'success': True})


@app.route('/delete_video/<video_id>', methods=['POST'])
def delete_video(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    # Check ownership
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&user_id=eq.{user["id"]}',
        headers=supabase_service_headers()
    )
    if not r.json():
        return jsonify({'success': False, 'error': 'Not your video'}), 403
    # Delete from Supabase
    requests.delete(
        f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}',
        headers=supabase_service_headers()
    )
    return jsonify({'success': True})


@app.route('/search')
def search():
    user = get_current_user()
    q = request.args.get('q', '').strip()
    videos = []
    if q:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username)&title=ilike.*{q}*&order=views.desc',
            headers=supabase_headers()
        )
        videos = r.json() if r.ok else []
    return render_template('search.html', videos=videos, query=q, user=user)


@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    # Get user's videos with like and comment counts
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?user_id=eq.{user["id"]}&order=views.desc',
        headers=supabase_service_headers()
    )
    videos = r.json() if r.ok else []

    # Get like counts per video
    for video in videos:
        r2 = requests.get(
            f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video["id"]}',
            headers=supabase_service_headers()
        )
        video['like_count'] = len(r2.json()) if r2.ok else 0

        r3 = requests.get(
            f'{SUPABASE_URL}/rest/v1/comments?video_id=eq.{video["id"]}',
            headers=supabase_service_headers()
        )
        video['comment_count'] = len(r3.json()) if r3.ok else 0

    total_views = sum(v.get('views') or 0 for v in videos)
    total_likes = sum(v.get('like_count') or 0 for v in videos)
    total_comments = sum(v.get('comment_count') or 0 for v in videos)

    return render_template('dashboard.html',
        user=user,
        videos=videos,
        total_views=total_views,
        total_likes=total_likes,
        total_comments=total_comments
    )


@app.route('/update_title/<video_id>', methods=['POST'])
def update_title(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    title = request.json.get('title', '').strip()
    if not title:
        return jsonify({'success': False, 'error': 'Title cannot be empty'}), 400
    # Check ownership
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&user_id=eq.{user["id"]}',
        headers=supabase_service_headers()
    )
    if not r.json():
        return jsonify({'success': False, 'error': 'Not your video'}), 403
    requests.patch(
        f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}',
        headers=supabase_service_headers(),
        json={'title': title}
    )
    return jsonify({'success': True})



@app.route('/privacy')
def privacy():
    user = get_current_user()
    return render_template('privacy.html', user=user)

@app.route('/terms')
def terms():
    user = get_current_user()
    return render_template('terms.html', user=user)


@app.route('/ads.txt')
def ads_txt():
    return send_from_directory('.', 'ads.txt', mimetype='text/plain')


@app.route('/live')
def live():
    user = get_current_user()
    return render_template('live.html', user=user, supabase_url=SUPABASE_URL, supabase_key=SUPABASE_KEY)

@app.route('/start_stream', methods=['POST'])
def start_stream():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    title = request.json.get('title', 'Live Stream')
    # End any existing streams by this user
    requests.patch(
        f'{SUPABASE_URL}/rest/v1/streams?user_id=eq.{user["id"]}',
        headers=supabase_service_headers(),
        json={'is_live': False}
    )
    # Create new stream
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/streams',
        headers=supabase_service_headers(),
        json={'user_id': user['id'], 'title': title, 'is_live': True, 'viewer_count': 0}
    )
    data = r.json()
    stream_id = data[0]['id'] if isinstance(data, list) and data else None
    return jsonify({'success': True, 'stream_id': stream_id})

@app.route('/end_stream/<stream_id>', methods=['POST'])
def end_stream(stream_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False}), 401
    requests.patch(
        f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}&user_id=eq.{user["id"]}',
        headers=supabase_service_headers(),
        json={'is_live': False}
    )
    return jsonify({'success': True})

@app.route('/watch_live/<stream_id>')
def watch_live(stream_id):
    user = get_current_user()
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}',
        headers=supabase_service_headers()
    )
    streams = r.json()
    if not streams:
        return redirect(url_for('index'))
    return render_template('watch_live.html', stream=streams[0], user=user)

@app.route('/join_stream/<stream_id>', methods=['POST'])
def join_stream(stream_id):
    requests.rpc if False else None
    requests.post(
        f'{SUPABASE_URL}/rest/v1/rpc/increment_viewers',
        headers=supabase_service_headers(),
        json={'stream_id': stream_id}
    )
    return jsonify({'success': True})

@app.route('/leave_stream/<stream_id>', methods=['POST'])
def leave_stream(stream_id):
    requests.post(
        f'{SUPABASE_URL}/rest/v1/rpc/decrement_viewers',
        headers=supabase_service_headers(),
        json={'stream_id': stream_id}
    )
    return jsonify({'success': True})

@app.route('/stream_viewers/<stream_id>')
def stream_viewers(stream_id):
    r = requests.get(
        f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}&select=viewer_count,is_live,peer_id',
        headers=supabase_service_headers()
    )
    data = r.json()
    if data:
        return jsonify({'count': data[0]['viewer_count'], 'is_live': data[0]['is_live'], 'peer_id': data[0].get('peer_id')})
    return jsonify({'count': 0, 'is_live': False})


@app.route('/update_viewers/<stream_id>', methods=['POST'])
def update_viewers(stream_id):
    count = request.json.get('count', 0)
    requests.patch(
        f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}',
        headers=supabase_service_headers(),
        json={'viewer_count': count}
    )
    return jsonify({'success': True})


@app.route('/send_signal', methods=['POST'])
def send_signal():
    data = request.json
    requests.post(
        f'{SUPABASE_URL}/rest/v1/signals',
        headers=supabase_service_headers(),
        json={
            'stream_id': data['stream_id'],
            'target_id': data['target_id'],
            'type': data['type'],
            'data': json.dumps(data['data'])
        }
    )
    return jsonify({'success': True})

@app.route('/get_signals/<stream_id>/<signal_type>')
def get_signals(stream_id, signal_type):
    viewer_id = request.args.get('viewer_id', '')
    if viewer_id:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/signals?stream_id=eq.{stream_id}&target_id=eq.{viewer_id}&order=created_at.asc',
            headers=supabase_service_headers()
        )
    else:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/signals?stream_id=eq.{stream_id}&type=eq.{signal_type}&order=created_at.asc',
            headers=supabase_service_headers()
        )
    signals = r.json() if r.ok else []
    for s in signals:
        if isinstance(s.get('data'), str):
            try:
                s['data'] = json.loads(s['data'])
            except:
                pass
    return jsonify(signals)

@app.route('/delete_signal/<signal_id>', methods=['POST'])
def delete_signal(signal_id):
    requests.delete(
        f'{SUPABASE_URL}/rest/v1/signals?id=eq.{signal_id}',
        headers=supabase_service_headers()
    )
    return jsonify({'success': True})


@app.route('/save_peer_id/<stream_id>', methods=['POST'])
def save_peer_id(stream_id):
    peer_id = request.json.get('peer_id')
    requests.patch(
        f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}',
        headers=supabase_service_headers(),
        json={'peer_id': peer_id}
    )
    return jsonify({'success': True})

if __name__ == '__main__':
    print("\n🎬 VAULTSTREAM — http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
