from django.views.generic import TemplateView
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count


class HomeView(TemplateView):
    """ホーム画面ビュー"""
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            user = self.request.user
            
            # QuizSessionをインポート
            from quiz.models import QuizSession
            
            # 学習統計を計算
            sessions = QuizSession.objects.filter(user=user, is_completed=True)
            today = timezone.now().date()
            today_sessions = sessions.filter(started_at__date=today)
            
            # ランクアップ進捗計算
            next_rank_info = user.get_next_rank_info()
            progress_percentage = 0
            if next_rank_info:
                progress = user.points_total - (next_rank_info['next_rank_points'] - next_rank_info['points_needed'])
                total_needed = next_rank_info['points_needed']
                if total_needed > 0:
                    progress_percentage = min((progress / total_needed) * 100, 100)
            
            context.update({
                'total_sessions': sessions.count(),
                'recent_sessions': sessions.order_by('-started_at')[:3],
                'next_rank_info': next_rank_info,
                'progress_percentage': progress_percentage,
                'today_sessions': today_sessions.count(),
                'today_progress': min((today_sessions.count() / 3) * 100, 100),
                'remaining_today': max(0, 3 - today_sessions.count()),
            })
        
        return context 