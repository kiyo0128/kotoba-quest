from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from .models import QuizSession, Question, Answer
from .openai_service import QuizGeneratorService
import json


class QuizStartView(LoginRequiredMixin, TemplateView):
    """クイズ開始画面"""
    template_name = 'quiz/start.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 未完了のセッションがあるかチェック
        ongoing_session = QuizSession.objects.filter(
            user=user, is_completed=False
        ).first()
        
        context['ongoing_session'] = ongoing_session
        return context


class QuizGameView(LoginRequiredMixin, TemplateView):
    """クイズゲーム画面"""
    template_name = 'quiz/game.html'

    def dispatch(self, request, *args, **kwargs):
        """リクエスト処理前の事前チェック"""
        session_id = kwargs.get('session_id')
        session = get_object_or_404(QuizSession, id=session_id, user=request.user)
        
        # 現在の問題番号を取得
        answered_count = session.questions.filter(answers__isnull=False).count()
        current_question_number = answered_count + 1
        
        if current_question_number > 10:
            # 全問題完了済み - 結果画面にリダイレクト
            return redirect('quiz:result', session_id=session.id)
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = kwargs.get('session_id')
        
        session = get_object_or_404(QuizSession, id=session_id, user=self.request.user)
        
        # 現在の問題番号を取得
        answered_count = session.questions.filter(answers__isnull=False).count()
        current_question_number = answered_count + 1
        
        # 現在の問題を取得
        current_question = session.questions.filter(
            question_number=current_question_number
        ).first()
        
        if not current_question:
            # 問題が見つからない場合はエラー
            raise Http404("問題が見つかりません")
        
        context.update({
            'session': session,
            'current_question': current_question,
            'current_question_number': current_question_number,
            'total_questions': 10,
            'answered_count': answered_count,
            'progress_percentage': (answered_count / 10) * 100,
        })
        
        return context


class QuizResultView(LoginRequiredMixin, TemplateView):
    """クイズ結果画面"""
    template_name = 'quiz/result.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = kwargs.get('session_id')
        
        session = get_object_or_404(QuizSession, id=session_id, user=self.request.user)
        
        # セッションが未完了の場合は完了処理を実行
        if not session.is_completed:
            session.finish_session()
        
        # 結果の詳細を取得
        questions_with_answers = []
        for question in session.questions.all().order_by('question_number'):
            answer = question.answers.first()
            questions_with_answers.append({
                'question': question,
                'answer': answer,
                'is_correct': answer.is_correct if answer else False,
                'user_choice': question.choices[answer.selected_idx] if answer else None,
                'correct_choice': question.choices[question.correct_idx],
            })
        
        # ランクアップチェック
        old_rank = session.user.rank
        session.user.update_rank()
        rank_up = old_rank != session.user.rank
        
        context.update({
            'session': session,
            'questions_with_answers': questions_with_answers,
            'rank_up': rank_up,
            'old_rank': old_rank,
            'new_rank': session.user.rank,
        })
        
        return context


class QuizHistoryView(LoginRequiredMixin, TemplateView):
    """学習履歴画面"""
    template_name = 'quiz/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 完了したセッションを取得（最新順）
        sessions = QuizSession.objects.filter(
            user=user,
            is_completed=True
        ).order_by('-finished_at')
        
        # ページネーション用に最初の20件を取得
        recent_sessions = sessions[:20]
        
        # 統計情報
        total_sessions = sessions.count()
        if total_sessions > 0:
            total_score = sum(session.score for session in sessions)
            average_score = total_score / total_sessions
            best_score = max(session.score for session in sessions)
            total_points = sum(session.points_earned for session in sessions)
        else:
            average_score = 0
            best_score = 0
            total_points = 0
        
        # 今月の統計
        from datetime import datetime, timezone as dt_timezone
        now = datetime.now(dt_timezone.utc)
        current_month_sessions = sessions.filter(
            finished_at__year=now.year,
            finished_at__month=now.month
        )
        
        context.update({
            'sessions': recent_sessions,
            'total_sessions': total_sessions,
            'average_score': round(average_score, 1),
            'best_score': best_score,
            'total_points': total_points,
            'current_month_sessions': current_month_sessions.count(),
        })
        
        return context


# API Views
@login_required
def start_quiz_api(request):
    """クイズセッション開始API"""
    if request.method == 'POST':
        try:
            print(f"クイズ開始API呼び出し - ユーザー: {request.user.username}")
            
            # 未完了のセッションがあるかチェック
            ongoing_session = QuizSession.objects.filter(
                user=request.user, is_completed=False
            ).first()
            
            if ongoing_session:
                print(f"未完了セッション発見: {ongoing_session.id}")
                return JsonResponse({
                    'status': 'ongoing',
                    'session_id': ongoing_session.id,
                    'message': '未完了のクイズがあります。続きから始めますか？'
                })
            
            print("新しいセッション作成中...")
            # 新しいセッションを作成
            session = QuizSession.objects.create(user=request.user)
            print(f"セッション作成完了: {session.id}")
            
            # 問題を生成
            print("問題生成サービス初期化中...")
            quiz_generator = QuizGeneratorService()
            print("問題生成開始...")
            questions_data = quiz_generator.generate_questions(10)
            print(f"問題生成完了: {len(questions_data)}問")
            
            # 問題をデータベースに保存
            print("問題をデータベースに保存中...")
            for i, q_data in enumerate(questions_data, 1):
                Question.objects.create(
                    session=session,
                    text=q_data['question'],
                    choices=q_data['choices'],
                    correct_idx=q_data['answer'],
                    question_number=i
                )
            print("問題保存完了")
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.id,
                'message': 'クイズセッションを開始しました！'
            })
            
        except Exception as e:
            print(f"クイズ開始エラー: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': f'クイズの開始に失敗しました: {str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)


@login_required
def submit_answer_api(request):
    """回答送信API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            question_number = data.get('question_number')
            selected_idx = data.get('selected_idx')
            
            # バリデーション
            if not all([session_id, question_number is not None, selected_idx is not None]):
                return JsonResponse({
                    'status': 'error',
                    'message': '必要なパラメータが不足しています'
                }, status=400)
            
            # セッションと問題を取得
            session = get_object_or_404(QuizSession, id=session_id, user=request.user)
            question = get_object_or_404(Question, session=session, question_number=question_number)
            
            # 既に回答済みかチェック
            if hasattr(question, 'answers') and question.answers.exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'この問題は既に回答済みです'
                }, status=400)
            
            # 回答を保存
            answer = Answer.objects.create(
                question=question,
                selected_idx=selected_idx
            )
            
            # 次の問題があるかチェック
            next_question_number = question_number + 1
            has_next = next_question_number <= 10
            
            response_data = {
                'status': 'success',
                'is_correct': answer.is_correct,
                'correct_answer': question.correct_idx,
                'correct_choice': question.choices[question.correct_idx],
                'has_next': has_next,
                'next_question_number': next_question_number if has_next else None
            }
            
            # 次の問題またはクイズ結果のURLを追加
            if has_next:
                response_data['next_url'] = reverse('quiz:game', kwargs={'session_id': session.id})
            else:
                session.finish_session()
                response_data['final_score'] = session.score
                response_data['points_earned'] = session.points_earned
                response_data['redirect_url'] = reverse('quiz:result', kwargs={'session_id': session.id})
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '無効なJSONデータです'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'回答の処理に失敗しました: {str(e)}'
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)


@login_required
def quiz_history_api(request):
    """クイズ履歴取得API"""
    sessions = QuizSession.objects.filter(
        user=request.user, 
        is_completed=True
    ).order_by('-started_at')[:20]
    
    history_data = []
    for session in sessions:
        history_data.append({
            'id': session.id,
            'started_at': session.started_at.strftime('%Y-%m-%d %H:%M'),
            'score': session.score,
            'points_earned': session.points_earned,
        })
    
    return JsonResponse({
        'status': 'success',
        'history': history_data
    })


# 既存の関数を削除
def home(request):
    """ホーム画面 - 削除予定"""
    return redirect('home')


def start_quiz(request):
    """旧クイズ開始 - 削除予定"""
    return start_quiz_api(request)


def get_user_profile(request):
    """旧プロフィール - 削除予定"""
    return JsonResponse({'message': 'プロフィール機能は準備中です'})
