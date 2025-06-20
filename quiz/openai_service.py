import openai
import re
from django.conf import settings
from typing import List, Dict

# ひらがな変換ライブラリ
try:
    from pykakasi import kakasi  # type: ignore
    _kks = kakasi()
    _kks.setMode("J", "H")  # 漢字(Kanji)→ひらがな
    _kks.setMode("K", "H")  # カタカナ→ひらがな（全角）
    _converter = _kks.getConverter()
except Exception:  # ランタイムにライブラリが無い場合でも動作
    _converter = None

KANJI_PATTERN = re.compile(r"[一-龯]+")  # Kanji Unicode 範囲

def _to_hiragana(text: str) -> str:
    """文字列をひらがな化（pykakasi が利用可能な場合）"""
    if _converter is not None:
        return _converter.do(text)
    # フォールバック: そのまま返す
    return text


class QuizGeneratorService:
    """
    OpenAI APIを使用してクイズ問題を生成するサービスクラス
    """
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        # 事前生成問題サービスの遅延読み込み（循環インポート回避）
        self._pregenerated_service = None
    
    @property
    def pregenerated_service(self):
        """事前生成問題サービスの遅延読み込み"""
        if self._pregenerated_service is None:
            from .pre_generated_service import PreGeneratedQuestionService
            self._pregenerated_service = PreGeneratedQuestionService()
        return self._pregenerated_service
    
    def generate_questions(self, num_questions: int = 10, question_type: str = 'language', use_pregenerated: bool = True) -> List[Dict]:
        """
        指定された数の問題を生成する（高品質事前生成問題を優先使用）
        
        Args:
            num_questions: 生成する問題数（デフォルト: 10）
            question_type: 問題のタイプ ('language' または 'math')
            use_pregenerated: 事前生成問題を使用するか（デフォルト: True）
            
        Returns:
            問題のリスト [{"question": "...", "choices": [...], "answer": 0}, ...]
        """
        if question_type == 'math':
            return self._generate_math_questions(num_questions)
        elif use_pregenerated:
            # 事前生成問題とAI生成問題を混合使用（70%:30%）
            return self.pregenerated_service.get_mixed_questions(
                count=num_questions,
                pregenerated_ratio=0.7
            )
        else:
            # 従来のAI生成のみ
            return self._generate_ai_questions(num_questions)
    
    def _generate_ai_questions(self, num_questions: int) -> List[Dict]:
        """
        AIで問題を生成する（内部メソッド）
        
        Args:
            num_questions: 生成する問題数
            
        Returns:
            問題のリスト
        """
        try:
            print(f"AI問題生成開始 - モデル: gpt-4o-mini, 問題数: {num_questions}")
            prompt = self._build_prompt(num_questions)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,  # 少し創造性を上げて質の高い問題を生成
                max_tokens=1200,   # トークン数を増加して詳細な説明を可能に
                top_p=0.9        # 応答の多様性を少し上げる
            )
            
            content = response.choices[0].message.content
            questions = self._parse_response(content)
            
            # 重複排除 & ひらがな化
            questions = self._post_process_questions(questions)
            
            # 不足分があれば追加生成
            if len(questions) < num_questions:
                remaining = num_questions - len(questions)
                questions.extend(self._generate_ai_questions(remaining))
            
            return questions[:num_questions]
            
        except Exception as e:
            print(f"問題生成エラー: {e}")
            # フォールバック問題を返す
            return self._get_fallback_questions(num_questions)
    
    def _get_system_prompt(self) -> str:
        """
        システムプロンプトを取得する
        """
        return """あなたは小学1年生向けの国語教材作成の専門家です。

【重要ルール】
1. ひらがな・カタカナ・数字のみ使用（漢字は絶対に使わない）
2. 選択肢は意味のある言葉にする（ひらがなに変換しただけの不自然な単語は避ける）
3. 1年生が実際に知っている語彙のみ使用
4. 正解が明確で、他の選択肢と区別できる問題

【出題分野例】
- 身近な動物の鳴き声・特徴
- 色の名前・混色
- 反対語（対義語）
- 音や状態を表す言葉（擬音語・擬態語）
- 日常のあいさつ・マナー
- 身の回りの物の名前
- 基本的な助詞の使い方

【良い例と悪い例】
○良い例：「わんわん」となくのはどのどうぶつ？ → いぬ・ねこ・とり
○悪い例：「がくしゅう」について → がくしゅう・べんきょう・こうがく（全部同じような意味）

【選択肢作成のコツ】
- 正解1つ、明らかに違う選択肢2つ
- 同じカテゴリから選ぶ（動物なら動物、色なら色）
- 1年生が迷わない程度の難易度

【出力形式】
問題1: [問題文]
A) 選択肢1
B) 選択肢2
C) 選択肢3
正解: A"""
    
    def _build_prompt(self, num_questions: int) -> str:
        """
        ユーザープロンプトを構築する
        """
        return f"""小学1年生向けの国語クイズを{num_questions}問作成してください。

【必須条件】
1. ひらがな・カタカナ・数字のみ使用
2. 1年生が学校や家庭で実際に使う語彙のみ
3. 選択肢は自然な日本語（無理にひらがなにした不自然な単語は禁止）
4. 問題の難易度は1年生レベル

【問題の種類を混ぜて作成】
- 動物の鳴き声・特徴（例：「わんわん」となくのは？）
- 色に関する問題（例：みかんは何色？）
- 反対語（例：「あつい」の反対は？）
- 音の表現（例：雨の音「ざあざあ」）
- あいさつ・マナー（例：食事前に言う言葉は？）
- 身近な物の名前（例：時間を知るための道具は？）

形式：
問題1: [問題文]
A) 選択肢1
B) 選択肢2
C) 選択肢3
正解: A

{num_questions}問すべて作成してください。"""
    
    def _parse_response(self, content: str) -> List[Dict]:
        """
        ChatGPTの応答をパースして問題リストに変換する
        """
        questions = []
        
        # 問題を分割
        question_blocks = re.split(r'問題\d+:', content)[1:]  # 最初の空文字を除く
        
        for i, block in enumerate(question_blocks):
            try:
                question_data = self._parse_single_question(block)
                if question_data:
                    questions.append(question_data)
            except Exception as e:
                print(f"問題{i+1}のパースエラー: {e}")
                continue
        
        return questions
    
    def _parse_single_question(self, block: str) -> Dict:
        """
        単一の問題ブロックをパースする
        """
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        if len(lines) < 5:  # 問題文 + 3選択肢 + 正解
            return None
        
        # 問題文を取得
        question_text = _to_hiragana(lines[0].strip())
        
        # 選択肢を取得
        choices = []
        choice_pattern = r'^[A-C]\)\s*(.+)$'
        
        for line in lines[1:4]:
            match = re.match(choice_pattern, line)
            if match:
                choices.append(_to_hiragana(match.group(1).strip()))
        
        if len(choices) != 3:
            return None
        
        # 正解を取得
        correct_answer = None
        for line in lines:
            if line.startswith('正解:') or line.startswith('答え:'):
                answer_match = re.search(r'[A-C]', line)
                if answer_match:
                    correct_letter = answer_match.group()
                    correct_answer = ord(correct_letter) - ord('A')
                    break
        
        if correct_answer is None or not (0 <= correct_answer <= 2):
            correct_answer = 0  # デフォルトで最初の選択肢
        
        return {
            "question": question_text,
            "choices": choices,
            "answer": correct_answer
        }
    
    def _generate_math_questions(self, num_questions: int) -> List[Dict]:
        """
        小学1年生レベルの算数問題を生成する
        
        Args:
            num_questions: 生成する問題数
            
        Returns:
            問題のリスト
        """
        try:
            print(f"算数問題生成開始 - モデル: gpt-4o-mini, 問題数: {num_questions}")
            prompt = self._build_math_prompt(num_questions)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_math_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 数学は創造性よりも正確性を重視
                max_tokens=800,
                top_p=0.8
            )
            
            content = response.choices[0].message.content
            questions = self._parse_math_response(content)
            
            # 不足分があれば追加生成
            if len(questions) < num_questions:
                remaining = num_questions - len(questions)
                questions.extend(self._generate_math_questions(remaining))
            
            return questions[:num_questions]
            
        except Exception as e:
            print(f"算数問題生成エラー: {e}")
            # フォールバック算数問題を返す
            return self._get_fallback_math_questions(num_questions)
    
    def _get_math_system_prompt(self) -> str:
        """
        算数問題用のシステムプロンプトを取得する
        """
        return """あなたは小学1年生向けの算数教材作成の専門家です。

【重要ルール】
1. 小学1年生レベルの計算のみ（1桁同士の足し算・引き算）
2. 答えは0以上20以下の整数のみ
3. 引き算の場合、答えが負の数にならないようにする
4. 文章問題は簡単な日常的なシーンを使用
5. ひらがな・カタカナ・数字のみ使用（漢字は使わない）

【出題範囲】
- 足し算: 1+1 から 9+9 まで（答えが20以下）
- 引き算: 大きい数から小さい数を引く（答えが0以上）
- 数の概念: 10までの数の大小、数え方
- 文章問題: リンゴ、あめ、ボールなど身近なものを使った簡単な問題

【出力形式】
問題1: [問題文]
答え: [数字]

文章問題の場合も答えは数字のみにしてください。"""
    
    def _build_math_prompt(self, num_questions: int) -> str:
        """
        算数問題用のユーザープロンプトを構築する
        """
        return f"""小学1年生向けの算数問題を{num_questions}問作成してください。

【必須条件】
1. ひらがな・カタカナ・数字のみ使用（漢字禁止）
2. 答えは0以上20以下の整数
3. 1年生が理解できる範囲の計算のみ

【問題の種類を混ぜて作成】
- 足し算（例: 3 + 4 = ?）
- 引き算（例: 8 - 3 = ?）
- 文章問題（例: りんごが 5こ あります。2こ たべました。のこりは なんこでしょう？）
- 数え方（例: ●●●●● は いくつでしょう？）

形式：
問題1: [問題文]
答え: [数字]

問題2: [問題文]  
答え: [数字]

{num_questions}問すべて作成してください。答えは必ず数字だけにしてください。"""
    
    def _parse_math_response(self, content: str) -> List[Dict]:
        """
        算数問題のChatGPT応答をパースして問題リストに変換する
        """
        questions = []
        
        # 問題を分割
        question_blocks = re.split(r'問題\d+:', content)[1:]  # 最初の空文字を除く
        
        for i, block in enumerate(question_blocks):
            try:
                question_data = self._parse_single_math_question(block)
                if question_data:
                    questions.append(question_data)
            except Exception as e:
                print(f"算数問題{i+1}のパースエラー: {e}")
                continue
        
        return questions
    
    def _parse_single_math_question(self, block: str) -> Dict:
        """
        単一の算数問題ブロックをパースする
        """
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        if len(lines) < 2:  # 問題文 + 答え
            return None
        
        # 問題文を取得
        question_text = lines[0].strip()
        
        # 答えを取得
        correct_value = None
        for line in lines:
            if line.startswith('答え:') or line.startswith('こたえ:'):
                answer_match = re.search(r'\d+', line)
                if answer_match:
                    correct_value = int(answer_match.group())
                    break
        
        if correct_value is None or correct_value < 0 or correct_value > 20:
            return None
        
        return {
            "question": question_text,
            "question_type": "math",
            "answer_format": "numeric",
            "correct_value": correct_value
        }
    
    def _get_fallback_math_questions(self, num_questions: int) -> List[Dict]:
        """
        算数問題のAPIエラー時のフォールバック問題
        """
        fallback_questions = [
            {
                "question": "2 + 3 = ?",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 5
            },
            {
                "question": "5 - 2 = ?",
                "question_type": "math", 
                "answer_format": "numeric",
                "correct_value": 3
            },
            {
                "question": "りんごが 4こ あります。2こ たべました。のこりは なんこでしょう？",
                "question_type": "math",
                "answer_format": "numeric", 
                "correct_value": 2
            },
            {
                "question": "1 + 4 = ?",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 5
            },
            {
                "question": "あめが 6こ あります。3こ あげました。のこりは なんこでしょう？",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 3
            },
            {
                "question": "3 + 5 = ?",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 8
            },
            {
                "question": "9 - 4 = ?",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 5
            },
            {
                "question": "ボールが 7こ あります。4こ つかいました。のこりは なんこでしょう？",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 3
            },
            {
                "question": "2 + 6 = ?",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 8
            },
            {
                "question": "10 - 3 = ?",
                "question_type": "math",
                "answer_format": "numeric",
                "correct_value": 7
            }
        ]
        
        # 必要な数だけ問題を返す（繰り返しも可）
        questions = []
        for i in range(num_questions):
            questions.append(fallback_questions[i % len(fallback_questions)])
        
        return questions
    
    def _post_process_questions(self, questions: List[Dict]) -> List[Dict]:
        """重複排除とひらがな化を保証"""
        unique_questions = []
        seen_texts = set()
        for q in questions:
            q["question"] = _to_hiragana(q["question"])
            q["choices"] = [_to_hiragana(c) for c in q["choices"]]
            if q["question"] not in seen_texts:
                unique_questions.append(q)
                seen_texts.add(q["question"])
        return unique_questions
    
    def _get_fallback_questions(self, num_questions: int) -> List[Dict]:
        """
        APIエラー時のフォールバック問題
        """
        fallback_questions = [
            {
                "question": "「わんわん」と なくのは どの どうぶつでしょう？",
                "choices": ["いぬ", "ねこ", "とり"],
                "answer": 0
            },
            {
                "question": "みかんは なにいろでしょう？",
                "choices": ["オレンジいろ", "みどりいろ", "むらさきいろ"],
                "answer": 0
            },
            {
                "question": "「あつい」の はんたいの ことばは なんでしょう？",
                "choices": ["つめたい", "たかい", "おおきい"],
                "answer": 0
            },
            {
                "question": "あめが ふるときの おとは どれでしょう？",
                "choices": ["ざあざあ", "わんわん", "ぽんぽん"],
                "answer": 0
            },
            {
                "question": "あさ そらで ひかっているのは なんでしょう？",
                "choices": ["たいよう", "つき", "ほし"],
                "answer": 0
            },
            {
                "question": "「にゃーにゃー」と なくのは どの どうぶつでしょう？",
                "choices": ["ねこ", "いぬ", "うし"],
                "answer": 0
            },
            {
                "question": "「いただきます」を いうのは いつでしょう？",
                "choices": ["たべる まえ", "たべた あと", "ねる まえ"],
                "answer": 0
            },
            {
                "question": "よるに そらで ひかっているのは なんでしょう？",
                "choices": ["つき", "たいよう", "くも"],
                "answer": 0
            },
            {
                "question": "「おおきい」の はんたいの ことばは なんでしょう？",
                "choices": ["ちいさい", "たかい", "ながい"],
                "answer": 0
            },
            {
                "question": "「もーもー」と なくのは どの どうぶつでしょう？",
                "choices": ["うし", "ひつじ", "いぬ"],
                "answer": 0
            },
            {
                "question": "りんごは なにいろでしょう？",
                "choices": ["あかいろ", "きいろ", "あおいろ"],
                "answer": 0
            },
            {
                "question": "「こんにちは」を いうのは いつでしょう？",
                "choices": ["ひるま", "あさ", "よる"],
                "answer": 0
            },
            {
                "question": "じかんを しるための どうぐは なんでしょう？",
                "choices": ["とけい", "かがみ", "はし"],
                "answer": 0
            },
            {
                "question": "「ぽかぽか」という ことばは なにを あらわしているでしょう？",
                "choices": ["あたたかい ようす", "つめたい ようす", "うるさい ようす"],
                "answer": 0
            },
            {
                "question": "「ごちそうさま」を いうのは いつでしょう？",
                "choices": ["たべた あと", "たべる まえ", "かう まえ"],
                "answer": 0
            },
            {
                "question": "「うえ」の はんたいの ことばは なんでしょう？",
                "choices": ["した", "よこ", "まえ"],
                "answer": 0
            },
            {
                "question": "がっこうで べんきょうを おしえてくれる ひとは だれでしょう？",
                "choices": ["せんせい", "いしゃ", "うんてんしゅ"],
                "answer": 0
            },
            {
                "question": "「ぴかぴか」という ことばは なにを あらわしているでしょう？",
                "choices": ["ひかっている ようす", "くらい ようす", "おもい ようす"],
                "answer": 0
            },
            {
                "question": "バナナは なにいろでしょう？",
                "choices": ["きいろ", "みどりいろ", "あかいろ"],
                "answer": 0
            },
            {
                "question": "「おはよう」を いうのは いつでしょう？",
                "choices": ["あさ", "ひるま", "よる"],
                "answer": 0
            }
        ]
        
        # 必要な数だけ問題を返す（繰り返しも可）
        questions = []
        for i in range(num_questions):
            questions.append(fallback_questions[i % len(fallback_questions)])
        
        return questions 