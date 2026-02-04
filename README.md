# 廃墟の研究所からの脱出

Django と Google Gemini API で作るテキストアドベンチャーゲーム。プレイヤーは廃墟となった地下研究所で謎を解きながら脱出を目指します。

## 機能

- **AI ゲームマスター**: Gemini 2.5 Flash が状況描写と選択肢を生成
- **セッション管理**: ブラウザセッションごとにゲームの進行を保存
- **特殊コマンド**: `/restart`（リセット）、`/hint`（ヒント）、`/status`（進行状況）、`/help`（コマンド一覧）
- **リアルタイムチャット**: htmx による部分更新でスムーズな会話体験

## 必要環境

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（パッケージ管理）

## セットアップ

### 1. リポジトリのクローンと依存関係のインストール

```bash
git clone <repository-url>
cd adventure-game
uv sync
```

### 2. 環境変数の設定

プロジェクトルートに `.env` を作成し、以下を設定してください。

```env
# 必須: Google AI Studio で取得した API キー
GEMINI_API_KEY=your_gemini_api_key

# 開発時（任意）
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
```

[Google AI Studio](https://aistudio.google.com/apikey) で API キーを発行できます。

### 3. データベースのマイグレーション

```bash
uv run python manage.py migrate
```

### 4. 開発サーバーの起動

```bash
uv run python manage.py runserver
```

ブラウザで http://127.0.0.1:8000/ にアクセスしてゲームを開始できます。

## プロジェクト構成

```
adventure-game/
├── game/                 # ゲームアプリ
│   ├── models.py        # GameSession, ChatMessage
│   ├── views.py         # ホーム・ゲームアクション
│   ├── prompts.py       # ゲーム用プロンプト
│   ├── utils.py         # 特殊コマンド・ゲーム判定
│   └── templates/       # ゲーム画面テンプレート
├── server/              # Django プロジェクト設定
│   ├── settings.py
│   └── urls.py
├── pyproject.toml       # 依存関係（uv）
├── adventure-game.service  # systemd 用（本番）
└── manage.py
```

## 本番環境

- **WSGI**: Gunicorn（`adventure-game.service` で systemd 管理）
- **設定**: `.env.prod` や環境変数で `DEBUG=False`、`ALLOWED_HOSTS`、`SECRET_KEY` を指定
- **HTTPS**: 本番時は `SECURE_SSL_REDIRECT` 等のセキュリティ設定が有効になります

## 技術スタック

- **バックエンド**: Django 5.2
- **AI**: Google Gemini API (gemini-2.5-flash)
- **フロント**: Tailwind CSS（CDN）、htmx
- **本番**: Gunicorn

## ライセンス

このプロジェクトのライセンスはリポジトリの設定に従います。
