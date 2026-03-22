from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    streak_days = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    last_check_in = models.DateField(null=True, blank=True)
    xp = models.IntegerField(default=0)
    notifications_enabled = models.BooleanField(default=False)
    reminder_hour = models.IntegerField(default=20)

    def get_level_info(self):
        thresholds = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 5500, 7500]
        for i, t in enumerate(thresholds):
            if self.xp < t:
                prev = thresholds[i - 1] if i > 0 else 0
                return {
                    'level': i,
                    'current_xp': self.xp - prev,
                    'needed_xp': t - prev,
                    'next_threshold': t,
                    'prev_threshold': prev,
                }
        return {
            'level': len(thresholds),
            'current_xp': 100,
            'needed_xp': 100,
            'next_threshold': 9999,
            'prev_threshold': 7500,
        }

    def __str__(self):
        return f"{self.user.username} (Lv.{self.level})"


class DailyCheckIn(models.Model):
    RISK_LEVELS = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    MOOD_CHOICES = [
        ('happy', 'Happy'), ('neutral', 'Neutral'), ('sad', 'Sad'),
        ('anxious', 'Anxious'), ('angry', 'Angry'), ('bored', 'Bored'),
        ('energetic', 'Energetic'), ('tired', 'Tired'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    # Usage
    screen_time_hours = models.FloatField(default=0)
    usage_frequency = models.IntegerField(default=0)
    sleep_disturbance = models.BooleanField(default=False)
    late_night_usage = models.BooleanField(default=False)
    app_types = models.CharField(max_length=300, blank=True)

    # Mood
    mood_rating = models.IntegerField(default=5)
    mood_label = models.CharField(max_length=20, choices=MOOD_CHOICES, default='neutral')
    journal_entry = models.TextField(blank=True)
    sentiment_score = models.FloatField(default=0)
    sentiment_label = models.CharField(max_length=20, default='neutral')

    # Risk
    risk_score = models.FloatField(default=0)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='low')
    risk_explanation = models.TextField(blank=True)

    # Productivity
    productivity_score = models.FloatField(default=0)
    focus_sessions = models.IntegerField(default=0)
    tasks_completed = models.IntegerField(default=0)
    tasks_total = models.IntegerField(default=0)

    # AI
    ai_suggestions = models.TextField(blank=True, default='[]')
    emotional_insight = models.TextField(blank=True)

    # XP
    xp_earned = models.IntegerField(default=0)

    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.risk_level}"


class FocusTask(models.Model):
    PRIORITY_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    STATUS_CHOICES = [('pending', 'Pending'), ('done', 'Done'), ('skipped', 'Skipped')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    title = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date', 'priority']

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.status})"


class Badge(models.Model):
    BADGE_TYPES = [
        ('streak', 'Streak'), ('detox', 'Digital Detox'),
        ('mood', 'Mood'), ('productivity', 'Productivity'),
        ('journal', 'Journal'), ('boss', 'Boss Level'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge_type = models.CharField(max_length=30, choices=BADGE_TYPES)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, default='🏆')
    rarity = models.CharField(max_length=20, default='common')
    xp_reward = models.IntegerField(default=50)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'name']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    mood_context = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.created_at:%Y-%m-%d %H:%M}"


class FocusSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    duration_minutes = models.IntegerField(default=25)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.duration_minutes}min"
