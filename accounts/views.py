from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib import messages
from django.urls import reverse_lazy
from .models import User
from .forms import CustomUserCreationForm
from django.db import models


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
