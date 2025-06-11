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
            
            # レベル情報も取得
            next_level_info = user.get_next_level_info()
            level_progress = 0
            if next_level_info:
                level_progress = (next_level_info['current_exp'] / next_level_info['level_exp_total']) * 100
            
            # ユーザーのバッジ情報を取得
            user_badges = []
            BADGE_INFO = {
                'first_quiz': {'name': '初心者', 'description': '初めてのクイズ完了', 'icon': 'star', 'color': 'primary'},
                'perfect_score': {'name': 'パーフェクト', 'description': '満点獲得', 'icon': 'trophy', 'color': 'warning'},
                'speed_master': {'name': 'スピードマスター', 'description': '3分以内でクリア', 'icon': 'bolt', 'color': 'success'},
                'streak_3': {'name': '継続の力', 'description': '3日連続学習', 'icon': 'fire', 'color': 'danger'},
                'streak_7': {'name': '一週間の努力', 'description': '7日連続学習', 'icon': 'calendar-check', 'color': 'info'},
                'streak_30': {'name': '継続王', 'description': '30日連続学習', 'icon': 'crown', 'color': 'warning'},
                'point_collector_100': {'name': 'ポイントコレクター', 'description': '100ポイント獲得', 'icon': 'coins', 'color': 'warning'},
                'point_collector_500': {'name': 'ポイントマスター', 'description': '500ポイント獲得', 'icon': 'gem', 'color': 'success'},
                'point_collector_1000': {'name': 'ポイントキング', 'description': '1000ポイント獲得', 'icon': 'diamond', 'color': 'primary'},
                'level_up_5': {'name': 'レベル5到達', 'description': 'レベル5に到達', 'icon': 'arrow-up', 'color': 'info'},
                'level_up_10': {'name': 'レベル10到達', 'description': 'レベル10に到達', 'icon': 'mountain', 'color': 'success'},
                'perfect_streak_3': {'name': '完璧主義者', 'description': '3回連続満点', 'icon': 'bullseye', 'color': 'danger'},
            }
            
            for badge_id in user.badges_earned:
                if badge_id in BADGE_INFO:
                    user_badges.append(BADGE_INFO[badge_id])
            
            context.update({
                'total_sessions': sessions.count(),
                'recent_sessions': sessions.order_by('-started_at')[:3],
                'next_rank_info': next_rank_info,
                'next_level_info': next_level_info,
                'progress_percentage': progress_percentage,
                'level_progress': round(level_progress, 1),
                'today_sessions': today_sessions.count(),
                'today_progress': min((today_sessions.count() / 3) * 100, 100),
                'remaining_today': max(0, 3 - today_sessions.count()),
                'user_badges': user_badges[:8],  # 最大8個まで表示
            })
        
        return context 