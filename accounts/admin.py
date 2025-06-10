from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # 一覧画面で表示するフィールド
    list_display = ['username', 'email', 'points_total', 'rank', 'is_active', 'date_joined']
    list_filter = ['rank', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email']
    
    # 詳細画面のフィールド配置
    fieldsets = BaseUserAdmin.fieldsets + (
        ('クイズ情報', {
            'fields': ('points_total', 'rank'),
        }),
    )
    
    # 新規作成時のフィールド
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('クイズ情報', {
            'fields': ('points_total', 'rank'),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
