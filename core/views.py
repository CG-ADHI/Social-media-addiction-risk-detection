import json
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings

from .models import UserProfile, DailyCheckIn, Badge, ChatMessage, FocusTask, FocusSession
from .analytics import (
    analyze_sentiment, calculate_risk, calculate_productivity,
    generate_emotional_insight, get_activities, calculate_xp,
    check_and_award_badges, WORKOUTS
)


# ── Helper ────────────────────────────────────────────────────────────────────
def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def get_gemini_response(prompt, fallback="I'm here for you! 💙"):
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return fallback


# ── Auth ──────────────────────────────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
        else:
            error = "Invalid username or password."
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form, 'error': error})


def logout_view(request):
    logout(request)
    return redirect('home')


# ── Dashboard ─────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    profile = get_or_create_profile(request.user)
    today = date.today()
    today_checkin = DailyCheckIn.objects.filter(user=request.user, date=today).first()
    all_checkins = DailyCheckIn.objects.filter(user=request.user)

    chart_labels, chart_risk, chart_mood, chart_screen, chart_prod = [], [], [], [], []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = DailyCheckIn.objects.filter(user=request.user, date=d).first()
        chart_labels.append(d.strftime('%b %d'))
        chart_risk.append(c.risk_score if c else None)
        chart_mood.append(c.mood_rating if c else None)
        chart_screen.append(c.screen_time_hours if c else None)
        chart_prod.append(c.productivity_score if c else None)

    total_checkins = all_checkins.count()
    low_risk_days = all_checkins.filter(risk_level='low').count()
    badges = Badge.objects.filter(user=request.user).order_by('-earned_at')[:8]

    week_ago = today - timedelta(days=7)
    this_week = list(all_checkins.filter(date__gte=week_ago))
    usage_trend_msg = None
    if len(this_week) >= 4:
        mid = len(this_week) // 2
        avg1 = sum(c.screen_time_hours for c in this_week[mid:]) / len(this_week[mid:])
        avg2 = sum(c.screen_time_hours for c in this_week[:mid]) / len(this_week[:mid])
        if avg2 < avg1 - 0.5:
            usage_trend_msg = f"📉 Your usage decreased by {avg1-avg2:.1f}h this week — great job!"
        elif avg2 > avg1 + 0.5:
            usage_trend_msg = f"📈 Your usage increased by {avg2-avg1:.1f}h this week — try to cut back."

    emotional_insights = generate_emotional_insight(all_checkins)
    today_tasks = FocusTask.objects.filter(user=request.user, date=today)
    level_info = profile.get_level_info()
    recent = list(all_checkins[:7])

    return render(request, 'core/dashboard.html', {
        'profile': profile,
        'today_checkin': today_checkin,
        'chart_labels': json.dumps(chart_labels),
        'chart_risk': json.dumps(chart_risk),
        'chart_mood': json.dumps(chart_mood),
        'chart_screen': json.dumps(chart_screen),
        'chart_prod': json.dumps(chart_prod),
        'total_checkins': total_checkins,
        'low_risk_days': low_risk_days,
        'badges': badges,
        'usage_trend_msg': usage_trend_msg,
        'emotional_insights': emotional_insights,
        'today_tasks': today_tasks,
        'level_info': level_info,
        'recent': recent,
        'today': today,
    })


# ── Check-In ──────────────────────────────────────────────────────────────────
APP_TYPES = [
    ('reels', '📽 Reels'), ('tiktok', '🎵 TikTok'), ('messaging', '💬 Messaging'),
    ('gaming', '🎮 Gaming'), ('news', '📰 News'), ('shopping', '🛍 Shopping'),
    ('youtube', '▶️ YouTube'), ('twitter', '🐦 Twitter/X'),
]
MOODS = [
    ('happy', 'Happy', '😊'), ('neutral', 'Neutral', '😐'), ('sad', 'Sad', '😢'),
    ('anxious', 'Anxious', '😰'), ('angry', 'Angry', '😠'), ('bored', 'Bored', '😑'),
    ('energetic', 'Energetic', '⚡'), ('tired', 'Tired', '😴'),
]


@login_required
def checkin(request):
    today = date.today()
    existing = DailyCheckIn.objects.filter(user=request.user, date=today).first()

    if request.method == 'POST':
        profile = get_or_create_profile(request.user)

        screen_time = float(request.POST.get('screen_time', 0))
        usage_freq  = int(request.POST.get('usage_frequency', 0))
        sleep_dist  = request.POST.get('sleep_disturbance') == 'on'
        late_night  = request.POST.get('late_night_usage') == 'on'
        app_types   = request.POST.getlist('app_types')
        mood_rating = int(request.POST.get('mood_rating', 5))
        mood_label  = request.POST.get('mood_label', 'neutral')
        journal     = request.POST.get('journal_entry', '')
        focus_sess  = int(request.POST.get('focus_sessions', 0))

        sentiment = analyze_sentiment(journal) if journal else {'score': 0, 'label': 'neutral'}
        risk = calculate_risk({
            'screen_time_hours': screen_time,
            'usage_frequency': usage_freq,
            'sleep_disturbance': sleep_dist,
            'late_night_usage': late_night,
            'app_types': app_types,
            'mood_rating': mood_rating,
        })

        today_tasks = FocusTask.objects.filter(user=request.user, date=today)
        tasks_done  = today_tasks.filter(status='done').count()
        tasks_total = today_tasks.count()

        prod = calculate_productivity(tasks_done, tasks_total, screen_time, focus_sess, mood_rating)

        prompt = f"""You are MindGuard AI, a compassionate wellness coach.
Risk: {risk['risk_level']} ({risk['risk_score']}/100). Mood: {mood_label} ({mood_rating}/10).
Screen time: {screen_time}h. Assessment: {risk['risk_explanation']}.
Journal: {journal[:200] if journal else 'None'}.
Give exactly 3 warm, practical suggestions as a JSON array of strings. Each 1-2 sentences.
Respond ONLY with the JSON array, no extra text."""

        raw_ai = get_gemini_response(prompt, fallback=None)
        if raw_ai:
            try:
                ai_list = json.loads(raw_ai.replace('```json', '').replace('```', '').strip())
            except Exception:
                ai_list = [raw_ai]
        else:
            fallbacks = {
                'high': [
                    "Put your phone in another room for 1 hour right now.",
                    "Tell someone you trust how you're feeling today.",
                    "Set a screen-free hour before bed tonight.",
                ],
                'medium': [
                    "Try a 20-minute phone-free window this afternoon.",
                    "Notice when you reach for your phone automatically — pause and breathe.",
                    "Complete one focus task before checking social media.",
                ],
                'low': [
                    "You're doing great! Celebrate this healthy day.",
                    "Share what's working with a friend or journal about it.",
                    "Set a slightly more ambitious screen-time goal tomorrow.",
                ],
            }
            ai_list = fallbacks.get(risk['risk_level'], fallbacks['medium'])

        obj, created = DailyCheckIn.objects.update_or_create(
            user=request.user, date=today,
            defaults={
                'screen_time_hours': screen_time,
                'usage_frequency': usage_freq,
                'sleep_disturbance': sleep_dist,
                'late_night_usage': late_night,
                'app_types': ', '.join(app_types),
                'mood_rating': mood_rating,
                'mood_label': mood_label,
                'journal_entry': journal,
                'sentiment_score': sentiment['score'],
                'sentiment_label': sentiment['label'],
                'risk_score': risk['risk_score'],
                'risk_level': risk['risk_level'],
                'risk_explanation': risk['risk_explanation'],
                'productivity_score': prod['score'],
                'focus_sessions': focus_sess,
                'tasks_completed': tasks_done,
                'tasks_total': tasks_total,
                'ai_suggestions': json.dumps(ai_list),
            }
        )

        if created:
            xp = calculate_xp(obj, tasks_done)
            obj.xp_earned = xp
            obj.save()
            profile.xp += xp
            yesterday = today - timedelta(days=1)
            profile.streak_days = profile.streak_days + 1 if profile.last_check_in == yesterday else 1
            profile.longest_streak = max(profile.longest_streak, profile.streak_days)
            profile.last_check_in = today
            profile.save()
            all_checkins = DailyCheckIn.objects.filter(user=request.user)
            check_and_award_badges(request.user, profile, obj, all_checkins)

        activities = get_activities(risk['risk_level'], mood_label)
        return render(request, 'core/checkin_result.html', {
            'checkin': obj,
            'risk': risk,
            'sentiment': sentiment,
            'activities': activities,
            'prod': prod,
            'ai_suggestions': json.dumps(ai_list),
        })

    return render(request, 'core/checkin.html', {
        'existing': existing,
        'today': today,
        'app_types': APP_TYPES,
        'moods': MOODS,
        'today_tasks': FocusTask.objects.filter(user=request.user, date=today),
    })


# ── Task API ──────────────────────────────────────────────────────────────────
@login_required
def task_api(request):
    today = date.today()
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'add':
            if FocusTask.objects.filter(user=request.user, date=today).count() >= 3:
                return JsonResponse({'error': 'Max 3 tasks per day'}, status=400)
            task = FocusTask.objects.create(
                user=request.user, date=today,
                title=data.get('title', ''),
                priority=data.get('priority', 'medium'),
            )
            return JsonResponse({'id': task.id, 'title': task.title, 'priority': task.priority})

        elif action == 'toggle':
            task = get_object_or_404(FocusTask, id=data.get('id'), user=request.user)
            task.status = 'done' if task.status == 'pending' else 'pending'
            if task.status == 'done':
                task.completed_at = timezone.now()
            task.save()
            return JsonResponse({'status': task.status})

        elif action == 'delete':
            FocusTask.objects.filter(id=data.get('id'), user=request.user).delete()
            return JsonResponse({'ok': True})

    tasks = FocusTask.objects.filter(user=request.user, date=today)
    return JsonResponse({'tasks': [
        {'id': t.id, 'title': t.title, 'priority': t.priority, 'status': t.status}
        for t in tasks
    ]})


# ── Focus Session API ─────────────────────────────────────────────────────────
@login_required
def focus_session_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        today = date.today()
        FocusSession.objects.create(
            user=request.user, date=today,
            duration_minutes=data.get('duration', 25),
            completed=True,
        )
        checkin_obj = DailyCheckIn.objects.filter(user=request.user, date=today).first()
        if checkin_obj:
            checkin_obj.focus_sessions += 1
            checkin_obj.save()
        return JsonResponse({'ok': True, 'xp': 10})
    return JsonResponse({'error': 'POST only'}, status=405)


# ── Chatbot ───────────────────────────────────────────────────────────────────
@login_required
def chatbot(request):
    msgs = list(ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:20])
    return render(request, 'core/chatbot.html', {'messages': reversed(msgs)})


@login_required
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    data = json.loads(request.body)
    user_msg = data.get('message', '').strip()
    if not user_msg:
        return JsonResponse({'error': 'Empty'}, status=400)

    profile = get_or_create_profile(request.user)
    last = DailyCheckIn.objects.filter(user=request.user).first()
    ctx = f"Risk:{last.risk_level}, Mood:{last.mood_label}, Streak:{profile.streak_days}d" if last else "New user"

    history = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:5]
    history_text = ''.join(
        f"User: {h.message}\nYou: {h.response}\n"
        for h in reversed(list(history))
    )

    prompt = f"""You are MindGuard, a warm, empathetic AI wellness companion for social media addiction recovery.
User context: {ctx}. XP: {profile.xp}.
{history_text}
User: {user_msg}
Respond warmly in 2-3 sentences. Acknowledge feelings first. Suggest one practical offline action when relevant."""

    response = get_gemini_response(
        prompt,
        "I hear you 💙. Sometimes stepping away for just 10 minutes — a glass of water, a stretch — can completely reset your mind. What's one tiny thing you could do right now?"
    )

    ChatMessage.objects.create(user=request.user, message=user_msg, response=response)
    return JsonResponse({'response': response})


# ── Workouts Page ─────────────────────────────────────────────────────────────
@login_required
def workouts_page(request):
    """Gallery of all available workouts/activities."""
    return render(request, 'core/workouts.html', {'workouts': WORKOUTS})


# ── Workout Detail ────────────────────────────────────────────────────────────
@login_required
def workout_detail(request, key):
    workout = WORKOUTS.get(key)
    if not workout:
        return redirect('workouts')
    return render(request, 'core/workout.html', {'workout': workout, 'key': key})


# ── History ───────────────────────────────────────────────────────────────────
@login_required
def history(request):
    checkins = DailyCheckIn.objects.filter(user=request.user)[:60]
    return render(request, 'core/history.html', {'checkins': checkins})


# ── Profile ───────────────────────────────────────────────────────────────────
@login_required
def profile_view(request):
    profile = get_or_create_profile(request.user)
    badges  = Badge.objects.filter(user=request.user).order_by('-earned_at')
    total   = DailyCheckIn.objects.filter(user=request.user).count()
    level_info = profile.get_level_info()

    RARITY_ORDER = {'legendary': 0, 'epic': 1, 'rare': 2, 'common': 3}
    badges_sorted = sorted(badges, key=lambda b: RARITY_ORDER.get(b.rarity, 4))

    from core.analytics import BADGE_DEFINITIONS
    all_defs = [
        {'icon': d['icon'], 'name': d['name'], 'rarity': d['rarity'], 'xp': d['xp']}
        for d in BADGE_DEFINITIONS
    ]
    earned_names = {b.name for b in badges}

    xp_guide = [
        {'label': '✍️ Daily Check-In',           'xp': 20},
        {'label': '✅ Low Risk Day',              'xp': 40},
        {'label': '📔 Journal Entry',             'xp': 25},
        {'label': '📵 Screen Time < 2h',          'xp': 50},
        {'label': '📵 Screen Time < 1h (bonus)',  'xp': 30},
        {'label': '😊 Mood Rating 8+',            'xp': 20},
        {'label': '🎯 Each Task Completed',       'xp': 15},
        {'label': '⏱ Each Focus Session',         'xp': 10},
    ]

    return render(request, 'core/profile.html', {
        'profile': profile,
        'badges': badges_sorted,
        'total_checkins': total,
        'level_info': level_info,
        'all_badge_defs': all_defs,
        'earned_names': earned_names,
        'xp_guide': xp_guide,
    })
