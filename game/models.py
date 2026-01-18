from django.db import models

class GameSession(models.Model):
    """ゲームセッション"""
    session_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="セッション ID"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="進行中"
    )

    class Meta:
        verbose_name = "ゲームセッション"
        verbose_name_plural = "ゲームセッション"
        ordering = ['-created_at']  # 新しい順

    def __str__(self):
        return f"Session {self.session_id[:8]}..."


class ChatMessage(models.Model):
    """チャットメッセージ"""
    ROLE_CHOICES = [
        ('user', 'ユーザー'),
        ('assistant', 'アシスタント'),
        ('system', 'システム'),
    ]

    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="セッション"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="役割"
    )
    content = models.TextField(
        verbose_name="内容"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="タイムスタンプ"
    )

    class Meta:
        verbose_name = "チャットメッセージ"
        verbose_name_plural = "チャットメッセージ"
        ordering = ['timestamp']  # 古い順

    def __str__(self):
        return f"{self.role}: {self.content[:30]}..."