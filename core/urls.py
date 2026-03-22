from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('checkin/', views.checkin, name='checkin'),
    path('chat/', views.chatbot, name='chatbot'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/tasks/', views.task_api, name='task_api'),
    path('api/focus-session/', views.focus_session_api, name='focus_session_api'),
    path('workouts/', views.workouts_page, name='workouts'),
    path('workout/<str:key>/', views.workout_detail, name='workout_detail'),
    path('history/', views.history, name='history'),
    path('profile/', views.profile_view, name='profile'),
]
