from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """カスタムユーザーモデル用の登録フォーム"""
    
    class Meta:
        model = User
        fields = ('username',)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # フィールドの日本語化とスタイリング
        self.fields['username'].label = 'ユーザー名'
        self.fields['username'].help_text = '小学生の名前や好きなニックネームを入力してね！'
        self.fields['password1'].label = 'パスワード'
        self.fields['password1'].help_text = '安全なパスワードを作ってね！'
        self.fields['password2'].label = 'パスワード（確認）'
        self.fields['password2'].help_text = '同じパスワードをもう一度入力してね！'
        
        # Bootstrap クラスを追加
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label
            }) 