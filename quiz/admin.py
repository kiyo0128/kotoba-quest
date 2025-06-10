from django.contrib import admin
from .models import QuizSession, Question, Answer, PreGeneratedQuestion


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    readonly_fields = ['created_at']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['answered_at', 'is_correct']


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'started_at', 'finished_at', 'score', 'points_earned', 'is_completed']
    list_filter = ['is_completed', 'started_at']
    search_fields = ['user__username']
    readonly_fields = ['started_at', 'finished_at', 'score', 'points_earned']
    inlines = [QuestionInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['session', 'question_number', 'text_preview', 'correct_idx', 'created_at']
    list_filter = ['created_at', 'session__started_at']
    search_fields = ['text', 'session__user__username']
    readonly_fields = ['created_at']
    inlines = [AnswerInline]
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = '問題文（プレビュー）'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session__user')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'selected_idx', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at']
    search_fields = ['question__text', 'question__session__user__username']
    readonly_fields = ['answered_at', 'is_correct']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('question__session__user')


@admin.register(PreGeneratedQuestion)
class PreGeneratedQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text_short', 'category', 'quality_score', 'used_count', 'correct_rate', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'quality_score']
    search_fields = ['question_text', 'Choice_1', 'choice_2', 'choice_3']
    ordering = ['-quality_score', '-created_at']
    readonly_fields = ['used_count', 'correct_rate', 'created_at']
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = '問題文'
    
    fieldsets = (
        ('問題内容', {
            'fields': ('question_text', ('choice_1', 'choice_2', 'choice_3'), 'correct_answer')
        }),
        ('品質・分類', {
            'fields': ('quality_score', 'category')
        }),
        ('統計情報', {
            'fields': ('used_count', 'correct_rate'),
            'classes': ('collapse',)
        }),
        ('管理', {
            'fields': ('is_active', 'created_at'),
            'classes': ('collapse',)
        }),
    )
