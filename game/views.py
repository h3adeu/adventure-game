from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from .models import GameSession, ChatMessage
from .prompts import get_game_prompt, GAME_START_PROMPT
from google import genai
import time
from google.genai.errors import APIError
from functools import wraps
from .utils import is_special_command, handle_special_command, check_game_over, check_game_clear


# Gemini API の設定（モジュールレベルで 1 回だけ）
client = genai.Client(api_key=settings.GEMINI_API_KEY)


# 最後のリクエスト時刻を記録
last_request_time = 0
min_interval = 4  # 秒（15 RPM = 4 秒間隔）


def rate_limit(func):
    """レート制限デコレーター"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global last_request_time
        current_time = time.time()
        elapsed = current_time - last_request_time
        
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            time.sleep(wait_time)
        
        result = func(*args, **kwargs)
        last_request_time = time.time()
        return result
    
    return wrapper


def _call_gemini_api_with_retry(prompt, max_retries=3):
    """
    Gemini API を呼び出し（リトライ付き）
    
    Args:
        prompt (str): プロンプト
        max_retries (int): 最大リトライ回数（502, 503 などの一時的なエラー用）
    
    Returns:
        str: API の応答テキスト
        
    Note:
        4XX 系（400-499）及び 500 エラーは即座にエラーメッセージを返します
        それ以外の APIError（502, 503 など）は指数バックオフでリトライします。
    """
    for attempt in range(max_retries):
        try:
            # Gemini API を呼び出し
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text
        
        except APIError as e:
            # HTTP ステータスコードを取得
            status_code = getattr(e, 'status_code', None)
            
            # 4XX 系エラー（400-499）のエラーメッセージ
            if status_code and 400 <= status_code < 500:
                return f"Error:️ API エラー（{status_code}）: {str(e)}"
        
            # 500 エラーのエラーメッセージ
            if status_code == 500:
                return "Error:️ サーバーエラーが発生しました。しばらく待ってから再度お試しください。"

            # それ以外の APIError（502, 503 など）はリトライ対象
            if attempt < max_retries - 1:
                # 指数バックオフで待機
                wait_time = (2 ** attempt)  # 1 秒、2秒、4秒...
                time.sleep(wait_time)
                continue

    # 最大リトライ回数に達した場合はエラーメッセージを返す
    return "Error:️ エラーが発生しました。少し待ってから再度お試しください。"


@rate_limit
def generate_game_response(user_action, session, max_retries=3):
    """
    Gemini API を使ってゲームの応答を生成（エラーハンドリング付き）
    
    Args:
        user_action (str): プレイヤーの行動
        session (GameSession): ゲームセッション
        max_retries (int): 最大リトライ回数（502, 503 などの一時的なエラー用）
    
    Returns:
        str: AI の応答
    
    Note:
        @rate_limit デコレーターで既にレート制限（4秒間隔）しているため、
        429 エラーは通常発生しません。
        4XX 系（400-499）及び 500 エラーは即座にエラーメッセージを返します。
        それ以外の APIError（502, 503 など）は指数バックオフでリトライします。
    """
    # 会話履歴を取得
    messages = session.messages.all()
    conversation_history = [
        {'role': msg.role, 'content': msg.content}
        for msg in messages
    ]
    
    # プロンプトを生成
    if not conversation_history:
        prompt = GAME_START_PROMPT
    else:
        prompt = get_game_prompt(user_action, conversation_history)
    
    # Gemini API を呼び出し（リトライ付き）
    return _call_gemini_api_with_retry(prompt, max_retries)


def home(request):
    """ゲームのホーム画面"""
    # セッション ID を取得または作成
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    # ゲームセッションを取得または作成
    game_session, created = GameSession.objects.get_or_create(
        session_id=session_id
    )
    
    # 会話履歴を取得
    messages = game_session.messages.all()
    
    # 初回アクセスの場合、開始メッセージを生成
    if created or not messages.exists():
        ai_response = generate_game_response("", game_session)
        
        # 開始メッセージを保存
        ChatMessage.objects.create(
            session=game_session,
            role='assistant',
            content=ai_response
        )
        
        # 再度取得
        messages = game_session.messages.all()
    
    return render(request, 'game/game.html', {
        'session': game_session,
        'messages': messages
    })


def game_action(request):
    """プレイヤーのアクション処理（htmx 用）"""
    # POST でない場合は空のメッセージリストを返す
    if request.method != 'POST':
        return render(request, 'partials/chat_messages.html', {'messages': []})
    
    message = request.POST.get('message', '').strip()
    
    # 空メッセージの場合はそのまま履歴を返す
    if not message:
        session_id = request.session.session_key
        if not session_id:
            return render(request, 'partials/chat_messages.html', {'messages': []})
        
        try:
            game_session = GameSession.objects.get(session_id=session_id)
            messages = game_session.messages.all().order_by('timestamp')
            return render(request, 'partials/chat_messages.html', {'messages': messages})
        except GameSession.DoesNotExist:
            return render(request, 'partials/chat_messages.html', {'messages': []})

    # セッションを取得または作成
    session_id = request.session.session_key
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    game_session, _ = GameSession.objects.get_or_create(session_id=session_id)
    
    # ユーザーのメッセージを保存
    ChatMessage.objects.create(
        session=game_session,
        role='user',
        content=message
    )

    # 特殊コマンドの処理
    if is_special_command(message):
        command_response = handle_special_command(message, game_session)
        ChatMessage.objects.create(
            session=game_session,
            role='system',
            content=command_response
        )

    else:
        # AI の応答を生成
        ai_response = generate_game_response(message, game_session)
    
        # AI の応答を保存
        ChatMessage.objects.create(
            session=game_session,
            role='assistant',
            content=ai_response
        )

        # ゲームオーバー判定
        is_over, reason = check_game_over(ai_response, game_session)
        if is_over:
            game_session.is_active = False
            game_session.save()
            ChatMessage.objects.create(
                session=game_session,
                role='system',
                content=f"GAMEOVER: {reason}\n\n'/restart'で最初からやり直せます。"
            )

        # ゲームクリア判定
        if check_game_clear(ai_response):
            game_session.is_active = False
            game_session.save()
            ChatMessage.objects.create(
                session=game_session,
                role='system',
                content="おめでとうございます! ゲームクリアです!"
            )

    # 更新された履歴を返す（htmx がこれを受け取って画面更新）
    messages = game_session.messages.all().order_by('timestamp')
    return render(request, 'partials/chat_messages.html', {'messages': messages})