from unittest.mock import patch

from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import ChatMessage, GameSession

# Gemini API の代わりに返す開始メッセージ
START_MESSAGE = "薄暗い部屋で目を覚ました。"


# 本番用の HTTPS へのリダイレクト（11.9 節）は、テストのリクエストでは無効にする
@override_settings(SECURE_SSL_REDIRECT=False)
@patch("game.views.generate_game_response", return_value=START_MESSAGE)
class BotProtectionTests(TestCase):
    """GET するだけのアクセス（ボット）で、セッションの作成や API の呼び出しが起きないこと"""

    def test_GETだけではセッションもゲームも作られずAPIも呼ばれない(self, generate):
        response = self.client.get(reverse("game:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ゲームを始める")
        self.assertContains(response, reverse("game:start_game"))
        self.assertEqual(GameSession.objects.count(), 0)
        self.assertEqual(Session.objects.count(), 0)
        generate.assert_not_called()

    def test_ボタンのPOSTで開始メッセージが1回だけ作られる(self, generate):
        first = self.client.post(reverse("game:start_game"))
        second = self.client.post(reverse("game:start_game"))  # 二度押し

        self.assertEqual(first.status_code, 200)
        self.assertContains(first, START_MESSAGE)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(GameSession.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.filter(role="assistant").count(), 1)
        generate.assert_called_once()

    def test_開始後のGETでは会話が表示されボタンは出ない(self, generate):
        self.client.post(reverse("game:start_game"))
        generate.reset_mock()

        response = self.client.get(reverse("game:home"))

        self.assertContains(response, START_MESSAGE)
        self.assertNotContains(response, "ゲームを始める")
        generate.assert_not_called()

    def test_start_gameはGETを受け付けない(self, generate):
        response = self.client.get(reverse("game:start_game"))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(GameSession.objects.count(), 0)
        generate.assert_not_called()

    def test_CSRFトークンのないPOSTは拒否される(self, generate):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("game:start_game"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(GameSession.objects.count(), 0)
        generate.assert_not_called()
