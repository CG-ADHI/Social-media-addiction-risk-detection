from django.contrib import admin
from .models import UserProfile, DailyCheckIn, Badge, ChatMessage, FocusTask, FocusSession
admin.site.register(UserProfile)
admin.site.register(DailyCheckIn)
admin.site.register(Badge)
admin.site.register(ChatMessage)
admin.site.register(FocusTask)
admin.site.register(FocusSession)
