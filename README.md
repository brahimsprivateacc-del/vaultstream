# 🎬 VaultStream

A YouTube-style video platform built for **everywhere** — city, remote, or off-grid. Watch, share and store videos even on the slowest connections. 🛰️

🌐 **Live at:** [https://vaultstream.online/](https://vaultstream.online/)

---

## ✨ Features

- 🎬 **Upload & watch videos** — supports MP4, MKV, MOV, AVI, WEBM
- ☁️ **Permanent cloud storage** — powered by Cloudinary, videos never disappear
- 🖼️ **Auto thumbnails** — generated automatically from every video
- 👤 **User accounts** — sign up, log in, profile pages with photos
- ❤️ **Likes & comments** — interact with videos and creators
- 🔥 **Trending page** — discover the most watched videos
- 📊 **View counts** — track how many times videos have been watched
- 📱 **PWA** — installable on iPhone and Android like a native app
- 🛰️ **Satellite ready** — low bandwidth mode + offline download for remote areas
- 🌙 **Dark theme** — YouTube-style dark UI

---

## 🗺️ Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Done | Local Python video player |
| Phase 2 | ✅ Done | Online platform with user accounts |
| Phase 3 | 🔴 Active | Offline sync, PWA, low bandwidth mode |
| Phase 4 | 🔵 Future | Full satellite connectivity for remote areas |

---

## 🛠️ Built With

| Technology | Purpose |
|---|---|
| Python + Flask | Backend server |
| Supabase | Database + authentication |
| Cloudinary | Video + image storage |
| Render | Hosting |
| HTML/CSS/JS | Frontend UI |

---

## 🚀 Run Locally

1. Clone the repo:
```bash
git clone https://github.com/brahimsprivateacc-del/vaultstream
cd vaultstream
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_KEY=your_service_key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

4. Run the app:
```bash
python app.py
```

5. Open [http://localhost:5000](http://localhost:5000) 🎉

---

## 📱 Install as App (PWA)

**iPhone:** Open in Safari → Share → Add to Home Screen

**Android:** Open in Chrome → Menu → Add to Home Screen

---

## 🛰️ Satellite Features

VaultStream is designed to work in remote areas with slow or satellite internet:

- **Auto-detects** slow connections and warns the user
- **Low quality mode** — reduces video quality to save bandwidth
- **Offline download** — save videos to your device with a progress bar
- Works with **Starlink, HughesNet** and any satellite provider

---

*Built from scratch by a beginner coder with big dreams* 🚀
