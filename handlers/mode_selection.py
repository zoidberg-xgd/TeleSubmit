"""
模式选择处理模块
"""
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CallbackContext

from config.settings import BOT_MODE, MODE_MEDIA, MODE_DOCUMENT, MODE_MIXED
from models.state import STATE
from database.db_manager import get_db, cleanup_old_data
from utils.blacklist import is_blacklisted

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
    
    # 获取用户名信息
    user = update.effective_user
    username = user.username or f"user{user.id}"
    
    # 检查用户是否在黑名单中
    if is_blacklisted(user_id):
        logger.warning(f"黑名单用户尝试使用机器人，user_id: {user_id}")
        await update.message.reply_text("⚠️ 您已被列入黑名单，无法使用投稿功能。如有疑问，请联系管理员。")
        return ConversationHandler.END
    
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            # 清除旧会话记录
            await c.execute("DELETE FROM submissions WHERE user_id=?", (user_id,))
            
            # 根据配置决定模式
            if BOT_MODE == MODE_MEDIA:
                mode = "media"
                logger.info(f"使用媒体模式，user_id: {user_id}")
                await c.execute("INSERT INTO submissions (user_id, timestamp, mode, image_id, document_id, username) VALUES (?, ?, ?, ?, ?, ?)",
                          (user_id, datetime.now().timestamp(), mode, "[]", "[]", username))
                await conn.commit()
                await show_media_welcome(update)
                return STATE['MEDIA']
                
            elif BOT_MODE == MODE_DOCUMENT:
                mode = "document"
                logger.info(f"使用文档模式，user_id: {user_id}")
                await c.execute("INSERT INTO submissions (user_id, timestamp, mode, image_id, document_id, username) VALUES (?, ?, ?, ?, ?, ?)",
                          (user_id, datetime.now().timestamp(), mode, "[]", "[]", username))
                await conn.commit()
                await show_document_welcome(update)
                return STATE['DOC']
                
            else:  # 混合模式
                # 先创建数据库记录
                logger.info(f"使用混合模式，user_id: {user_id}")
                await c.execute("INSERT INTO submissions (user_id, timestamp, mode, image_id, document_id, username) VALUES (?, ?, ?, ?, ?, ?)",
                          (user_id, datetime.now().timestamp(), "mixed", "[]", "[]", username))
                await conn.commit()
                
                # 显示模式选择键盘
                keyboard = [['📷 媒体投稿', '📄 文档投稿']]
                markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    "📮 欢迎使用投稿机器人！请选择投稿类型：",
                    reply_markup=markup
                )
                return STATE['START_MODE']
    except Exception as e:
        logger.error(f"初始化数据错误: {e}")
        await update.message.reply_text("❌ 初始化失败，请稍后再试")
        return ConversationHandler.END

async def select_mode(update: Update, context: CallbackContext) -> int:
    """
    处理用户模式选择
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            
            if "媒体投稿" in text:
                # 选择媒体投稿模式
                logger.info(f"用户选择媒体模式，user_id: {user_id}")
                await c.execute("UPDATE submissions SET mode=?, image_id=?, document_id=? WHERE user_id=?", 
                                ("media", "[]", "[]", user_id))
                await conn.commit()
                await update.message.reply_text("✅ 已选择媒体投稿模式", reply_markup=ReplyKeyboardRemove())
                await show_media_welcome(update)
                return STATE['MEDIA']
                
            elif "文档投稿" in text:
                # 选择文档投稿模式
                logger.info(f"用户选择文档模式，user_id: {user_id}")
                await c.execute("UPDATE submissions SET mode=?, image_id=?, document_id=? WHERE user_id=?", 
                                ("document", "[]", "[]", user_id))
                await conn.commit()
                await update.message.reply_text("✅ 已选择文档投稿模式", reply_markup=ReplyKeyboardRemove())
                await show_document_welcome(update)
                return STATE['DOC']
                
            else:
                # 无效选择
                keyboard = [['📷 媒体投稿', '📄 文档投稿']]
                markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    "⚠️ 请选择有效的投稿类型：",
                    reply_markup=markup
                )
                return STATE['START_MODE']
    except Exception as e:
        logger.error(f"模式选择错误: {e}")
        await update.message.reply_text("❌ 模式选择失败，请稍后再试", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def show_media_welcome(update):
    """
    显示媒体投稿欢迎信息
    
    Args:
        update: Telegram 更新对象
    """
    await update.message.reply_text(
        "📮 欢迎使用媒体投稿功能！请按照以下步骤提交：\n\n"
        "1️⃣ 发送媒体文件（必选）：\n"
        "   - 支持图片、视频、GIF、音频等，最多上传50个文件。\n"
        "   - 上传完毕后，请发送 /done_media。\n\n"
        "2️⃣ 发送标签（必选）：\n"
        "   - 最多30个标签，用逗号分隔（例如：明日方舟，原神）。\n\n"
        "3️⃣ 发送链接（可选）：\n"
        "   - 如需附加链接，请确保以 http:// 或 https:// 开头；不需要请回复 \"无\" 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "4️⃣ 发送标题（可选）：\n"
        "   - 如不需要标题，请回复 \"无\" 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "5️⃣ 发送简介（可选）：\n"
        "   - 如不需要简介，请回复 \"无\" 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "6️⃣ 是否将所有媒体设为剧透（点击查看）？\n"
        "   - 请回复 \"否\" 或 \"是\"。\n\n"
        "随时发送 /cancel 取消投稿。"
    )

async def show_document_welcome(update):
    """
    显示文档投稿欢迎信息
    
    Args:
        update: Telegram 更新对象
    """
    await update.message.reply_text(
        "📮 欢迎使用文档投稿功能！请按照以下步骤提交：\n\n"
        "1️⃣ 发送文档文件（必选）：\n"
        "   - 支持各种文档格式（PDF、DOC、XLS、TXT等），至少上传1个文件，最多上传10个文件。\n"
        "   - 上传完毕后，请发送 /done_doc。\n\n"
        "2️⃣ 发送媒体文件（可选）：\n"
        "   - 支持图片、视频、GIF、音频等，最多上传10个文件。\n"
        "   - 上传完毕后，请发送 /done_media，或发送 /skip_media 跳过此步骤。\n\n"
        "3️⃣ 发送标签（必选）：\n"
        "   - 最多30个标签，用逗号分隔（例如：教程，资料）。\n\n"
        "4️⃣ 发送链接（可选）：\n"
        "   - 如需附加链接，请确保以 http:// 或 https:// 开头；不需要请回复 \"无\" 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "5️⃣ 发送标题（可选）：\n"
        "   - 如不需要标题，请回复 \"无\" 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "6️⃣ 发送简介（可选）：\n"
        "   - 如不需要简介，请回复 \"无\" 或发送 /skip_optional 跳过后面的所有可选项。\n\n"
        "7️⃣ 是否将内容设为剧透（点击查看）？\n"
        "   - 请回复 \"否\" 或 \"是\"。\n\n"
        "随时发送 /cancel 取消投稿。"
    )