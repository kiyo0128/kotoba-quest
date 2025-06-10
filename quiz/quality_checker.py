"""
クイズ問題の品質自動評価システム
"""
import re
from typing import Dict, List, Tuple


class QuestionQualityChecker:
    """問題の品質を自動評価するクラス"""
    
    def __init__(self):
        # 小学1年生に適した語彙リスト
        self.grade1_vocabulary = {
            'animals': ['いぬ', 'ねこ', 'とり', 'うし', 'ぶた', 'うま', 'ひつじ', 'やぎ'],
            'colors': ['あか', 'あお', 'きいろ', 'みどり', 'しろ', 'くろ', 'ももいろ'],
            'sounds': ['わんわん', 'にゃーにゃー', 'もーもー', 'ざあざあ', 'ぴかぴか'],
            'opposites': ['おおきい', 'ちいさい', 'あつい', 'つめたい', 'うえ', 'した'],
            'basic_words': ['がっこう', 'せんせい', 'おうち', 'おかあさん', 'おとうさん']
        }
        
        # 品質評価基準
        self.quality_criteria = {
            'hiragana_katakana_only': 25,      # ひらがな・カタカナのみ使用
            'appropriate_length': 20,           # 適切な文字数
            'clear_question': 20,              # 明確な問題文
            'valid_choices': 20,               # 妥当な選択肢
            'age_appropriate': 15              # 年齢に適した内容
        }
    
    def evaluate_question(self, question_data: Dict) -> Tuple[int, Dict]:
        """
        問題を評価してスコアと詳細を返す
        
        Args:
            question_data: {"question": "...", "choices": [...], "answer": 0}
            
        Returns:
            (total_score, evaluation_details)
        """
        scores = {}
        
        # 1. ひらがな・カタカナのみチェック
        scores['hiragana_katakana_only'] = self._check_hiragana_katakana_only(question_data)
        
        # 2. 適切な文字数チェック
        scores['appropriate_length'] = self._check_appropriate_length(question_data)
        
        # 3. 明確な問題文チェック
        scores['clear_question'] = self._check_clear_question(question_data)
        
        # 4. 妥当な選択肢チェック
        scores['valid_choices'] = self._check_valid_choices(question_data)
        
        # 5. 年齢に適した内容チェック
        scores['age_appropriate'] = self._check_age_appropriate(question_data)
        
        total_score = sum(scores.values())
        
        evaluation_details = {
            'total_score': total_score,
            'max_score': 100,
            'criteria_scores': scores,
            'is_high_quality': total_score >= 70,  # 70点以上で高品質
            'recommendations': self._get_recommendations(scores)
        }
        
        return total_score, evaluation_details
    
    def _check_hiragana_katakana_only(self, question_data: Dict) -> int:
        """ひらがな・カタカナのみ使用されているかチェック"""
        text_to_check = question_data['question'] + ' '.join(question_data['choices'])
        
        # 漢字や英語が含まれていないかチェック
        if re.search(r'[a-zA-Z一-龯]', text_to_check):
            return 0
        
        # ひらがな・カタカナ・記号のみの場合
        if re.match(r'^[あ-んア-ンー・（）「」？！。、\s]+$', text_to_check):
            return self.quality_criteria['hiragana_katakana_only']
        
        return 10  # 部分的に適合
    
    def _check_appropriate_length(self, question_data: Dict) -> int:
        """適切な文字数かチェック"""
        question_length = len(question_data['question'])
        choice_lengths = [len(choice) for choice in question_data['choices']]
        
        # 問題文の長さチェック（10-40文字が適切）
        if 10 <= question_length <= 40:
            question_score = 10
        else:
            question_score = 5
        
        # 選択肢の長さチェック（各選択肢1-15文字が適切）
        if all(1 <= length <= 15 for length in choice_lengths):
            choice_score = 10
        else:
            choice_score = 5
        
        return question_score + choice_score
    
    def _check_clear_question(self, question_data: Dict) -> int:
        """明確な問題文かチェック"""
        question = question_data['question']
        
        score = 0
        
        # 疑問符があるかチェック
        if '？' in question or 'でしょう' in question or 'なん' in question:
            score += 10
        
        # 問題文に答えが直接含まれていないかチェック
        question_lower = question.lower()
        answer_choice = question_data['choices'][question_data['answer']].lower()
        
        if answer_choice not in question_lower:
            score += 10
        
        return score
    
    def _check_valid_choices(self, question_data: Dict) -> int:
        """妥当な選択肢かチェック"""
        choices = question_data['choices']
        
        score = 0
        
        # 選択肢数チェック（3つであることを確認）
        if len(choices) == 3:
            score += 5
        
        # 選択肢の重複チェック
        if len(set(choices)) == len(choices):
            score += 5
        
        # 選択肢が空でないかチェック
        if all(choice.strip() for choice in choices):
            score += 5
        
        # 選択肢の妥当性（極端に長い/短いものがないか）
        choice_lengths = [len(choice) for choice in choices]
        if min(choice_lengths) >= 1 and max(choice_lengths) <= 15:
            score += 5
        
        return score
    
    def _check_age_appropriate(self, question_data: Dict) -> int:
        """年齢に適した内容かチェック"""
        text = question_data['question'] + ' '.join(question_data['choices'])
        
        score = 0
        
        # 小学1年生向けの語彙が含まれているかチェック
        for category, words in self.grade1_vocabulary.items():
            if any(word in text for word in words):
                score += 3
                break
        
        # 複雑すぎる概念が含まれていないかチェック
        complex_concepts = ['分数', '割り算', '掛け算', '引き算', '足し算', '数学', '理科']
        if not any(concept in text for concept in complex_concepts):
            score += 5
        
        # 適切な敬語・丁寧語が使われているかチェック
        if 'です' in text or 'ます' in text or 'でしょう' in text:
            score += 4
        
        # 楽しい要素が含まれているかチェック
        fun_elements = ['どうぶつ', 'おと', 'いろ', 'あそび', 'うた']
        if any(element in text for element in fun_elements):
            score += 3
        
        return min(score, self.quality_criteria['age_appropriate'])
    
    def _get_recommendations(self, scores: Dict) -> List[str]:
        """改善推奨事項を生成"""
        recommendations = []
        
        if scores['hiragana_katakana_only'] < 20:
            recommendations.append("ひらがな・カタカナのみを使用してください")
        
        if scores['appropriate_length'] < 15:
            recommendations.append("問題文や選択肢の長さを調整してください")
        
        if scores['clear_question'] < 15:
            recommendations.append("より明確で考えさせる問題文にしてください")
        
        if scores['valid_choices'] < 15:
            recommendations.append("選択肢の内容を改善してください")
        
        if scores['age_appropriate'] < 10:
            recommendations.append("小学1年生により適した内容にしてください")
        
        return recommendations


def batch_evaluate_questions(questions: List[Dict]) -> List[Dict]:
    """
    複数の問題を一括評価
    
    Args:
        questions: 問題のリスト
        
    Returns:
        評価結果付きの問題リスト
    """
    checker = QuestionQualityChecker()
    evaluated_questions = []
    
    for question in questions:
        score, details = checker.evaluate_question(question)
        
        question_with_evaluation = {
            **question,
            'quality_score': score,
            'evaluation_details': details
        }
        
        evaluated_questions.append(question_with_evaluation)
    
    return evaluated_questions


def filter_high_quality_questions(questions: List[Dict], min_score: int = 70) -> List[Dict]:
    """
    高品質な問題のみをフィルタリング
    
    Args:
        questions: 評価済み問題リスト
        min_score: 最低品質スコア
        
    Returns:
        高品質問題のみのリスト
    """
    return [q for q in questions if q.get('quality_score', 0) >= min_score]


# 使用例
if __name__ == "__main__":
    # テスト用問題
    test_question = {
        "question": "「わんわん」と なくのは どの どうぶつでしょう？",
        "choices": ["いぬ", "ねこ", "とり"],
        "answer": 0
    }
    
    checker = QuestionQualityChecker()
    score, details = checker.evaluate_question(test_question)
    
    print(f"品質スコア: {score}/100")
    print(f"高品質判定: {'✅' if details['is_high_quality'] else '❌'}")
    print(f"改善推奨: {details['recommendations']}") 