from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta


class User(AbstractUser):
    """
    小学1年生向け国語クイズアプリのカスタムユーザーモデル
    """
    points_total = models.PositiveIntegerField(
        default=0,
        verbose_name="総ポイント数",
        help_text="ユーザーが獲得した総ポイント数"
    )
    
    rank = models.CharField(
        max_length=20,
        default="ノーマル",
        verbose_name="現在のランク",
        help_text="現在のユーザーのランク"
    )
    
    # 新しいバッジ関連フィールド
    badges_earned = models.JSONField(
        default=list,
        verbose_name="獲得バッジリスト",
        help_text="獲得したバッジのリスト"
    )
    
    level = models.PositiveIntegerField(
        default=1,
        verbose_name="レベル",
        help_text="現在のユーザーレベル"
    )
    
    experience_points = models.PositiveIntegerField(
        default=0,
        verbose_name="経験値",
        help_text="レベルアップ用の経験値"
    )
    
    # 統計データ
    consecutive_days = models.PositiveIntegerField(
        default=0,
        verbose_name="連続学習日数",
        help_text="連続で学習した日数"
    )
    
    last_study_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="最終学習日",
        help_text="最後に学習した日付"
    )
    
    perfect_scores = models.PositiveIntegerField(
        default=0,
        verbose_name="満点回数",
        help_text="満点を取った回数"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時"
    )

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
        
    def __str__(self):
        return f"{self.username} (Lv.{self.level} {self.rank})"
    
    def update_rank(self):
        """
        ポイント数に基づいてランクを更新する
        """
        RANK_TABLE = [
            ("ノーマル", 0),
            ("コモン", 100),
            ("レア", 300),
            ("エピック", 700),
            ("レジェンダリー", 1500),
            ("ミシック", 3000),
            ("ゴッド", 5000),
        ]
        
        old_rank = self.rank
        for rank, points in reversed(RANK_TABLE):
            if self.points_total >= points:
                self.rank = rank
                break
        
        # save()は呼び出し元で行う
        return old_rank != self.rank  # ランクアップしたかどうか
    
    def update_level(self, points_earned):
        """
        経験値を追加してレベルを更新する
        """
        old_level = self.level
        self.experience_points += points_earned
        
        # レベルアップ計算（100経験値で1レベルアップ）
        new_level = min((self.experience_points // 100) + 1, 99)  # 最大レベル99
        level_up = new_level > old_level
        self.level = new_level
        
        # save()は呼び出し元で行う
        return level_up
    
    def get_next_rank_info(self):
        """
        次のランクまでの情報を取得する
        """
        RANK_TABLE = [
            ("ノーマル", 0),
            ("コモン", 100),
            ("レア", 300),
            ("エピック", 700),
            ("レジェンダリー", 1500),
            ("ミシック", 3000),
            ("ゴッド", 5000),
        ]
        
        current_rank_index = None
        for i, (rank, points) in enumerate(RANK_TABLE):
            if rank == self.rank:
                current_rank_index = i
                break
        
        if current_rank_index is None or current_rank_index == len(RANK_TABLE) - 1:
            return None  # 最高ランクまたは不明
        
        next_rank, next_points = RANK_TABLE[current_rank_index + 1]
        points_needed = next_points - self.points_total
        
        return {
            'next_rank': next_rank,
            'points_needed': points_needed,
            'next_rank_points': next_points
        }
    
    def get_next_level_info(self):
        """
        次のレベルまでの情報を取得する
        """
        if self.level >= 99:
            return None  # 最大レベル
        
        current_level_exp = (self.level - 1) * 100
        next_level_exp = self.level * 100
        exp_needed = next_level_exp - self.experience_points
        
        return {
            'next_level': self.level + 1,
            'exp_needed': exp_needed,
            'current_exp': self.experience_points - current_level_exp,
            'level_exp_total': 100
        }
    
    def check_new_badges(self, quiz_session=None):
        """
        新しいバッジの獲得をチェックする
        """
        new_badges = []
        current_badges = set(self.badges_earned)
        
        # バッジ定義
        BADGE_CONDITIONS = {
            'first_quiz': {
                'name': '初心者',
                'description': '初めてのクイズ完了',
                'icon': 'star',
                'color': 'primary',
                'condition': lambda user, session: True  # 初回クイズ
            },
            'perfect_score': {
                'name': 'パーフェクト',
                'description': '満点獲得',
                'icon': 'trophy',
                'color': 'warning',
                'condition': lambda user, session: session and session.score == 10
            },
            'speed_master': {
                'name': 'スピードマスター',
                'description': '3分以内でクリア',
                'icon': 'bolt',
                'color': 'success',
                'condition': lambda user, session: session and session.finished_at and session.started_at and (session.finished_at - session.started_at).total_seconds() < 180
            },
            'streak_3': {
                'name': '継続の力',
                'description': '3日連続学習',
                'icon': 'fire',
                'color': 'danger',
                'condition': lambda user, session: user.consecutive_days >= 3
            },
            'streak_7': {
                'name': '一週間の努力',
                'description': '7日連続学習',
                'icon': 'calendar-check',
                'color': 'info',
                'condition': lambda user, session: user.consecutive_days >= 7
            },
            'streak_30': {
                'name': '継続王',
                'description': '30日連続学習',
                'icon': 'crown',
                'color': 'warning',
                'condition': lambda user, session: user.consecutive_days >= 30
            },
            'point_collector_100': {
                'name': 'ポイントコレクター',
                'description': '100ポイント獲得',
                'icon': 'coins',
                'color': 'warning',
                'condition': lambda user, session: user.points_total >= 100
            },
            'point_collector_500': {
                'name': 'ポイントマスター',
                'description': '500ポイント獲得', 
                'icon': 'gem',
                'color': 'success',
                'condition': lambda user, session: user.points_total >= 500
            },
            'point_collector_1000': {
                'name': 'ポイントキング',
                'description': '1000ポイント獲得',
                'icon': 'diamond',
                'color': 'primary',
                'condition': lambda user, session: user.points_total >= 1000
            },
            'level_up_5': {
                'name': 'レベル5到達',
                'description': 'レベル5に到達',
                'icon': 'arrow-up',
                'color': 'info',
                'condition': lambda user, session: user.level >= 5
            },
            'level_up_10': {
                'name': 'レベル10到達',
                'description': 'レベル10に到達',
                'icon': 'mountain',
                'color': 'success',
                'condition': lambda user, session: user.level >= 10
            },
            'perfect_streak_3': {
                'name': '完璧主義者',
                'description': '3回連続満点',
                'icon': 'bullseye',
                'color': 'danger',
                'condition': lambda user, session: user.perfect_scores >= 3
            }
        }
        
        for badge_id, badge_info in BADGE_CONDITIONS.items():
            if badge_id not in current_badges:
                if badge_info['condition'](self, quiz_session):
                    new_badges.append({
                        'id': badge_id,
                        **{k: v for k, v in badge_info.items() if k != 'condition'}
                    })
                    self.badges_earned.append(badge_id)
        
        # save()は呼び出し元で行う
        return new_badges
    
    def update_consecutive_days(self):
        """
        連続学習日数を更新する
        """
        today = timezone.now().date()
        
        if self.last_study_date is None:
            # 初回学習
            self.consecutive_days = 1
            self.last_study_date = today
        elif self.last_study_date == today:
            # 今日は既に学習済み
            pass
        elif self.last_study_date == today - timedelta(days=1):
            # 昨日に続いて今日も学習
            self.consecutive_days += 1
            self.last_study_date = today
        else:
            # 連続が途切れた
            self.consecutive_days = 1
            self.last_study_date = today
        
        # save()は呼び出し元で行う
        return self.consecutive_days


class Badge(models.Model):
    """
    バッジマスターデータ（将来的な拡張用）
    """
    badge_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "バッジ"
        verbose_name_plural = "バッジ"
    
    def __str__(self):
        return self.name
