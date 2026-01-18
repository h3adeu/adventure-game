from .models import ChatMessage

# 定義されている特殊コマンドのリスト
SPECIAL_COMMANDS = {
    '/restart': 'ゲームをリセットして最初から始める',
    '/hint': '現在の状況に関するヒントを表示',
    '/status': 'ゲームの進行状況を表示',
    '/help': '使用可能なコマンドの一覧を表示'
}


def is_special_command(message):
    """
    メッセージが特殊コマンドかどうかを判定

    Args:
        message (str): ユーザーの入力メッセージ

    Returns:
        bool: 特殊コマンドなら True、そうでなければ False
    """
    message = message.strip().lower()
    return message in SPECIAL_COMMANDS


def handle_special_command(command, game_session):
    """
    特殊コマンドを処理

    Args:
        command: コマンド文字列（例: '/restart'）
        game_session: GameSession オブジェクト

    Returns:
        str: コマンドの実行結果メッセージ
    """
    command = command.strip().lower()

    if command == '/restart':
        # ゲームセッションのメッセージを全削除
        ChatMessage.objects.filter(session=game_session).delete()
        return """ゲームをリセットしました。

目を覚ますと、あなたは薄暗い研究所の中にいた。
記憶は曖昧だが、ここから脱出しなければならないことだけは確かだ..."""

    elif command == '/hint':
        # 最新の AI 応答を取得して、ヒントを生成
        last_ai_message = ChatMessage.objects.filter(
            session=game_session,
            role='assistant'
        ).order_by('-timestamp').first()

        if last_ai_message:
            return f"【ヒント】前回のゲームマスターの言葉をよく読んでみましょう: 「{last_ai_message.content[:50]}...」"
        else:
            return "【ヒント】まずは周囲を調べてみましょう。"

    elif command == '/status':
        # 行動回数と進行状況を表示
        total_messages = ChatMessage.objects.filter(
            session=game_session,
            role='user'
        ).count()

        return f"""【現在の状況】
- 行動回数: {total_messages}回
- セッション ID: {game_session.session_id}
- ゲーム開始: {game_session.created_at.strftime('%Y-%m-%d %H:%M')}

脱出まであと少しかもしれません!"""

    elif command == '/help':
        # コマンド一覧を表示
        help_text = "【使用可能なコマンド】\n"
        for cmd, desc in SPECIAL_COMMANDS.items():
            help_text += f"{cmd}: {desc}\n"
        return help_text

    else:
        return f"不明なコマンド: {command}\n'/help'でコマンド一覧を確認できます。"


def check_game_over(response_text, game_session):
    """
    ゲームオーバー判定

    Args:
        response_text: Gemini API からの応答
        game_session: GameSession オブジェクト

    Returns:
        tuple: (is_game_over: bool, reason: str)
    """
    # キーワードチェック
    game_over_keywords = ['死んでしまった', 'ゲームオーバー', '力尽きた', '命を落とした']
    if any(keyword in response_text for keyword in game_over_keywords):
        return (True, "ゲームオーバー: プレイヤーが死亡しました。")

    # 行動回数チェック
    total_actions = ChatMessage.objects.filter(
        session=game_session,
        role='user'
    ).count()

    if total_actions >= 30:
        return (True, "ゲームオーバー: 時間切れです。研究所に閉じ込められました...")

    return (False, "")


def check_game_clear(response_text):
    """
    ゲームクリア判定

    Args:
        response_text (str): AI の応答テキスト

    Returns:
        bool: クリアなら True、そうでなければ False
    """
    # クリアを示すキーワード
    clear_keywords = [
        '脱出成功',
        '外の世界',
        'ゲームクリア',
        '研究所を出た',
        '自由になった',
        '無事に脱出',
        '脱出に成功'
    ]

    return any(keyword in response_text for keyword in clear_keywords)
