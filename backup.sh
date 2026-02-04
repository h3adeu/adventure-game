#!/bin/bash

# 変数
BACKUP_DIR="/home/ubuntu/backups"
DB_FILE="/home/ubuntu/adventure-game/db.sqlite3"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_$DATE.sqlite3"
S3_BUCKET="s3://adventure-game-backups"

# ローカルバックアップ
cp "$DB_FILE" "$BACKUP_FILE"

# S3にアップロード
aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/"

# 30日以上前のローカルバックアップを削除
find "$BACKUP_DIR" -name "db_*.sqlite3" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
