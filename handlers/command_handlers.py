"""
命令处理器模块
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from database.db_manager import get_db

logger = logging.getLogger(__name__)

async def cancel(update: Update, context: CallbackContext) -> int:
    """
    处理 /cancel 命令，取消当前会话
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 结束会话状态
    """
    logger.info(f"收到 /cancel 命令，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("DELETE FROM submissions WHERE user_id=?", (user_id,))
    except Exception as e:
        logger.error(f"取消时删除数据错误: {e}")
    await update.message.reply_text("❌ 投稿已取消")
    return ConversationHandler.END

async def debug(update: Update, context: CallbackContext):
    """
    调试命令处理函数
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    logger.info(f"调试命令收到，user_id: {update.effective_user.id}")
    await update.message.reply_text("调试信息：收到你的消息！")

async def catch_all(update: Update, context: CallbackContext):
    """
    捕获所有未处理的消息
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    logger.debug(f"收到未知消息: {update}")