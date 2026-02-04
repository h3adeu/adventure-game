#!/bin/bash
set -e  # エラーが発生したら終了

# 環境変数の確認
if [ -z "$PUBLIC_IP" ]; then
    echo "エラー: PUBLIC_IP が設定されていません"
    echo "export PUBLIC_IP=3.112.xxx.xxx を実行してください"
    exit 1
fi

SSH_KEY="$HOME/.ssh/adventure-game-key.pem"
REMOTE_USER="ubuntu"
REMOTE_DIR="/home/ubuntu/adventure-game"

# SSH鍵の存在確認
if [ ! -f "$SSH_KEY" ]; then
    echo "エラー: SSH鍵が見つかりません: $SSH_KEY"
    exit 1
fi

echo "=== デプロイ開始 ==="
echo "サーバー: $REMOTE_USER@$PUBLIC_IP"
echo ""

# 1. プロジェクトファイルをコピー
echo "[1/7] プロジェクトファイルをコピー中..."
if ! rsync -avz \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'db.sqlite3' \
  --exclude 'staticfiles/' \
  --exclude '*.log' \
  -e "ssh -i $SSH_KEY" \
  ./ $REMOTE_USER@$PUBLIC_IP:$REMOTE_DIR/; then
    echo "エラー: ファイル転送に失敗しました"
    exit 1
fi
echo "[√] プロジェクトファイルの転送完了"

# 2. .env.prod をコピー（存在する場合）
if [ -f ".env.prod" ]; then
    echo "[2/7] .env.prod をコピー中..."
    if ! rsync -avz \
      -e "ssh -i $SSH_KEY" \
      .env.prod $REMOTE_USER@$PUBLIC_IP:$REMOTE_DIR/; then
        echo "エラー: .env.prod の転送に失敗しました"
        exit 1
    fi
    echo "[√] .env.prod の転送完了"
else
    echo "[2/7] .env.prod が見つかりません。スキップします。"
fi

# 3. pyproject.toml と uv.lock をコピー
echo "[3/7] 依存関係ファイルをコピー中..."
if ! rsync -avz \
  -e "ssh -i $SSH_KEY" \
  pyproject.toml uv.lock \
  $REMOTE_USER@$PUBLIC_IP:$REMOTE_DIR/; then
    echo "エラー: 依存関係ファイルの転送に失敗しました"
    exit 1
fi
echo "[√] 依存関係ファイルの転送完了"

# 4. Systemdサービスファイルをコピー
if [ -f "adventure-game.service" ]; then
    echo "[4/7] Systemdサービスファイルをコピー中..."
    if ! rsync -avz \
      -e "ssh -i $SSH_KEY" \
      adventure-game.service \
      $REMOTE_USER@$PUBLIC_IP:/tmp/adventure-game.service; then
        echo "エラー: Systemdサービスファイルの転送に失敗しました"
        exit 1
    fi
    ssh -i $SSH_KEY $REMOTE_USER@$PUBLIC_IP \
      "sudo mv /tmp/adventure-game.service /etc/systemd/system/adventure-game.service" || true
    echo "[√] Systemdサービスファイルの転送完了"
else
    echo "[4/7] adventure-game.service が見つかりません。スキップします。"
fi

# 5. Nginx設定ファイルをコピー
if [ -f "adventure-game.nginx" ]; then
    echo "[5/7] Nginx設定ファイルをコピー中..."
    if ! rsync -avz \
      -e "ssh -i $SSH_KEY" \
      adventure-game.nginx \
      $REMOTE_USER@$PUBLIC_IP:/tmp/adventure-game.nginx; then
        echo "エラー: Nginx設定ファイルの転送に失敗しました"
        exit 1
    fi
    ssh -i $SSH_KEY $REMOTE_USER@$PUBLIC_IP \
      "sudo mv /tmp/adventure-game.nginx /etc/nginx/sites-available/adventure-game" || true
    echo "[√] Nginx設定ファイルの転送完了"
else
    echo "[5/7] adventure-game.nginx が見つかりません。スキップします。"
fi

# 6. サーバー側でデプロイスクリプトを実行
echo "[6/7] サーバー側でデプロイを実行中..."
ssh -i $SSH_KEY $REMOTE_USER@$PUBLIC_IP << 'REMOTE_SCRIPT'
set -e
cd /home/ubuntu/adventure-game

# 仮想環境の作成（既に存在する場合はスキップ）
if [ ! -d ".venv" ]; then
    echo "仮想環境を作成中..."
    uv venv --python 3.13
fi

# 仮想環境を有効化
source .venv/bin/activate

# 依存関係のインストール
echo "依存関係をインストール中..."
uv sync

# .env のシンボリックリンク作成（既に存在する場合はスキップ）
if [ ! -e ".env" ]; then
    if [ -f ".env.prod" ]; then
        echo ".env へのシンボリックリンクを作成中..."
        ln -s .env.prod .env
    else
        echo "警告: .env.prod が見つかりません。.env へのシンボリックリンクを作成できません。"
    fi
fi

# データベースのマイグレーション
echo "データベースのマイグレーションを実行中..."
uv run python manage.py migrate

# 静的ファイルの収集
echo "静的ファイルを収集中..."
uv run python manage.py collectstatic --noinput

REMOTE_SCRIPT

# 7. SystemdサービスとNginxの設定
echo "[7/7] サービスを再起動中..."
ssh -i $SSH_KEY $REMOTE_USER@$PUBLIC_IP << 'REMOTE_SCRIPT'
set -e

# ubuntu ユーザーを www-data グループに追加（既に追加されている場合はスキップ）
if ! groups | grep -q www-data; then
    sudo usermod -aG www-data ubuntu
    echo "ubuntu ユーザーを www-data グループに追加しました"
else
    echo "ubuntu ユーザーは既に www-data グループに属しています"
fi

# Systemdサービスの設定
if [ -f "/etc/systemd/system/adventure-game.service" ]; then
    # Systemdをリロード
    sudo systemctl daemon-reload
    
    # サービスを有効化（既に有効化されている場合はエラーになるが、|| true で無視）
    sudo systemctl enable adventure-game || true
    
    # サービスを再起動
    sudo systemctl restart adventure-game
    
    echo "Gunicornサービスを再起動しました"
fi

# Nginx設定の設定
if [ -f "/etc/nginx/sites-available/adventure-game" ]; then
    # シンボリックリンクの作成（既に存在する場合はスキップ）
    if [ ! -e "/etc/nginx/sites-enabled/adventure-game" ]; then
        sudo ln -s /etc/nginx/sites-available/adventure-game /etc/nginx/sites-enabled/ || true
        echo "Nginx設定ファイルを有効化しました"
    fi
    
    # デフォルト設定を削除（既に削除されている場合はエラーになるが、|| true で無視）
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Nginx設定のテスト
    sudo nginx -t
    
    # Nginxを再起動
    sudo systemctl restart nginx
    
    echo "Nginxを再起動しました"
fi

REMOTE_SCRIPT

echo ""
echo "=== デプロイ完了 ==="
echo "ブラウザで http://$PUBLIC_IP にアクセスして確認してください。"