import json
from datetime import date, timedelta

def detect_language(text):
    """Simple heuristic to detect En, Hi, or Ml."""
    if not text: return 'en'
    # Malayalam: \u0D00-\u0D7F
    if any('\u0D00' <= char <= '\u0D7F' for char in text):
        return 'ml'
    # Hindi/Devanagari: \u0900-\u097F
    if any('\u0900' <= char <= '\u097F' for char in text):
        return 'hi'
    return 'en'
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
    check_and_award_badges, WORKOUTS,
    SMALL_WINS, calculate_minimalism_score, calculate_self_awareness,
    get_recent_stats, get_workout_rec
)


# Helper functions moved to analytics.py

# ── Helper ────────────────────────────────────────────────────────────────────
def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def get_gemini_response(prompt, fallback="I'm here for you! 💙"):
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        ai_text = response.text.strip()
        # Cleanup
        if ai_text.lower().startswith('mindguard ai:'): ai_text = ai_text[13:].strip()
        elif ai_text.lower().startswith('mindguard:'): ai_text = ai_text[10:].strip()
        return ai_text
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
    tasks_done = today_tasks.filter(status='done').count()
    level_info = profile.get_level_info()
    recent = list(all_checkins[:14]) # For charts

    # New advanced metrics
    avg_min = round(sum(c.minimalism_score for c in recent if c.minimalism_score > 0) / max(1, len([c for c in recent if c.minimalism_score > 0])), 1)
    avg_sa = round(sum(c.self_awareness_score for c in recent if c.self_awareness_score > 0) / max(1, len([c for c in recent if c.self_awareness_score > 0])), 1)
    
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
        'tasks_done': tasks_done,
        'level_info': level_info,
        'recent': recent[:7],
        'today': today,
        'avg_min': avg_min,
        'avg_sa': avg_sa,
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

        prompt = f"""You are Viora AI, a compassionate wellness coach.
Risk: {risk['risk_level']} ({risk['risk_score']}/100). Mood: {mood_label} ({mood_rating}/10).
Screen time: {screen_time}h. Assessment: {risk['risk_explanation']}.
Journal: {journal[:200] if journal else 'None'}.
Give exactly 3 warm, practical suggestions as a JSON array of strings. Each 1-2 sentences.
Respond ONLY with the JSON array, no extra text."""

        raw_ai = get_gemini_response(prompt, fallback=None)
        
        # Fallback suggestions if AI fails
        fallbacks = {
            'low': [
                "Great job maintaining healthy habits! Try to keep your screen time under 2 hours.",
                "Consider a 10-minute mindful walk to stay grounded.",
                "Continue journaling to build your self-awareness."
            ],
            'medium': [
                "You're doing okay, but try to set some digital boundaries.",
                "Take a 5-minute breathing break if you feel overwhelmed.",
                "Try to avoid scrolling at least 30 minutes before bed."
            ],
            'high': [
                "Your risk level is high. Please consider a digital detox for the next few hours.",
                "Practice box breathing to calm your nervous system.",
                "Reach out to a friend or loved one if you're feeling stressed."
            ]
        }

        if raw_ai:
            try:
                ai_list = json.loads(raw_ai.replace('```json', '').replace('```', '').strip())
            except Exception:
                ai_list = [raw_ai]
        else:
            ai_list = fallbacks.get(risk['risk_level'], fallbacks['medium'])

        # Advanced Metrics (New)
        # 1. Digital Minimalism
        min_score, min_feedback = calculate_minimalism_score(screen_time, usage_freq, prod['score'])

        # 2. Self-Awareness
        checkins_14 = []
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            c = DailyCheckIn.objects.filter(user=request.user, date=d).first()
            checkins_14.append({
                'exists': c is not None,
                'journaled': bool(c.journal_entry) if c else (journal != '' if d == today else False)
            })
        sa_score, sa_feedback = calculate_self_awareness(checkins_14)

        # 3. Mood Recovery Tracker
        recovery_hours = None
        last_neg = DailyCheckIn.objects.filter(user=request.user, mood_rating__lte=4, date__lt=today).first()
        if last_neg and mood_rating > 5:
            # Check if this is the FIRST positive checkin since the negative one
            is_recovered = not DailyCheckIn.objects.filter(user=request.user, mood_rating__gt=5, date__gt=last_neg.date, date__lt=today).exists()
            if is_recovered:
                diff = timezone.now() - last_neg.created_at
                recovery_hours = round(diff.total_seconds() / 3600, 1)

        # 4. One Small Win
        win_title = existing.small_win_title if existing else None
        if not win_title:
            import random
            win_title = random.choice(SMALL_WINS)

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
                'minimalism_score': min_score,
                'minimalism_feedback': min_feedback,
                'self_awareness_score': sa_score,
                'mood_recovery_hours': recovery_hours or (existing.mood_recovery_hours if existing else None),
                'small_win_title': win_title,
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
            # Sync to DailyCheckIn
            ci = DailyCheckIn.objects.filter(user=request.user, date=today).first()
            if ci:
                ci.tasks_total = FocusTask.objects.filter(user=request.user, date=today).count()
                ci.save()
            
            t_total = FocusTask.objects.filter(user=request.user, date=today).count()
            t_done = FocusTask.objects.filter(user=request.user, date=today, status='done').count()
            return JsonResponse({'id': task.id, 'title': task.title, 'priority': task.priority, 'done': t_done, 'total': t_total})

        elif action == 'toggle':
            task = get_object_or_404(FocusTask, id=data.get('id'), user=request.user)
            task.status = 'done' if task.status == 'pending' else 'pending'
            if task.status == 'done':
                task.completed_at = timezone.now()
            task.save()
            
            # Sync to DailyCheckIn
            ci = DailyCheckIn.objects.filter(user=request.user, date=today).first()
            if ci:
                ci.tasks_completed = FocusTask.objects.filter(user=request.user, date=today, status='done').count()
                ci.save()
                
            t_total = FocusTask.objects.filter(user=request.user, date=today).count()
            t_done = FocusTask.objects.filter(user=request.user, date=today, status='done').count()
            return JsonResponse({'status': task.status, 'done': t_done, 'total': t_total})

        elif action == 'delete':
            FocusTask.objects.filter(id=data.get('id'), user=request.user).delete()
            
            # Sync to DailyCheckIn
            ci = DailyCheckIn.objects.filter(user=request.user, date=today).first()
            if ci:
                ci.tasks_total = FocusTask.objects.filter(user=request.user, date=today).count()
                ci.tasks_completed = FocusTask.objects.filter(user=request.user, date=today, status='done').count()
                ci.save()
                
            t_total = FocusTask.objects.filter(user=request.user, date=today).count()
            t_done = FocusTask.objects.filter(user=request.user, date=today, status='done').count()
            return JsonResponse({'ok': True, 'done': t_done, 'total': t_total})

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


@login_required
def chatbot_view(request):
    # 'New Chat' will just be a client-side action to clear the UI, 
    # but we can also provide a way to 'mark' the start of a new session if needed.
    # For now, we just fetch the last 30 messages for the initial load.
    msgs = list(ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:30])
    return render(request, 'core/chatbot.html', {'messages': reversed(msgs)})


@login_required
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_msg = data.get('message', '').strip()
    # Auto-detect language if not explicitly provided or if 'auto'
    lang = data.get('language', 'auto')
    if lang == 'auto' or not lang:
        lang = detect_language(user_msg)
    
    if not user_msg:
        return JsonResponse({'error': 'Empty message'}, status=400)

    profile = get_or_create_profile(request.user)
    username = request.user.username

    # Context gathering
    all_checkins = list(DailyCheckIn.objects.filter(user=request.user).order_by('-date')[:7])
    last = all_checkins[0] if all_checkins else None

    personal_context = f"- Name: {username}\n"
    if last:
        avg_screen = round(sum(c.screen_time_hours for c in all_checkins) / len(all_checkins), 1)
        personal_context += f"- Today risk: {last.risk_level}, screen: {last.screen_time_hours}h, mood: {last.mood_label}\n"
        personal_context += f"- 7-day avg screen: {avg_screen}h\n"
    else:
        personal_context += "- No recent check-in data.\n"

    # History for AI context (Long-term memory)
    history = list(ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:10])
    history_text = ''
    for h in reversed(history):
        history_text += f"User ({h.language}): {h.message}\nViora: {h.response}\n\n"

    # Summary context for assistant
    stats_summary = get_recent_stats(request.user)
    rec_workout = get_workout_rec(last.mood_label.lower() if last else 'neutral')

    prompt = f"""You are 'Viora AI', a compassionate, proactive mental wellness assistant for {username}.
The user is currently communicating in {lang}.

Context about {username}:
{personal_context}
- Recent 7-day stats: {stats_summary}
- Recommended activity: {rec_workout['title'] if rec_workout else 'Meditation'}

Recent Chat History:
{history_text}

User's New Message: "{user_msg}"

INSTRUCTIONS:
1. Respond EXCLUSIVELY in the following language: {lang}.
2. If {lang} is 'ml', use Malayalam script.
3. Be proactive: Reference their data ('I see your screen time was high') or recommend an activity ('Maybe try {rec_workout['title'] if rec_workout else 'meditation'}').
4. Be empathetic and concise (MAX 3 sentences).
5. Use the user's name ({username}) naturally.

Viora AI:"""

    ai_response = None
    try:
        if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # Safety settings to be less restrictive for wellness context if needed
            response = model.generate_content(prompt)
            if response.candidates and response.candidates[0].content.parts:
                ai_response = response.text.strip()
            
            # Clean up potential prefixes
            if ai_response:
                for pre in ['mindguard ai:', 'mindguard:', 'viora ai:', 'viora:']:
                    if ai_response.lower().startswith(pre):
                        ai_response = ai_response[len(pre):].strip()
                        break
    except Exception as e:
        print(f"Chat AI Error (Gemini): {type(e).__name__} - {e}")
        # Log to a file for deeper debugging if needed
        with open('ai_error.log', 'a', encoding='utf-8') as f:
            f.write(f"{timezone.now()} | {type(e).__name__}: {e}\n")

    # Enhanced Fallback Logic for offline/API failure/missing response
    if not ai_response:
        fallbacks = {
            'en': {
                'greeting': [f"Hello {username}! How can I help you today?", f"Hi {username}, I'm Viora AI. Ready to support you."],
                'stress': f"I'm sorry you're stressed. {stats_summary} Try a {rec_workout['title'] if rec_workout else 'meditation'}. 💙",
                'sad': f"I hear you. {stats_summary} I'm here for you, {username}. 💙",
                'happy': "That's wonderful! Keep up the great health habits. ✨",
                'exam': "Exams are stressful, but one result won't define you. Take a break. 📚",
                'family': "Family problems are tough. I'm here if you need to vent. 🫂",
                'failure': "Setbacks happen and they help us grow. Be kind to yourself, {username}. 💙",
                'stats': f"Here are your recent health stats: {stats_summary}. How do you feel about them?",
                'workout': f"Based on your mood, I recommend a session of **{rec_workout['title'] if rec_workout else 'Meditation'}**. It might help!",
                'default': f"I understand, {username}. {stats_summary} Tell me more about what's going on."
            },
            'hi': {
                'greeting': [f"नमस्ते {username}! मैं आपकी कैसे सहायता कर सकती हूँ?", f"हेलो {username}, मैं वियोरा AI हूँ।"],
                'stress': f"तनाव कम करने के लिए गहरी सांसें लें। {stats_summary} 💙",
                'sad': f"मैं आपकी बात समझ सकती हूँ। मैं आपके साथ हूँ, {username}। 💙",
                'happy': "बहुत बढ़िया! ✨",
                'exam': "परीक्षा का दबाव कठिन हो सकता है। 📚",
                'stats': f"आपका हालिया विवरण: {stats_summary}",
                'workout': f"मैं आपको **{rec_workout['title'] if rec_workout else 'Meditation'}** करने की सलाह देती हूँ।",
                'default': f"मैं समझती हूँ, {username}। {stats_summary}"
            },
            'ml': {
                'greeting': [f"നമസ്കാരം {username}! ഞാൻ എങ്ങനെ സഹായിക്കണം?", f"ഹലോ {username}, ഞാൻ Viora സഹായിയാണ്."],
                'stress': f"സ്ട്രെസ് കുറയ്ക്കാൻ 5 തവണ ആഴത്തിൽ ശ്വസിക്കൂ. {stats_summary} 💙",
                'sad': f"എനിക്ക് മനസ്സിലാകും. ഞാൻ കൂടെയുണ്ട്, {username}. 💙",
                'happy': "വളരെ സന്തോഷം! ✨",
                'exam': "പരീക്ഷാഫലം നിങ്ങളെ തളർത്താതിരിക്കട്ടെ. 📚",
                'stats': f"നിങ്ങളുടെ ആരോഗ്യ വിവരങ്ങൾ: {stats_summary}",
                'workout': f"ഞാൻ നിങ്ങൾക്ക് **{rec_workout['title'] if rec_workout else 'Meditation'}** നിർദ്ദേശിക്കുന്നു. ഇത് സമാധാനം നൽകും!",
                'default': f"എനിക്ക് മനസ്സിലാകുന്നു, {username}. {stats_summary}"
            }
        }
        
        lg = fallbacks.get(lang, fallbacks['en'])
        
        # Inject context into defaults if available
        if last:
            if last.risk_level == 'High':
                lg['default'] = f"I've noticed your risk level was high recently, {username}. Please be gentle with yourself. I'm here to listen. 💙"
            elif last.mood_label == 'Sad':
                lg['default'] = f"I know you've been feeling a bit low lately, {username}. Do you want to talk more about what's happening?"

        msg_l = user_msg.lower()
        import random

        # Keyword mapping (Prioritize emotional/crisis triggers)
        if any(w in msg_l for w in ['fail', 'lost', 'തോറ്റു', 'പരാജയം', 'നാണം', 'തോൽവി', 'फेल', 'हार']):
            ai_response = lg['failure']
        elif any(w in msg_l for w in ['parent', 'family', 'home', 'അമ്മ', 'അച്ഛൻ', 'വീട്ടിൽ', 'മാതാപിതാക്കൾ', 'വീട്ടിലേക്ക്', 'അമ്മയും', 'അച്ഛനും', 'परिवार', 'माता', 'पिता']):
            ai_response = lg['family']
        elif any(w in msg_l for w in ['exam', 'test', 'board', 'result', 'പരീക്ഷ', 'പരീക്ഷാ', 'പരീക്ഷാഫലം', 'പരീക്ഷയിൽ', 'परीक्षा']):
            ai_response = lg['exam']
        elif any(w in msg_l for w in ['stat', 'report', 'how am i', 'doing', 'health', 'നില', 'റിപ്പോർട്ട്', 'വിവരങ്ങൾ', 'സ്ഥിതി', 'ആരോഗ്യം', 'स्थिति', 'कैसा', 'स्वास्थ्य']):
            ai_response = lg['stats']
        elif any(w in msg_l for w in ['workout', 'exercise', 'training', 'yoga', 'പരിശീലനം', 'വ്യായാമം', 'യോഗ', 'व्यायाम', 'योग', 'കായികം']):
            ai_response = lg['workout']
        elif any(w in msg_l for w in ['hi', 'hello', 'hey', 'नमस्ते', 'നമസ്കാരം', 'ഹലോ', 'സുഖമാണോ']):
            ai_response = random.choice(lg['greeting'])
        elif any(w in msg_l for w in ['stress', 'anxious', 'tension', 'തनाव', 'സ്ട്രെസ്', 'പേടി', 'ആധി']):
            ai_response = lg['stress']
        elif any(w in msg_l for w in ['sad', 'bad', 'depressed', 'വിഷമം', 'സങ്കടം', 'വിഷാദം', 'വിഷാദത്തിലാണ്', 'കണ്ണീർ', 'സങ്കടത്തിലാണ്', 'दुखी', 'परेशान']):
            ai_response = lg['sad']
        elif any(w in msg_l for w in ['happy', 'good', 'സന്തോഷം', 'വിജയം', 'നല്ലത്', 'സന്തോഷത്തിലാണ്', 'खुश']):
            ai_response = lg['happy']
        else:
            ai_response = lg['default']

    # Store message
    ChatMessage.objects.create(
        user=request.user,
        message=user_msg,
        response=ai_response,
        language=lang
    )

    # Return response + history snippet
    recent_history = list(ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:10])
    history_data = [
        {'message': h.message, 'response': h.response, 'created_at': h.created_at.isoformat()}
        for h in reversed(recent_history)
    ]

    return JsonResponse({
        'response': ai_response,
        'history': history_data
    })

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
@login_required
def toggle_win(request):
    if request.method == 'POST':
        today = date.today()
        checkin = DailyCheckIn.objects.filter(user=request.user, date=today).first()
        if not checkin:
            return JsonResponse({'error': 'Please check in first to see your daily small win!'}, status=400)
            
        if not checkin.small_win_completed:
            checkin.small_win_completed = True
            checkin.save()
            profile = get_or_create_profile(request.user)
            profile.xp += 10
            profile.save()
            return JsonResponse({'status': 'done', 'xp': profile.xp})
        else:
            checkin.small_win_completed = False
            checkin.save()
            profile = get_or_create_profile(request.user)
            profile.xp -= 10
            profile.save()
            return JsonResponse({'status': 'pending', 'xp': profile.xp})
    return JsonResponse({'error': 'Invalid request'}, status=405)
