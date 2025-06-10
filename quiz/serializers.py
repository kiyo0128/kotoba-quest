from rest_framework import serializers
from .models import QuizSession, Question, Answer
from accounts.models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """
    ユーザープロフィール情報のシリアライザー
    """
    next_rank_info = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['username', 'points_total', 'rank', 'next_rank_info', 'date_joined']
        read_only_fields = ['username', 'date_joined']
    
    def get_next_rank_info(self, obj):
        return obj.get_next_rank_info()


class QuestionSerializer(serializers.ModelSerializer):
    """
    問題のシリアライザー
    """
    class Meta:
        model = Question
        fields = ['id', 'text', 'choices', 'question_number']
        read_only_fields = ['id']


class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    """
    回答情報を含む問題のシリアライザー（結果表示用）
    """
    user_answer = serializers.SerializerMethodField()
    correct_answer = serializers.SerializerMethodField()
    is_correct = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'choices', 'question_number', 'correct_idx', 
                 'user_answer', 'correct_answer', 'is_correct']
    
    def get_user_answer(self, obj):
        try:
            answer = obj.answers.first()
            return answer.selected_idx if answer else None
        except:
            return None
    
    def get_correct_answer(self, obj):
        return obj.get_correct_answer()
    
    def get_is_correct(self, obj):
        try:
            answer = obj.answers.first()
            return answer.is_correct if answer else False
        except:
            return False


class AnswerSerializer(serializers.ModelSerializer):
    """
    回答のシリアライザー
    """
    class Meta:
        model = Answer
        fields = ['question', 'selected_idx', 'is_correct', 'answered_at']
        read_only_fields = ['is_correct', 'answered_at']


class QuizSessionSerializer(serializers.ModelSerializer):
    """
    クイズセッションのシリアライザー
    """
    questions = QuestionSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = QuizSession
        fields = ['id', 'user', 'started_at', 'finished_at', 'score', 
                 'points_earned', 'is_completed', 'questions']
        read_only_fields = ['id', 'user', 'started_at', 'finished_at', 
                          'score', 'points_earned', 'is_completed']


class QuizResultSerializer(serializers.ModelSerializer):
    """
    クイズ結果表示用のシリアライザー
    """
    questions = QuestionWithAnswerSerializer(many=True, read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    accuracy = serializers.SerializerMethodField()
    user_rank_info = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizSession
        fields = ['id', 'user', 'started_at', 'finished_at', 'score', 
                 'points_earned', 'is_completed', 'accuracy', 'questions',
                 'user_rank_info']
    
    def get_accuracy(self, obj):
        total_questions = obj.questions.count()
        if total_questions == 0:
            return 0
        return round((obj.score / total_questions) * 100, 1)
    
    def get_user_rank_info(self, obj):
        return {
            'current_rank': obj.user.rank,
            'total_points': obj.user.points_total,
            'next_rank_info': obj.user.get_next_rank_info()
        }


class SubmitAnswerSerializer(serializers.Serializer):
    """
    回答送信用のシリアライザー
    """
    question_id = serializers.IntegerField()
    selected_idx = serializers.IntegerField(min_value=0, max_value=4)
    
    def validate_question_id(self, value):
        try:
            question = Question.objects.get(id=value)
            # セッションが完了していないかチェック
            if question.session.is_completed:
                raise serializers.ValidationError("このクイズセッションは既に完了しています。")
            return value
        except Question.DoesNotExist:
            raise serializers.ValidationError("指定された問題が見つかりません。")


class StartQuizSerializer(serializers.Serializer):
    """
    クイズ開始用のシリアライザー
    """
    # 特別な入力は不要。ユーザー情報は認証から取得
    pass 