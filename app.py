from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for, session
import os
from werkzeug.utils import secure_filename
import requests
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'vaultstream-secret-key-2026-change-this')
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 365  # 1 year
app.config['SESSION_COOKIE_SECURE'] = True      # Only send over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True    # JS can't read the cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevents CSRF attacks

VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')
ALLOWED_EXTENSIONS = {'mp4', 'mkv', 'mov', 'avi', 'webm'}
app.config['MAX_CONTENT_LENGTH'] = 4096 * 1024 * 1024

# Admin
ADMIN_USER_ID = '9e186088-8134-43d3-9ea6-8a3330335845'

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://wweckerzweqjrrrbqysq.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_publishable_cxxK6Id-_Ttl18yWep2oNQ_BgO2rghG')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind3ZWNrZXJ6d2VxanJycmJxeXNxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjgyNTg5NSwiZXhwIjoyMDg4NDAxODk1fQ.6ZOMljwV5qt7mPPjn_6kpxaQHlt44J89Xdm2eeHET4g')

# Agora
AGORA_APP_ID = os.environ.get('AGORA_APP_ID', '5f982bff4e5b4545be3d1539af0538a5')
AGORA_APP_CERT = os.environ.get('AGORA_APP_CERT', '907ad51f2a20407d98d9d389a0665d5f')
AGORA_CHANNEL = 'vaultstream'

# Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'dkym11l9b'),
    api_key=os.environ.get('CLOUDINARY_API_KEY', '372954551797955'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', 'l7p9Qa1jY5yJcK_kv4_jJFbIkdo')
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

@app.route('/')
def index():
    user = get_current_user()
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username,avatar_url)&order=created_at.desc', headers=supabase_headers())
    videos = r.json() if r.ok else []
    r2 = requests.get(f'{SUPABASE_URL}/rest/v1/streams?is_live=eq.true&select=*,profiles(username)&order=created_at.desc', headers=supabase_service_headers())
    live_streams = r2.json() if r2.ok else []
    return render_template('index.html', videos=videos, user=user, live_streams=live_streams)

@app.route('/watch/<video_id>')
def watch(video_id):
    user = get_current_user()
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&select=*,profiles(username,avatar_url)', headers=supabase_headers())
    videos = r.json()
    if not videos:
        return redirect(url_for('index'))
    video = videos[0]
    r2 = requests.get(f'{SUPABASE_URL}/rest/v1/comments?video_id=eq.{video_id}&select=*,profiles(username)&order=created_at.asc', headers=supabase_headers())
    comments = r2.json() if r2.ok else []
    r3 = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&select=id', headers=supabase_headers())
    likes = len(r3.json()) if r3.ok else 0
    user_liked = False
    if user:
        r4 = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}', headers=supabase_headers())
        user_liked = len(r4.json()) > 0 if r4.ok else False
    requests.post(f'{SUPABASE_URL}/rpc/increment_views', headers=supabase_service_headers(), json={'video_id': video_id})
    return render_template('watch.html', video=video, comments=comments, likes=likes, user=user, user_liked=user_liked)

@app.route('/profile/<username>')
def profile(username):
    user = get_current_user()
    r = requests.get(f'{SUPABASE_URL}/rest/v1/profiles?username=eq.{username}&select=*', headers=supabase_headers())
    profiles = r.json()
    if not profiles:
        return redirect(url_for('index'))
    profile_user = profiles[0]
    r2 = requests.get(f'{SUPABASE_URL}/rest/v1/videos?user_id=eq.{profile_user["id"]}&order=created_at.desc', headers=supabase_headers())
    user_videos = r2.json() if r2.ok else []
    return render_template('profile.html', profile_user=profile_user, videos=user_videos, user=user)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        r = requests.post(f'{SUPABASE_URL}/auth/v1/signup', headers=supabase_headers(), json={'email': email, 'password': password})
        data = r.json()
        if r.ok and data.get('user'):
            user_id = data['user']['id']
            token = data.get('access_token')
            requests.post(f'{SUPABASE_URL}/rest/v1/profiles', headers=supabase_service_headers(), json={'id': user_id, 'username': username})
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
        r = requests.post(f'{SUPABASE_URL}/auth/v1/token?grant_type=password', headers=supabase_headers(), json={'email': email, 'password': password})
        data = r.json()
        if r.ok and data.get('access_token'):
            user_id = data['user']['id']
            token = data['access_token']
            r2 = requests.get(f'{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}', headers=supabase_headers(token))
            profiles = r2.json()
            username = profiles[0]['username'] if profiles else email
            session.permanent = True
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
    is_short = request.form.get('is_short', '0') == '1'
    result = cloudinary.uploader.upload(file, resource_type='video', folder='vaultstream', public_id=os.path.splitext(filename)[0], overwrite=True)
    video_url = result.get('secure_url')
    thumbnail_url = result.get('secure_url', '').rsplit('.', 1)[0].replace('/video/upload/', '/video/upload/so_0,w_400,h_225,c_fill/') + '.jpg'
    size = get_file_size(result.get('bytes', 0))
    requests.post(f'{SUPABASE_URL}/rest/v1/videos', headers=supabase_service_headers(), json={
        'user_id': user['id'], 'filename': filename, 'title': title, 'size': size,
        'extension': ext, 'video_url': video_url, 'thumbnail_url': thumbnail_url,
        'category': category, 'is_short': is_short
    })
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
    r = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}', headers=supabase_headers())
    if r.json():
        requests.delete(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video_id}&user_id=eq.{user["id"]}', headers=supabase_headers(user['token']))
        liked = False
    else:
        requests.post(f'{SUPABASE_URL}/rest/v1/likes', headers=supabase_headers(user['token']), json={'user_id': user['id'], 'video_id': video_id})
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
    requests.post(f'{SUPABASE_URL}/rest/v1/comments', headers={**supabase_headers(user['token']), 'Prefer': 'return=representation'}, json={'user_id': user['id'], 'video_id': video_id, 'content': content})
    return jsonify({'success': True, 'username': user['username'], 'content': content})

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    file = request.files['avatar']
    result = cloudinary.uploader.upload(file, folder='vaultstream/avatars', public_id=user['id'], overwrite=True, transformation=[{'width': 200, 'height': 200, 'crop': 'fill', 'gravity': 'face'}])
    avatar_url = result.get('secure_url')
    requests.patch(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}", headers=supabase_service_headers(), json={'avatar_url': avatar_url})
    return jsonify({'success': True, 'url': avatar_url})

@app.route('/update_bio', methods=['POST'])
def update_bio():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    bio = request.json.get('bio', '').strip()
    requests.patch(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}", headers=supabase_service_headers(), json={'bio': bio})
    return jsonify({'success': True})

@app.route('/update_title/<video_id>', methods=['POST'])
def update_title(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    title = request.json.get('title', '').strip()
    if not title:
        return jsonify({'success': False, 'error': 'Title cannot be empty'}), 400
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&user_id=eq.{user["id"]}', headers=supabase_service_headers())
    if not r.json():
        return jsonify({'success': False, 'error': 'Not your video'}), 403
    requests.patch(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}', headers=supabase_service_headers(), json={'title': title})
    return jsonify({'success': True})

@app.route('/delete_video/<video_id>', methods=['POST'])
def delete_video(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&select=*', headers=supabase_service_headers())
    videos = r.json()
    if not videos:
        return jsonify({'success': False, 'error': 'Video not found'}), 404
    video = videos[0]
    if user['id'] != ADMIN_USER_ID:
        if video['user_id'] != user['id']:
            return jsonify({'success': False, 'error': 'Not your video'}), 403
    reason = request.json.get('reason', '') if request.is_json else ''
    if user['id'] == ADMIN_USER_ID and video['user_id'] != user['id']:
        msg = f'Your video "{video["title"]}" was removed by an admin.'
        if reason:
            msg += f' Reason: {reason}'
        requests.post(f'{SUPABASE_URL}/rest/v1/notifications', headers=supabase_service_headers(), json={'user_id': video['user_id'], 'message': msg})
    requests.delete(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}', headers=supabase_service_headers())
    return jsonify({'success': True})

@app.route('/send_warning/<video_id>', methods=['POST'])
def send_warning(video_id):
    user = get_current_user()
    if not user or user['id'] != ADMIN_USER_ID:
        return jsonify({'success': False}), 403
    message = request.json.get('message', 'You have received a warning from an admin.')
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&select=user_id,title', headers=supabase_service_headers())
    videos = r.json()
    if videos:
        requests.post(f'{SUPABASE_URL}/rest/v1/notifications', headers=supabase_service_headers(), json={'user_id': videos[0]['user_id'], 'message': f'⚠️ Warning: {message}'})
    return jsonify({'success': True})

@app.route('/report_video/<video_id>', methods=['POST'])
def report_video(video_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    reason = request.json.get('reason', 'No reason given')
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?id=eq.{video_id}&select=title,user_id', headers=supabase_service_headers())
    videos = r.json()
    if not videos:
        return jsonify({'success': False}), 404
    msg = f'🚨 Video "{videos[0]["title"]}" was reported. Reason: {reason}'
    requests.post(f'{SUPABASE_URL}/rest/v1/notifications', headers=supabase_service_headers(), json={'user_id': ADMIN_USER_ID, 'message': msg})
    return jsonify({'success': True})

@app.route('/notifications')
def notifications():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    r = requests.get(f'{SUPABASE_URL}/rest/v1/notifications?user_id=eq.{user["id"]}&order=created_at.desc', headers=supabase_service_headers())
    notifs = r.json() if r.ok else []
    requests.patch(f'{SUPABASE_URL}/rest/v1/notifications?user_id=eq.{user["id"]}', headers=supabase_service_headers(), json={'is_read': True})
    return render_template('notifications.html', notifications=notifs, user=user)

@app.route('/unread_notifications')
def unread_notifications():
    user = get_current_user()
    if not user:
        return jsonify({'count': 0})
    r = requests.get(f'{SUPABASE_URL}/rest/v1/notifications?user_id=eq.{user["id"]}&is_read=eq.false', headers=supabase_service_headers())
    return jsonify({'count': len(r.json()) if r.ok else 0})

@app.route('/trending')
def trending():
    user = get_current_user()
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username)&order=views.desc', headers=supabase_headers())
    videos = r.json() if r.ok else []
    return render_template('trending.html', videos=videos, user=user)

@app.route('/search')
def search():
    user = get_current_user()
    q = request.args.get('q', '').strip()
    videos = []
    if q:
        r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?select=*,profiles(username)&title=ilike.*{q}*&order=views.desc', headers=supabase_headers())
        videos = r.json() if r.ok else []
    return render_template('search.html', videos=videos, query=q, user=user)

@app.route('/shorts')
def shorts():
    user = get_current_user()
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?is_short=eq.true&select=*,profiles(username)&order=created_at.desc', headers=supabase_headers())
    shorts_list = r.json() if r.ok else []
    for short in shorts_list:
        r2 = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{short["id"]}', headers=supabase_service_headers())
        short['like_count'] = len(r2.json()) if r2.ok else 0
        short['user_liked'] = False
        if user:
            r3 = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{short["id"]}&user_id=eq.{user["id"]}', headers=supabase_service_headers())
            short['user_liked'] = len(r3.json()) > 0 if r3.ok else False
        r4 = requests.get(f'{SUPABASE_URL}/rest/v1/comments?video_id=eq.{short["id"]}', headers=supabase_service_headers())
        short['comment_count'] = len(r4.json()) if r4.ok else 0
    return render_template('shorts.html', shorts=shorts_list, user=user)

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    r = requests.get(f'{SUPABASE_URL}/rest/v1/videos?user_id=eq.{user["id"]}&order=views.desc', headers=supabase_service_headers())
    videos = r.json() if r.ok else []
    for video in videos:
        r2 = requests.get(f'{SUPABASE_URL}/rest/v1/likes?video_id=eq.{video["id"]}', headers=supabase_service_headers())
        video['like_count'] = len(r2.json()) if r2.ok else 0
        r3 = requests.get(f'{SUPABASE_URL}/rest/v1/comments?video_id=eq.{video["id"]}', headers=supabase_service_headers())
        video['comment_count'] = len(r3.json()) if r3.ok else 0
    total_views = sum(v.get('views') or 0 for v in videos)
    total_likes = sum(v.get('like_count') or 0 for v in videos)
    total_comments = sum(v.get('comment_count') or 0 for v in videos)
    return render_template('dashboard.html', user=user, videos=videos, total_views=total_views, total_likes=total_likes, total_comments=total_comments)

@app.route('/settings')
def settings():
    user = get_current_user()
    return render_template('settings.html', user=user)

@app.route('/about')
def about():
    user = get_current_user()
    return render_template('about.html', user=user)

@app.route('/help')
def help():
    user = get_current_user()
    return render_template('help.html', user=user)

@app.route('/privacy')
def privacy():
    user = get_current_user()
    return render_template('privacy.html', user=user)

@app.route('/terms')
def terms():
    user = get_current_user()
    return render_template('terms.html', user=user)

@app.route('/live')
def live():
    user = get_current_user()
    return render_template('live.html', user=user)

@app.route('/start_stream', methods=['POST'])
def start_stream():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    title = request.json.get('title', 'Live Stream')
    requests.patch(f'{SUPABASE_URL}/rest/v1/streams?user_id=eq.{user["id"]}', headers=supabase_service_headers(), json={'is_live': False})
    r = requests.post(f'{SUPABASE_URL}/rest/v1/streams', headers=supabase_service_headers(), json={'user_id': user['id'], 'title': title, 'is_live': True, 'viewer_count': 0})
    data = r.json()
    stream_id = data[0]['id'] if isinstance(data, list) and data else None
    return jsonify({'success': True, 'stream_id': stream_id})

@app.route('/end_stream/<stream_id>', methods=['POST'])
def end_stream(stream_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False}), 401
    requests.patch(f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}&user_id=eq.{user["id"]}', headers=supabase_service_headers(), json={'is_live': False})
    return jsonify({'success': True})

@app.route('/watch_live/<stream_id>')
def watch_live(stream_id):
    user = get_current_user()
    r = requests.get(f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}', headers=supabase_service_headers())
    streams = r.json()
    if not streams:
        return redirect(url_for('index'))
    return render_template('watch_live.html', stream=streams[0], user=user)

@app.route('/stream_viewers/<stream_id>')
def stream_viewers(stream_id):
    r = requests.get(f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}&select=viewer_count,is_live', headers=supabase_service_headers())
    data = r.json()
    if data:
        return jsonify({'count': data[0]['viewer_count'], 'is_live': data[0]['is_live']})
    return jsonify({'count': 0, 'is_live': False})

@app.route('/update_viewers/<stream_id>', methods=['POST'])
def update_viewers(stream_id):
    count = request.json.get('count', 0)
    requests.patch(f'{SUPABASE_URL}/rest/v1/streams?id=eq.{stream_id}', headers=supabase_service_headers(), json={'viewer_count': count})
    return jsonify({'success': True})

@app.route('/agora_token')
def agora_token():
    try:
        from agora_token_builder import RtcTokenBuilder
        import time
        channel = request.args.get('channel', AGORA_CHANNEL)
        role = 1 if request.args.get('role', 'publisher') == 'publisher' else 2
        expire = int(time.time()) + 86400 * 7
        token = RtcTokenBuilder.buildTokenWithUid(AGORA_APP_ID, AGORA_APP_CERT, channel, 0, role, expire)
        return jsonify({'token': token, 'channel': channel, 'app_id': AGORA_APP_ID})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/auth/google')
def auth_google():
    redirect_url = f'{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=https://vaultstream.online/auth/callback'
    return redirect(redirect_url)

@app.route('/auth/callback')
def auth_callback():
    return render_template('auth_callback.html')

@app.route('/auth/set_session', methods=['POST'])
def set_session():
    token = request.json.get('access_token')
    if not token:
        return jsonify({'success': False}), 400
    r = requests.get(f'{SUPABASE_URL}/auth/v1/user', headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {token}'})
    if not r.ok:
        return jsonify({'success': False}), 400
    user_data = r.json()
    user_id = user_data['id']
    email = user_data.get('email', '')
    r2 = requests.get(f'{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}', headers=supabase_service_headers())
    profiles = r2.json()
    if profiles:
        username = profiles[0]['username']
    else:
        username = email.split('@')[0] if email else f'user_{user_id[:8]}'
        requests.post(f'{SUPABASE_URL}/rest/v1/profiles', headers=supabase_service_headers(), json={'id': user_id, 'username': username})
    session.permanent = True
    session['user'] = {'id': user_id, 'username': username, 'token': token}
    return jsonify({'success': True})

@app.route('/manifest.json')
def manifest():
    return send_from_directory('.', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    response = send_from_directory('.', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/favicon.svg')
def favicon():
    return send_from_directory('.', 'favicon.svg', mimetype='image/svg+xml')

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory('.', 'ads.txt', mimetype='text/plain')

if __name__ == '__main__':
    print("\n🎬 VAULTSTREAM — http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
