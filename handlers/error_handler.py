"""
错误处理模块
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: CallbackContext) -> None:
    """
    处理 Telegram bot 运行中的错误
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文，包含错误信息
    """
    logger.error(msg="处理更新时发生异常：", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        if isinstance(context.error, asyncio.TimeoutError):
            await update.message.reply_text("⚠️ 网络请求超时，请稍等片刻再试。如果问题持续，请重新发送 /start")
        else:
            await update.message.reply_text("⚠️ 对话异常，已中断，请稍等片刻再试，或者重新发送 /start")