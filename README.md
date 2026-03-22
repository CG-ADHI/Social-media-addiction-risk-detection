# 🧠 MindGuard v2 — Social Media Addiction Risk Detector

> **Biopunk wellness app** · Detect addiction risk · Analyze mood · Gamified recovery  
> Built with Django · Gemini AI · Chart.js · Mobile-first design

---

## ✨ Features

| Feature | Description |
|---|---|
| 📊 **Risk Engine** | 0–100 addiction score from screen time, sleep, frequency, mood |
| 🌈 **Mood Intelligence** | 8 mood types · Journal sentiment analysis · Personalized activities |
| 💬 **Gemini AI Chat** | Empathetic real-time conversation with Google Gemini |
| 🎯 **Focus Planner** | Max 3 daily tasks · Priority levels · Inline Pomodoro timer |
| ⏱ **Pomodoro Timer** | 25/15/5 min sessions · Auto-logs focus time · XP reward |
| 📈 **Dashboard** | 5 live charts · Emotional insights · Weekly trend analysis |
| 🏋️ **Workout Demos** | Animated breathing · HIIT timer · Stretch guide · Meditation wave |
| 🔥 **Streak + XP** | Daily streaks · Level system · 12 badges (Common→Legendary) |
| 🔔 **Browser Notifications** | Break reminders · Sleep nudges · Check-in alerts |
| 🔒 **Privacy First** | Local SQLite · No data sharing · No analytics |

---

## 🗂 Project Structure

```
mindguard/
├── manage.py
├── requirements.txt
├── main/
│   ├── settings.py        ← Config + Gemini API key
│   ├── urls.py
│   └── wsgi.py
├── core/
│   ├── models.py          ← 6 models: Profile, CheckIn, Badge, Task, Session, Chat
│   ├── views.py           ← 12 views + 3 JSON APIs
│   ├── analytics.py       ← Risk engine, sentiment, productivity, 12 badges
│   ├── urls.py
│   └── admin.py
├── static/
│   ├── css/main.css       ← 900-line biopunk theme
│   └── js/main.js
└── templates/
    ├── base.html           ← Desktop navbar + mobile bottom nav
    ├── core/
    │   ├── home.html
    │   ├── dashboard.html  ← Charts, tasks, Pomodoro, XP bar, notifications
    │   ├── checkin.html
    │   ├── checkin_result.html ← 3 animated score rings (inline)
    │   ├── chatbot.html
    │   ├── workout.html    ← Per-exercise animated demos
    │   ├── history.html
    │   └── profile.html   ← All 12 badges, XP guide, rarity display
    └── registration/
        ├── login.html
        └── register.html
```

---

## 🚀 Local Setup (Windows — VS Code)

### Step 1 — Create & Activate Virtual Environment

```powershell
cd path\to\mindguard
python -m venv .venv
.\.venv\Scripts\activate
```

### Step 2 — Install Dependencies

```powershell
pip install Django==4.2
pip install google-generativeai
```

### Step 3 — Run Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

### Step 4 — Start Server

```powershell
python manage.py runserver
```

Open → **http://127.0.0.1:8000**

---

## 🌐 DEPLOY TO GITHUB + MAKE IT PUBLIC (Free)

### Option A — Railway.app (Recommended, 100% Free)

Railway gives you a real public URL like `mindguard.up.railway.app`.

#### Step 1 — Push to GitHub

1. Go to **github.com** → click **New Repository**
2. Name it `mindguard` → make it **Public** → click **Create**
3. In VS Code terminal:

```powershell
git init
git add .
git commit -m "Initial MindGuard commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mindguard.git
git push -u origin main
```

#### Step 2 — Add Production Files

Create `Procfile` (no extension) in the root folder:
```
web: gunicorn main.wsgi
```

Create `runtime.txt`:
```
python-3.11.0
```

Update `requirements.txt`:
```
Django>=4.2,<5.0
google-generativeai>=0.8.0
gunicorn
whitenoise
```

Update `main/settings.py` — add these lines:
```python
import os

# For production
ALLOWED_HOSTS = ['*']
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# WhiteNoise for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Secret key from environment
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-local-dev-key-here')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBLLeUyLZ91gqSd86JaelU5qy1kl8Mtq-Y')
```

Push again:
```powershell
git add .
git commit -m "Add production config"
git push
```

#### Step 3 — Deploy on Railway

1. Go to **railway.app** → Sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `mindguard` repo
4. Railway auto-detects Django and deploys!
5. Click **Settings → Environment Variables** → Add:
   - `SECRET_KEY` = any long random string
   - `GEMINI_API_KEY` = your key
   - `DEBUG` = `False`
6. Click **Domains** → **Generate Domain** → copy your URL!

**Your app is now live at: `https://mindguard-xxx.up.railway.app`** 🎉

---

### Option B — Render.com (Also Free)

1. Push to GitHub (same as Step 1 above)
2. Go to **render.com** → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn main.wsgi`
5. Add environment variables (same as Railway)
6. Click **Create Web Service** → get your live URL!

---

### Option C — PythonAnywhere (Free tier)

1. Go to **pythonanywhere.com** → Create free account
2. Open **Bash console**:
```bash
git clone https://github.com/YOUR_USERNAME/mindguard.git
cd mindguard
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic
```
3. Go to **Web tab** → Add New Web App → Manual → Python 3.11
4. Set source dir to `/home/YOUR_USERNAME/mindguard`
5. Set WSGI to point to `main.wsgi`
6. Your URL: `YOUR_USERNAME.pythonanywhere.com`

---

## 🔑 URL Map

| URL | Page |
|---|---|
| `/` | Landing page |
| `/register/` | Create account |
| `/login/` | Sign in |
| `/dashboard/` | Main dashboard |
| `/checkin/` | Daily check-in form |
| `/checkin/` POST | Results with score rings |
| `/chat/` | AI companion |
| `/workout/<key>/` | Exercise demo (breathing/hiit/walk/etc.) |
| `/history/` | Check-in history |
| `/profile/` | Badges + XP + level |
| `/api/chat/` | Chat JSON API |
| `/api/tasks/` | Task CRUD JSON API |
| `/api/focus-session/` | Log Pomodoro session |
| `/admin/` | Django admin |

---

## 🏆 Badge List

| Badge | Icon | Rarity | XP | How to Earn |
|---|---|---|---|---|
| First Step | 👣 | Common | 30 | First check-in |
| Week Warrior | 🔥 | Rare | 100 | 7-day streak |
| Month Master | 💎 | Epic | 300 | 30-day streak |
| Unstoppable | ⚡ | Legendary | 700 | 90-day streak |
| Light Touch | 📵 | Common | 50 | Screen time ≤ 1h |
| Digital Monk | 🧘 | Epic | 200 | 7 days of ≤1h screen |
| Mood Tracker | 🌈 | Common | 40 | 5 check-ins |
| Inner Peace | ☮️ | Rare | 150 | Mood ≥8 for 5 days |
| Wordsmith | ✍️ | Rare | 80 | Journal 7 times |
| Task Crusher | 🎯 | Rare | 100 | Complete 3 tasks in a day |
| Flow State | 🌊 | Epic | 200 | 4 focus sessions in a day |
| Productivity God | 👑 | Legendary | 500 | Productivity score ≥90 |

---

## 🔧 Troubleshooting

**`ModuleNotFoundError: No module named 'django'`**  
→ Activate venv: `.\.venv\Scripts\activate`

**`FutureWarning: google.generativeai deprecated`**  
→ Cosmetic warning only. App works fine. Will be fixed in a future google-genai migration.

**Static files not loading in production**  
→ Run `python manage.py collectstatic` and ensure WhiteNoise is in MIDDLEWARE.

**Gemini API timeout**  
→ The app has fallback suggestions — it will still work without Gemini connectivity.

---

## 🔮 Future Roadmap

- [ ] Screen Time API integration (iOS Screen Time / Android Digital Wellbeing)
- [ ] Voice mood detection
- [ ] Progressive Web App (PWA) for home screen install
- [ ] Dark/light mode toggle
- [ ] Weekly email wellness report
- [ ] AI habit prediction model

---

*Built with Django 4.2 · Gemini 2.5 Flash · Chart.js 4 · Outfit + JetBrains Mono fonts*  
*Designed for those who want to reclaim their attention. 🧠*
