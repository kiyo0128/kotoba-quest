from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    # クイズ画面
    path('start/', views.QuizStartView.as_view(), name='start'),
    path('game/<int:session_id>/', views.QuizGameView.as_view(), name='game'),
    path('result/<int:session_id>/', views.QuizResultView.as_view(), name='result'),
    path('history/', views.QuizHistoryView.as_view(), name='history'),
    
    # API エンドポイント
    path('api/start/', views.start_quiz_api, name='start_api'),
    path('api/answer/', views.submit_answer_api, name='answer_api'),
    path('api/finish/', views.finish_quiz_api, name='finish_api'),
    path('api/stats/', views.quiz_stats_api, name='stats_api'),
    path('api/history/', views.quiz_history_api, name='history_api'),
    
    # 旧エンドポイント（後方互換性）
    path('', views.home, name='home'),
    path('api/profile/', views.get_user_profile, name='user_profile'),
] 