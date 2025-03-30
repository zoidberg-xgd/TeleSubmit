"""
命令处理器模块
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from models.state import STATE
from database.db_manager import get_db, cleanup_old_data

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> int:
    """
    处理 /start 命令，初始化会话
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"收到 /start 命令，user_id: {update.effective_user.id}")
    await cleanup_old_data()
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            # 清除旧会话记录并插入新记录
            await c.execute("DELETE FROM submissions WHERE user_id=?", (user_id,))
            await c.execute("INSERT INTO submissions (user_id, timestamp) VALUES (?, ?)",
                      (user_id, datetime.now().timestamp()))
    except Exception as e:
        logger.error(f"初始化数据错误: {e}")
    await update.message.reply_text(
        "📮 欢迎使用投稿机器人！请按照以下步骤提交：\n\n"
        "1️⃣ 发送媒体文件（必选）：\n   - 支持图片、视频、GIF、音频等，至少上传一个媒体文件。\n   - 上传完毕后，请发送 /done。\n\n"
        "2️⃣ 发送标签（必选）：\n   - 最多30个标签，用逗号分隔（例如：明日方舟，原神）。\n\n"
        "3️⃣ 发送链接（可选）：\n   - 如需附加链接，请确保以 http:// 或 https:// 开头；不需要请回复 “无” 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "4️⃣ 发送标题（可选）：\n   - 如不需要标题，请回复 “无” 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "5️⃣ 发送简介（可选）：\n   - 如不需要简介，请回复 “无” 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "6️⃣ 是否将所有媒体设为剧透（点击查看）？\n   - 请回复 “否” 或 “是”。\n\n"
        "随时发送 /cancel 取消投稿。"
    )
    return STATE['MEDIA']

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