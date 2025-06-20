from django.db import models
from django.conf import settings
from django.utils import timezone


class QuizSession(models.Model):
    """
    クイズセッション（1回のクイズゲーム）
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="ユーザー",
        related_name="quiz_sessions"
    )
    
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="開始日時"
    )
    
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="終了日時"
    )
    
    score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="スコア（正解数）"
    )
    
    points_earned = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="獲得ポイント"
    )
    
    is_completed = models.BooleanField(
        default=False,
        verbose_name="完了フラグ"
    )

    class Meta:
        verbose_name = "クイズセッション"
        verbose_name_plural = "クイズセッション"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.started_at.strftime('%Y/%m/%d %H:%M')}"
    
    def calculate_score(self):
        """
        正解数を計算する
        """
        correct_answers = self.questions.filter(answers__is_correct=True).count()
        self.score = correct_answers
        self.points_earned = correct_answers * 10  # 1問正解につき10ポイント
        self.save()
        return self.score
    
    def finish_session(self):
        """
        セッションを終了し、ユーザーのポイント・レベル・バッジを更新する
        """
        if not self.is_completed:
            self.finished_at = timezone.now()
            self.is_completed = True
            self.calculate_score()
            
            # 満点かどうかをチェック
            if self.score == 10:
                self.user.perfect_scores += 1
            
            # 連続学習日数を更新
            self.user.update_consecutive_days()
            
            # ユーザーの総ポイントを更新
            self.user.points_total += self.points_earned
            
            # レベルアップ処理
            level_up = self.user.update_level(self.points_earned)
            
            # ランクアップ処理
            rank_up = self.user.update_rank()
            
            # 新しいバッジをチェック
            new_badges = self.user.check_new_badges(self)
            
            self.user.save()
            self.save()
            
            # 結果を辞書で返す
            return {
                'score': self.score,
                'points_earned': self.points_earned,
                'level_up': level_up,
                'rank_up': rank_up,
                'new_badges': new_badges,
                'user_level': self.user.level,
                'user_rank': self.user.rank,
                'consecutive_days': self.user.consecutive_days
            }
        
        return {'score': self.score}


class Question(models.Model):
    """
    クイズの問題
    """
    QUESTION_TYPES = [
        ('language', '国語'),
        ('math', '算数'),
    ]
    
    ANSWER_FORMATS = [
        ('multiple_choice', '選択問題'),
        ('numeric', '数値入力'),
    ]
    
    session = models.ForeignKey(
        QuizSession,
        on_delete=models.CASCADE,
        verbose_name="セッション",
        related_name="questions"
    )
    
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='language',
        verbose_name="問題タイプ"
    )
    
    answer_format = models.CharField(
        max_length=20,
        choices=ANSWER_FORMATS,
        default='multiple_choice',
        verbose_name="回答形式"
    )
    
    text = models.TextField(
        verbose_name="問題文",
        help_text="小学1年生レベルの問題文"
    )
    
    choices = models.JSONField(
        verbose_name="選択肢",
        help_text="選択肢のリスト（選択問題の場合）",
        default=list,
        blank=True
    )
    
    correct_idx = models.PositiveSmallIntegerField(
        verbose_name="正解のインデックス",
        help_text="正解の選択肢のインデックス（選択問題の場合）",
        null=True,
        blank=True
    )
    
    correct_value = models.IntegerField(
        verbose_name="正解の数値",
        help_text="正解の数値（数値入力問題の場合）",
        null=True,
        blank=True
    )
    
    question_number = models.PositiveSmallIntegerField(
        verbose_name="問題番号",
        help_text="セッション内での問題番号（1-10）"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時"
    )

    class Meta:
        verbose_name = "問題"
        verbose_name_plural = "問題"
        ordering = ['question_number']
        unique_together = ['session', 'question_number']
    
    def __str__(self):
        return f"問題{self.question_number}: {self.text[:30]}..."
    
    def get_correct_answer(self):
        """
        正解の選択肢または数値を取得する
        """
        if self.answer_format == 'numeric':
            return self.correct_value
        elif self.answer_format == 'multiple_choice' and self.correct_idx is not None:
            if 0 <= self.correct_idx < len(self.choices):
                return self.choices[self.correct_idx]
        return None


class Answer(models.Model):
    """
    ユーザーの回答
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        verbose_name="問題",
        related_name="answers"
    )
    
    selected_idx = models.PositiveSmallIntegerField(
        verbose_name="選択した回答のインデックス",
        help_text="ユーザーが選択した選択肢のインデックス（選択問題の場合）",
        null=True,
        blank=True
    )
    
    numeric_answer = models.IntegerField(
        verbose_name="数値回答",
        help_text="ユーザーが入力した数値（数値入力問題の場合）",
        null=True,
        blank=True
    )
    
    is_correct = models.BooleanField(
        verbose_name="正解フラグ"
    )
    
    answered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="回答日時"
    )

    class Meta:
        verbose_name = "回答"
        verbose_name_plural = "回答"
        unique_together = ['question']  # 1つの問題に対して1つの回答のみ
    
    def __str__(self):
        result = "正解" if self.is_correct else "不正解"
        return f"{self.question} - {result}"
    
    def save(self, *args, **kwargs):
        """
        保存時に正解判定を行う
        """
        if self.question.answer_format == 'numeric':
            self.is_correct = self.numeric_answer == self.question.correct_value
        elif self.question.answer_format == 'multiple_choice':
            self.is_correct = self.selected_idx == self.question.correct_idx
        else:
            self.is_correct = False
        super().save(*args, **kwargs)


class PreGeneratedQuestion(models.Model):
    """事前生成された高品質問題"""
    QUESTION_TYPES = [
        ('language', '国語'),
        ('math', '算数'),
    ]
    
    ANSWER_FORMATS = [
        ('multiple_choice', '選択問題'),
        ('numeric', '数値入力'),
    ]
    
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='language',
        verbose_name="問題タイプ"
    )
    
    answer_format = models.CharField(
        max_length=20,
        choices=ANSWER_FORMATS,
        default='multiple_choice',
        verbose_name="回答形式"
    )
    
    question_text = models.TextField(verbose_name="問題文")
    choice_1 = models.CharField(max_length=50, verbose_name="選択肢1", blank=True)
    choice_2 = models.CharField(max_length=50, verbose_name="選択肢2", blank=True)
    choice_3 = models.CharField(max_length=50, verbose_name="選択肢3", blank=True)
    correct_answer = models.IntegerField(
        choices=[(0, 'A'), (1, 'B'), (2, 'C')],
        verbose_name="正解インデックス",
        null=True,
        blank=True
    )
    correct_value = models.IntegerField(
        verbose_name="正解の数値",
        null=True,
        blank=True
    )
    
    # 品質評価情報
    quality_score = models.IntegerField(default=0, verbose_name="品質スコア")
    category = models.CharField(
        max_length=20,
        choices=[
            ('animals', '動物'),
            ('sounds', '音・擬音語'),
            ('opposites', '反対語'),
            ('colors', '色'),
            ('hiragana', 'ひらがな'),
            ('basic', '基本語彙'),
            ('addition', '足し算'),
            ('subtraction', '引き算'),
            ('numbers', '数字'),
            ('counting', '数え方'),
            ('others', 'その他'),
        ],
        default='others',
        verbose_name="カテゴリ"
    )
    
    # 使用統計
    used_count = models.IntegerField(default=0, verbose_name="使用回数")
    correct_rate = models.FloatField(default=0.0, verbose_name="正答率")
    
    # 管理情報
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    
    class Meta:
        verbose_name = "事前生成問題"
        verbose_name_plural = "事前生成問題"
        ordering = ['-quality_score', '-created_at']
    
    def __str__(self):
        return f"{self.question_text[:30]}... (品質:{self.quality_score})"
    
    def get_choices_list(self):
        """選択肢をリストで取得"""
        if self.answer_format == 'multiple_choice':
            return [self.choice_1, self.choice_2, self.choice_3]
        return []
    
    def to_dict(self):
        """辞書形式で問題データを取得"""
        data = {
            'question': self.question_text,
            'question_type': self.question_type,
            'answer_format': self.answer_format,
            'quality_score': self.quality_score,
            'category': self.category
        }
        
        if self.answer_format == 'multiple_choice':
            data.update({
                'choices': self.get_choices_list(),
                'answer': self.correct_answer,
            })
        elif self.answer_format == 'numeric':
            data.update({
                'correct_value': self.correct_value,
            })
        
        return data
