from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # 認証関連
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # プロフィール関連
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    
    # API エンドポイント
    path('api/profile/', views.user_profile_api, name='profile_api'),
    path('api/profile/update/', views.update_user_profile_api, name='profile_update_api'),
    path('api/ranking/', views.user_ranking_api, name='ranking_api'),
] 