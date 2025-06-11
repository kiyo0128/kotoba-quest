from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from .models import User
from .forms import CustomUserCreationForm
from django.db import models
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json


class RegisterView(CreateView):
    """ユーザー登録ビュー"""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'アカウント作成が完了しました！ことばクエストへようこそ！')
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """プロフィール表示ビュー"""
    template_name = 'accounts/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 学習統計を計算
        from quiz.models import QuizSession
        sessions = QuizSession.objects.filter(user=user, is_completed=True)
        
        context.update({
            'total_sessions': sessions.count(),
            'total_score': sum(session.score for session in sessions),
            'average_score': sessions.aggregate(avg_score=models.Avg('score'))['avg_score'] or 0,
            'recent_sessions': sessions.order_by('-started_at')[:5],
            'next_rank_info': user.get_next_rank_info(),
        })
        
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """プロフィール編集ビュー"""
    model = User
    fields = ['username', 'email']
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'プロフィールを更新しました！')
        return super().form_valid(form)


# API Views
@login_required
def user_profile_api(request):
    """ユーザープロフィール取得API"""
    user = request.user
    
    # 基本プロフィール情報
    profile_data = {
        'username': user.username,
        'email': user.email,
        'level': user.level,
        'rank': user.rank,
        'points_total': user.points_total,
        'consecutive_days': user.consecutive_days,
        'perfect_scores': user.perfect_scores,
        'created_at': user.date_joined.strftime('%Y-%m-%d'),
        'badges_earned': user.badges_earned,
    }
    
    # 進捗情報
    next_level_info = user.get_next_level_info()
    next_rank_info = user.get_next_rank_info()
    
    return JsonResponse({
        'status': 'success',
        'profile': profile_data,
        'progress': {
            'next_level_info': next_level_info,
            'next_rank_info': next_rank_info,
        }
    })


@login_required
def update_user_profile_api(request):
    """ユーザープロフィール更新API"""
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            user = request.user
            
            # 更新可能フィールド
            if 'username' in data:
                new_username = data['username'].strip()
                if new_username and new_username != user.username:
                    # ユーザー名の重複チェック
                    if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                        return JsonResponse({
                            'status': 'error',
                            'message': 'このユーザー名は既に使用されています'
                        }, status=400)
                    user.username = new_username
            
            if 'email' in data:
                user.email = data['email']
            
            user.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'プロフィールを更新しました',
                'profile': {
                    'username': user.username,
                    'email': user.email,
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '無効なJSONデータです'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'プロフィール更新に失敗しました: {str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'PUT method required'}, status=405)


@login_required
def user_ranking_api(request):
    """ユーザーランキング取得API"""
    # トップ20ユーザーを取得
    top_users = User.objects.order_by('-points_total')[:20]
    
    ranking_data = []
    for i, user in enumerate(top_users, 1):
        ranking_data.append({
            'rank': i,
            'username': user.username,
            'level': user.level,
            'rank_name': user.rank,
            'points_total': user.points_total,
            'consecutive_days': user.consecutive_days,
        })
    
    # 現在のユーザーの順位を計算
    current_user_rank = User.objects.filter(
        points_total__gt=request.user.points_total
    ).count() + 1
    
    return JsonResponse({
        'status': 'success',
        'ranking': ranking_data,
        'current_user_rank': current_user_rank,
        'total_users': User.objects.count()
    })
