"""
事前生成高品質問題管理サービス
"""
import random
from typing import List, Dict
from django.db import transaction
from .models import PreGeneratedQuestion
from .openai_service import QuizGeneratorService
from .quality_checker import QuestionQualityChecker, batch_evaluate_questions, filter_high_quality_questions


class PreGeneratedQuestionService:
    """事前生成問題の管理サービス"""
    
    def __init__(self):
        self.quality_checker = QuestionQualityChecker()
        self.openai_service = QuizGeneratorService()
        self.min_quality_score = 70  # 最低品質スコア
    
    @transaction.atomic
    def generate_and_store_questions(self, count: int = 50) -> Dict:
        """
        高品質問題を生成してDBに保存
        
        Args:
            count: 生成する問題数
            
        Returns:
            生成結果の統計情報
        """
        print(f"🚀 {count}問の高品質問題生成を開始...")
        
        # 品質の高い問題が必要数集まるまで生成を続ける
        high_quality_questions = []
        total_generated = 0
        max_attempts = count * 3  # 最大試行回数
        
        while len(high_quality_questions) < count and total_generated < max_attempts:
            # バッチで問題生成（一度に10問）
            batch_size = min(10, count - len(high_quality_questions))
            raw_questions = self.openai_service._generate_ai_questions(batch_size)
            total_generated += len(raw_questions)
            
            # 品質評価
            evaluated_questions = batch_evaluate_questions(raw_questions)
            
            # 高品質問題をフィルタリング
            batch_high_quality = filter_high_quality_questions(
                evaluated_questions, 
                self.min_quality_score
            )
            
            high_quality_questions.extend(batch_high_quality)
            
            print(f"📊 進捗: {len(high_quality_questions)}/{count} (生成済み:{total_generated})")
        
        # DBに保存
        saved_count = 0
        for question_data in high_quality_questions[:count]:
            if self._save_question_to_db(question_data):
                saved_count += 1
        
        result = {
            'requested_count': count,
            'total_generated': total_generated,
            'high_quality_found': len(high_quality_questions),
            'saved_to_db': saved_count,
            'success_rate': len(high_quality_questions) / total_generated if total_generated > 0 else 0
        }
        
        print(f"✅ 完了: {saved_count}問をDBに保存")
        return result
    
    def _save_question_to_db(self, question_data: Dict) -> bool:
        """問題をDBに保存"""
        try:
            # 重複チェック
            if PreGeneratedQuestion.objects.filter(
                question_text=question_data['question']
            ).exists():
                return False
            
            # カテゴリ自動判定
            category = self._determine_category(question_data)
            
            PreGeneratedQuestion.objects.create(
                question_text=question_data['question'],
                choice_1=question_data['choices'][0],
                choice_2=question_data['choices'][1],
                choice_3=question_data['choices'][2],
                correct_answer=question_data['answer'],
                quality_score=question_data['quality_score'],
                category=category
            )
            return True
            
        except Exception as e:
            print(f"⚠️ DB保存エラー: {e}")
            return False
    
    def _determine_category(self, question_data: Dict) -> str:
        """問題のカテゴリを自動判定"""
        text = question_data['question'] + ' '.join(question_data['choices'])
        text_lower = text.lower()
        
        # キーワードベースの分類
        if any(word in text_lower for word in ['どうぶつ', 'いぬ', 'ねこ', 'とり', 'うし']):
            return 'animals'
        
        if any(word in text_lower for word in ['わんわん', 'にゃー', 'もー', 'おと']):
            return 'sounds'
        
        if any(word in text_lower for word in ['はんたい', 'おおきい', 'ちいさい', 'あつい', 'つめたい']):
            return 'opposites'
        
        if any(word in text_lower for word in ['いろ', 'あか', 'あお', 'きいろ', 'みどり']):
            return 'colors'
        
        if any(word in text_lower for word in ['きゃ', 'きゅ', 'きょ', 'ひらがな']):
            return 'hiragana'
        
        return 'others'
    
    def get_random_questions(self, count: int = 10, category: str = None) -> List[Dict]:
        """
        ランダムに高品質問題を取得
        
        Args:
            count: 取得する問題数
            category: カテゴリ指定（任意）
            
        Returns:
            問題のリスト
        """
        query = PreGeneratedQuestion.objects.filter(is_active=True)
        
        if category:
            query = query.filter(category=category)
        
        # 品質スコア順で取得し、その中からランダム選択
        high_quality_questions = query.filter(
            quality_score__gte=self.min_quality_score
        ).order_by('-quality_score')[:count * 2]  # 選択肢を多めに取得
        
        if high_quality_questions.count() < count:
            # 足りない場合は全問題から選択
            high_quality_questions = query.order_by('-quality_score')[:count * 2]
        
        # ランダム選択
        selected_questions = random.sample(
            list(high_quality_questions), 
            min(count, high_quality_questions.count())
        )
        
        # 使用回数を更新
        for question in selected_questions:
            question.used_count += 1
            question.save(update_fields=['used_count'])
        
        return [q.to_dict() for q in selected_questions]
    
    def get_mixed_questions(self, count: int = 10, pregenerated_ratio: float = 0.7) -> List[Dict]:
        """
        事前生成問題とAI生成問題を混合して取得
        
        Args:
            count: 総問題数
            pregenerated_ratio: 事前生成問題の割合 (0.0-1.0)
            
        Returns:
            混合問題のリスト
        """
        pregenerated_count = int(count * pregenerated_ratio)
        ai_generated_count = count - pregenerated_count
        
        questions = []
        
        # 事前生成問題を取得
        if pregenerated_count > 0:
            pregenerated_questions = self.get_random_questions(pregenerated_count)
            questions.extend(pregenerated_questions)
        
        # 不足分をAI生成で補完
        if ai_generated_count > 0 or len(questions) < count:
            remaining_count = count - len(questions)
            if remaining_count > 0:
                ai_questions = self.openai_service._generate_ai_questions(remaining_count)
                questions.extend(ai_questions)
        
        # シャッフル
        random.shuffle(questions)
        return questions[:count]
    
    def update_question_stats(self, question_text: str, is_correct: bool):
        """
        問題の統計情報を更新
        
        Args:
            question_text: 問題文
            is_correct: 正解かどうか
        """
        try:
            question = PreGeneratedQuestion.objects.get(
                question_text=question_text,
                is_active=True
            )
            
            # 正答率の更新
            total_attempts = question.used_count
            if total_attempts > 0:
                current_correct_count = question.correct_rate * (total_attempts - 1)
                new_correct_count = current_correct_count + (1 if is_correct else 0)
                question.correct_rate = new_correct_count / total_attempts
                question.save(update_fields=['correct_rate'])
                
        except PreGeneratedQuestion.DoesNotExist:
            pass  # 事前生成問題でない場合は何もしない
    
    def get_db_stats(self) -> Dict:
        """DB内の問題統計を取得"""
        total_questions = PreGeneratedQuestion.objects.filter(is_active=True).count()
        
        stats = {
            'total_questions': total_questions,
            'high_quality_questions': PreGeneratedQuestion.objects.filter(
                is_active=True,
                quality_score__gte=self.min_quality_score
            ).count(),
            'categories': {},
            'average_quality_score': 0,
        }
        
        # カテゴリ別統計
        for category_code, category_name in PreGeneratedQuestion._meta.get_field('category').choices:
            count = PreGeneratedQuestion.objects.filter(
                is_active=True,
                category=category_code
            ).count()
            stats['categories'][category_name] = count
        
        # 平均品質スコア
        if total_questions > 0:
            from django.db.models import Avg
            avg_score = PreGeneratedQuestion.objects.filter(
                is_active=True
            ).aggregate(Avg('quality_score'))['quality_score__avg']
            stats['average_quality_score'] = round(avg_score or 0, 1)
        
        return stats


# コマンドライン用のバッチ生成関数
def batch_generate_questions(count: int = 100):
    """
    バッチで高品質問題を生成
    
    Usage:
        python manage.py shell
        from quiz.pre_generated_service import batch_generate_questions
        batch_generate_questions(100)
    """
    service = PreGeneratedQuestionService()
    result = service.generate_and_store_questions(count)
    
    print("\n🎯 生成結果:")
    print(f"要求数: {result['requested_count']}")
    print(f"総生成数: {result['total_generated']}")
    print(f"高品質問題数: {result['high_quality_found']}")
    print(f"DB保存数: {result['saved_to_db']}")
    print(f"成功率: {result['success_rate']:.1%}")
    
    return result 