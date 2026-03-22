"""MindGuard Analytics Engine v2"""
import re


# ── Sentiment Analysis ────────────────────────────────────────────────────────
POSITIVE = {
    'happy', 'great', 'amazing', 'wonderful', 'good', 'excited', 'joy', 'love',
    'excellent', 'fantastic', 'awesome', 'blessed', 'grateful', 'calm', 'peaceful',
    'motivated', 'energetic', 'productive', 'cheerful', 'optimistic', 'confident',
    'relaxed', 'content', 'pleased', 'delighted', 'thrilled', 'ecstatic', 'proud',
    'refreshed', 'inspired', 'focused', 'hopeful', 'strong', 'better', 'positive',
}

NEGATIVE = {
    'sad', 'depressed', 'anxious', 'stressed', 'overwhelmed', 'tired', 'exhausted',
    'lonely', 'hopeless', 'worthless', 'angry', 'frustrated', 'irritated', 'bored',
    'empty', 'numb', 'miserable', 'terrible', 'awful', 'horrible', 'worried',
    'scared', 'lost', 'stuck', 'hate', 'crying', 'pain', 'hurt', 'broken',
    'failed', 'failure', 'useless', 'drained', 'addicted', 'wasted', 'distracted',
    'unfocused', 'lazy', 'guilty', 'shame', 'regret', 'negative', 'bad', 'worse',
}

INTENSIFIERS = {'very', 'really', 'extremely', 'so', 'absolutely', 'totally', 'super', 'incredibly'}


def analyze_sentiment(text):
    """Returns sentiment score (-1 to 1) and label."""
    if not text or not text.strip():
        return {'score': 0.0, 'label': 'neutral'}
    words = re.findall(r'\b\w+\b', text.lower())
    pos, neg = 0, 0
    for i, w in enumerate(words):
        boost = 1.5 if (i > 0 and words[i - 1] in INTENSIFIERS) else 1.0
        if w in POSITIVE:
            pos += boost
        elif w in NEGATIVE:
            neg += boost
    total = pos + neg
    score = round((pos - neg) / total, 3) if total else 0.0
    label = 'positive' if score > 0.15 else ('negative' if score < -0.15 else 'neutral')
    return {'score': score, 'label': label}


# ── Risk Engine ───────────────────────────────────────────────────────────────
def calculate_risk(data):
    """Score addiction risk 0-100 from usage data."""
    score = 0
    flags = []

    st = float(data.get('screen_time_hours', 0))
    if st > 8:
        score += 35; flags.append("extreme screen time (8+ hrs)")
    elif st > 6:
        score += 27; flags.append("very high screen time (6-8 hrs)")
    elif st > 4:
        score += 18; flags.append("high screen time (4-6 hrs)")
    elif st > 2:
        score += 9;  flags.append("moderate screen time")
    else:
        score += 2

    freq = int(data.get('usage_frequency', 0))
    if freq > 50:
        score += 20; flags.append("compulsive checking (50+/day)")
    elif freq > 30:
        score += 14; flags.append("very frequent checking")
    elif freq > 15:
        score += 8;  flags.append("frequent app-checking habit")
    elif freq > 8:
        score += 4

    if data.get('sleep_disturbance'):
        score += 10; flags.append("sleep disrupted by phone")
    if data.get('late_night_usage'):
        score += 6;  flags.append("late-night scrolling")

    mood = int(data.get('mood_rating', 5))
    if mood <= 2:
        score += 15; flags.append("very low mood")
    elif mood <= 4:
        score += 10; flags.append("low mood")
    elif mood <= 6:
        score += 4

    apps = data.get('app_types', [])
    if isinstance(apps, str):
        apps = [apps]
    high_risk = {'reels', 'tiktok', 'gaming', 'gambling', 'shorts'}
    if any(a.lower() in high_risk for a in apps):
        score += 10; flags.append("high-dopamine content")
    if len(apps) > 3:
        score += 5; flags.append("multi-platform overuse")

    score = min(round(score, 1), 100)

    if score >= 60:
        level = 'high'
        explanation = f"⚠️ You show signs of {', '.join(flags[:3])}. Immediate action recommended."
    elif score >= 30:
        level = 'medium'
        explanation = f"⚡ Moderate concern: {', '.join(flags[:2])}. Build better boundaries."
    else:
        level = 'low'
        explanation = "✅ Your habits look healthy. Keep up the great work!"

    return {
        'risk_score': score,
        'risk_level': level,
        'risk_explanation': explanation,
        'flags': flags,
    }


# ── Productivity Score ────────────────────────────────────────────────────────
def calculate_productivity(tasks_completed, tasks_total, screen_time, focus_sessions, mood_rating):
    """Calculate daily productivity score 0-100."""
    score = 0
    feedback = []

    # Task completion (40 pts max)
    if tasks_total > 0:
        ratio = tasks_completed / tasks_total
        score += ratio * 40
        if ratio == 1.0:
            feedback.append("🎯 All tasks completed — outstanding!")
        elif ratio >= 0.5:
            feedback.append(f"📋 {tasks_completed}/{tasks_total} tasks completed")
        else:
            feedback.append(f"📋 Only {tasks_completed}/{tasks_total} tasks done — push harder tomorrow")
    else:
        # No tasks set — give partial credit
        score += 10
        feedback.append("📋 Set up to 3 focus tasks tomorrow for more points")

    # Screen time (30 pts max)
    if screen_time <= 2:
        score += 30; feedback.append("📵 Excellent screen discipline")
    elif screen_time <= 4:
        score += 20; feedback.append("📱 Decent screen time — aim for under 2h")
    elif screen_time <= 6:
        score += 10; feedback.append("⚠️ High screen time is hurting productivity")
    else:
        score += 0;  feedback.append("🚨 Reduce screen time significantly tomorrow")

    # Focus sessions (20 pts max)
    pts = min(focus_sessions * 5, 20)
    score += pts
    if focus_sessions > 0:
        feedback.append(f"⏱ {focus_sessions} focus session(s) completed")
    else:
        feedback.append("⏱ Try the Pomodoro timer for focused work")

    # Mood (10 pts max)
    score += (mood_rating / 10) * 10

    score = min(round(score, 1), 100)

    if score >= 80:
        overall = "Excellent day! 🌟"
    elif score >= 60:
        overall = "Good progress! 💪"
    elif score >= 40:
        overall = "Room to improve 📈"
    else:
        overall = "Tomorrow is a new chance 🌅"

    return {'score': score, 'feedback': feedback, 'overall': overall}


# ── Emotional Insights ────────────────────────────────────────────────────────
def generate_emotional_insight(checkins):
    """Generate psychological insights from recent check-in data."""
    if not checkins:
        return None

    recent = list(checkins[:7])
    if len(recent) < 3:
        return None

    insights = []

    high_screen = [c for c in recent if c.screen_time_hours > 4]
    low_screen  = [c for c in recent if c.screen_time_hours <= 2]

    if high_screen and low_screen:
        avg_mood_high = sum(c.mood_rating for c in high_screen) / len(high_screen)
        avg_mood_low  = sum(c.mood_rating for c in low_screen)  / len(low_screen)
        if avg_mood_low > avg_mood_high + 0.8:
            insights.append({
                'icon': '🔗',
                'title': 'Screen Time & Mood Are Linked',
                'text': (
                    f'You rate your mood {avg_mood_low - avg_mood_high:.1f} points higher '
                    f'on low-screen days. Less scrolling = better feelings.'
                ),
                'color': 'teal',
            })

    neg_days = [c for c in recent if c.sentiment_label == 'negative']
    if len(neg_days) >= 3:
        insights.append({
            'icon': '💭',
            'title': 'Emotional Heaviness Detected',
            'text': (
                f'{len(neg_days)} of your recent journal entries show negative sentiment. '
                f'Consider talking to someone you trust.'
            ),
            'color': 'red',
        })

    risk_scores = [c.risk_score for c in recent if c.risk_score > 0]
    if len(risk_scores) >= 3:
        trend = risk_scores[0] - risk_scores[-1]
        if trend < -5:
            insights.append({
                'icon': '📉',
                'title': 'Risk Score Declining — Great!',
                'text': f'Your addiction risk dropped {abs(trend):.0f} points this week. Real progress!',
                'color': 'green',
            })
        elif trend > 5:
            insights.append({
                'icon': '📈',
                'title': 'Risk Score Increasing — Take Action',
                'text': f'Your risk score rose {trend:.0f} points this week. Time to reset boundaries.',
                'color': 'amber',
            })

    prod_scores = [c.productivity_score for c in recent if c.productivity_score > 0]
    if prod_scores and (sum(prod_scores) / len(prod_scores)) < 50:
        insights.append({
            'icon': '⚡',
            'title': 'Productivity Needs a Boost',
            'text': (
                'Your average productivity score is below 50. '
                'Try completing 1 high-priority task before picking up your phone.'
            ),
            'color': 'purple',
        })

    return insights if insights else None


# ── Activity Recommendations ──────────────────────────────────────────────────
WORKOUTS = {
    'breathing': {
        'title': 'Box Breathing',
        'icon': '🫁',
        'duration': '5 min',
        'desc': 'Calm your nervous system with 4-4-4-4 breath pattern',
        'steps': [
            'Sit comfortably with your back straight',
            'Inhale slowly for 4 counts',
            'Hold your breath for 4 counts',
            'Exhale fully for 4 counts',
            'Hold empty for 4 counts — repeat 5 times',
        ],
        'demo_type': 'breathing',
        'for_mood': ['angry', 'anxious'],
    },
    'walk': {
        'title': 'Mindful Walk',
        'icon': '🚶',
        'duration': '10-15 min',
        'desc': 'Step outside without your phone for a full reset',
        'steps': [
            'Put your phone inside — no earphones either',
            'Step outside and feel the air on your skin',
            'Notice 5 things you can see around you',
            'Walk at a natural, relaxed pace',
            'When urge to check phone arises — breathe and keep walking',
        ],
        'demo_type': 'walk',
        'for_mood': ['sad', 'bored', 'tired'],
    },
    'stretching': {
        'title': 'Desk Stretch Sequence',
        'icon': '🙆',
        'duration': '7 min',
        'desc': 'Release tension from head to toe at your desk',
        'steps': [
            'Neck rolls — 5 slow circles each side',
            'Shoulder shrugs — lift to ears, hold 3s, release × 10',
            'Wrist circles — 10 each direction',
            'Seated spinal twist — hold 20 seconds each side',
            'Forward fold — chin to chest, hang heavy for 30 seconds',
        ],
        'demo_type': 'stretching',
        'for_mood': ['tired', 'neutral', 'anxious'],
    },
    'hiit': {
        'title': 'Energy Burst HIIT',
        'icon': '⚡',
        'duration': '10 min',
        'desc': 'Release natural dopamine with a quick high-intensity circuit',
        'steps': [
            '20 jumping jacks — full extension',
            '15 squats — chest up, parallel depth',
            '10 push-ups — or knee push-ups',
            '30 second plank — breathe steadily',
            'Rest 60 seconds — then repeat once more',
        ],
        'demo_type': 'hiit',
        'for_mood': ['angry', 'bored', 'energetic'],
    },
    'meditation': {
        'title': 'Body Scan Meditation',
        'icon': '🧘',
        'duration': '8 min',
        'desc': 'Travel through your body and release stored tension',
        'steps': [
            'Lie down or sit very comfortably',
            'Close your eyes and take 3 deep slow breaths',
            'Bring awareness to your feet — notice any tension',
            'Slowly scan upward: legs, belly, chest, shoulders, face',
            'End with 3 grateful breaths — open eyes slowly',
        ],
        'demo_type': 'meditation',
        'for_mood': ['anxious', 'angry', 'sad'],
    },
    'journaling': {
        'title': 'Structured Journaling',
        'icon': '📔',
        'duration': '10 min',
        'desc': 'Process your emotions with a proven 4-prompt framework',
        'steps': [
            'Write 3 things you are genuinely grateful for today',
            'Describe one challenge you faced honestly',
            'Write what you would do differently if you could',
            'End with one positive affirmation about yourself',
        ],
        'demo_type': 'journal',
        'for_mood': ['sad', 'neutral', 'tired'],
    },
    'learning': {
        'title': 'Micro-Learning Session',
        'icon': '🎓',
        'duration': '15 min',
        'desc': 'Feed your curiosity offline and train your focus muscle',
        'steps': [
            'Pick one topic you have been curious about',
            'Open a book, article, or educational app (no social media)',
            'Take handwritten notes — this boosts retention 40%',
            'Summarize what you learned in 3 sentences',
            'Share it with someone or save it to revisit',
        ],
        'demo_type': 'learn',
        'for_mood': ['bored', 'neutral', 'energetic'],
    },
    'cold_water': {
        'title': 'Cold Water Reset',
        'icon': '💧',
        'duration': '2 min',
        'desc': 'Instant nervous system reset using cold water',
        'steps': [
            'Fill a glass with ice cold water',
            'Splash cold water on your face 5 times',
            'Drink the full glass slowly',
            'Take 5 slow deep breaths through your nose',
            'Notice how different you feel now vs 2 minutes ago',
        ],
        'demo_type': 'water',
        'for_mood': ['angry', 'tired', 'anxious'],
    },
}

MOOD_ACTIVITY_MAP = {
    'happy':    ['learning', 'hiit', 'journaling'],
    'neutral':  ['meditation', 'walk', 'learning'],
    'sad':      ['journaling', 'walk', 'cold_water'],
    'anxious':  ['breathing', 'meditation', 'cold_water'],
    'angry':    ['hiit', 'breathing', 'cold_water'],
    'bored':    ['learning', 'hiit', 'walk'],
    'energetic': ['hiit', 'learning', 'journaling'],
    'tired':    ['stretching', 'cold_water', 'meditation'],
}

RISK_EXTRA_MAP = {
    'high':   ['breathing', 'walk', 'meditation'],
    'medium': ['journaling', 'stretching'],
    'low':    ['learning', 'hiit'],
}


def get_activities(risk_level, mood_label):
    """Return list of recommended workout dicts for the given risk/mood combo."""
    keys = list(dict.fromkeys(
        MOOD_ACTIVITY_MAP.get(mood_label, ['meditation', 'walk', 'journaling']) +
        RISK_EXTRA_MAP.get(risk_level, [])
    ))[:4]
    return [WORKOUTS[k] for k in keys if k in WORKOUTS]


# ── XP Calculation ────────────────────────────────────────────────────────────
def calculate_xp(checkin, tasks_completed):
    """Calculate XP earned from a single check-in."""
    xp = 20  # base for checking in
    if checkin.risk_level == 'low':
        xp += 40
    elif checkin.risk_level == 'medium':
        xp += 20
    if checkin.journal_entry:
        xp += 25
    if checkin.screen_time_hours < 2:
        xp += 50
    if checkin.screen_time_hours < 1:
        xp += 30  # bonus
    if checkin.mood_rating >= 8:
        xp += 20
    if tasks_completed > 0:
        xp += tasks_completed * 15
    if checkin.focus_sessions > 0:
        xp += checkin.focus_sessions * 10
    return xp


# ── Badge Definitions ─────────────────────────────────────────────────────────
BADGE_DEFINITIONS = [
    {
        'name': 'First Step',
        'icon': '👣', 'type': 'streak', 'rarity': 'common', 'xp': 30,
        'check': lambda p, c, all_c: p.streak_days >= 1,
    },
    {
        'name': 'Week Warrior',
        'icon': '🔥', 'type': 'streak', 'rarity': 'rare', 'xp': 100,
        'check': lambda p, c, all_c: p.streak_days >= 7,
    },
    {
        'name': 'Month Master',
        'icon': '💎', 'type': 'streak', 'rarity': 'epic', 'xp': 300,
        'check': lambda p, c, all_c: p.streak_days >= 30,
    },
    {
        'name': 'Unstoppable',
        'icon': '⚡', 'type': 'streak', 'rarity': 'legendary', 'xp': 700,
        'check': lambda p, c, all_c: p.streak_days >= 90,
    },
    {
        'name': 'Light Touch',
        'icon': '📵', 'type': 'detox', 'rarity': 'common', 'xp': 50,
        'check': lambda p, c, all_c: c.screen_time_hours <= 1,
    },
    {
        'name': 'Digital Monk',
        'icon': '🧘', 'type': 'detox', 'rarity': 'epic', 'xp': 200,
        'check': lambda p, c, all_c: sum(1 for x in all_c if x.screen_time_hours <= 1) >= 7,
    },
    {
        'name': 'Mood Tracker',
        'icon': '🌈', 'type': 'mood', 'rarity': 'common', 'xp': 40,
        'check': lambda p, c, all_c: len(list(all_c)) >= 5,
    },
    {
        'name': 'Inner Peace',
        'icon': '☮️', 'type': 'mood', 'rarity': 'rare', 'xp': 150,
        'check': lambda p, c, all_c: sum(1 for x in all_c if x.mood_rating >= 8) >= 5,
    },
    {
        'name': 'Wordsmith',
        'icon': '✍️', 'type': 'journal', 'rarity': 'rare', 'xp': 80,
        'check': lambda p, c, all_c: sum(1 for x in all_c if x.journal_entry) >= 7,
    },
    {
        'name': 'Task Crusher',
        'icon': '🎯', 'type': 'productivity', 'rarity': 'rare', 'xp': 100,
        'check': lambda p, c, all_c: c.tasks_completed >= 3,
    },
    {
        'name': 'Flow State',
        'icon': '🌊', 'type': 'productivity', 'rarity': 'epic', 'xp': 200,
        'check': lambda p, c, all_c: c.focus_sessions >= 4,
    },
    {
        'name': 'Productivity God',
        'icon': '👑', 'type': 'boss', 'rarity': 'legendary', 'xp': 500,
        'check': lambda p, c, all_c: c.productivity_score >= 90,
    },
]


def check_and_award_badges(user, profile, checkin, all_checkins):
    """Check all badge conditions and award any newly earned badges."""
    from core.models import Badge
    awarded = []
    all_c = list(all_checkins)
    for defn in BADGE_DEFINITIONS:
        if Badge.objects.filter(user=user, name=defn['name']).exists():
            continue
        try:
            if defn['check'](profile, checkin, all_c):
                b = Badge.objects.create(
                    user=user,
                    badge_type=defn['type'],
                    name=defn['name'],
                    icon=defn['icon'],
                    description=f"Earned: {defn['name']}",
                    rarity=defn['rarity'],
                    xp_reward=defn['xp'],
                )
                profile.xp += defn['xp']
                awarded.append(b)
        except Exception:
            pass
    if awarded:
        profile.save()
    return awarded
