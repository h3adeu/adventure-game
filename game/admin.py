from django.contrib import admin
from .models import GameSession, ChatMessage


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """GameSession の管理画面設定"""
    list_display = ['id', 'session_id', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['session_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """ChatMessage の管理画面設定"""
    list_display = ['id', 'session', 'role', 'short_content', 'timestamp']
    list_filter = ['role', 'timestamp']
    search_fields = ['content']
    readonly_fields = ['timestamp']

    def short_content(self, obj):
        """内容を短く表示"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = '内容'