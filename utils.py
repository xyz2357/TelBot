import functools
import logging
from typing import Callable, Awaitable

def safe_call(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # 自动回复错误信息（支持 update/message/query）
            logging.error(f"异常: {e}", exc_info=True)
            # 尝试获取 update/message/query
            update = kwargs.get('update') or (args[1] if len(args) > 1 else None)
            context = kwargs.get('context') or (args[2] if len(args) > 2 else None)
            error_text = f"❌ 系统错误: {str(e)}"
            # 回复到消息或回调
            try:
                if hasattr(update, "message") and update.message:
                    await update.message.reply_text(error_text)
                elif hasattr(update, "callback_query") and update.callback_query:
                    await update.callback_query.edit_message_text(error_text)
            except Exception:
                pass
    return wrapper