from django.contrib.auth.models import AbstractUser
from django.db import models


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
        return f"{self.username} ({self.rank})"
    
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
        ]
        
        for rank, points in reversed(RANK_TABLE):
            if self.points_total >= points:
                self.rank = rank
                break
        
        self.save()
        return self.rank
    
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
