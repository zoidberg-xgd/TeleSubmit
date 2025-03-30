"""
媒体处理模块
"""
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from models.state import STATE
from database.db_manager import get_db
from utils.helper_functions import validate_state

logger = logging.getLogger(__name__)

@validate_state(STATE['MEDIA'])
async def handle_media(update: Update, context: CallbackContext) -> int:
    """
    处理媒体文件上传
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 当前会话状态
    """
    logger.info(f"处理媒体输入，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    new_media = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        new_media = f"photo:{file_id}"
    elif update.message.video:
        file_id = update.message.video.file_id
        new_media = f"video:{file_id}"
    elif update.message.animation:
        file_id = update.message.animation.file_id
        new_media = f"animation:{file_id}"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        new_media = f"audio:{file_id}"
    elif update.message.document:
        mime = update.message.document.mime_type
        if mime == "image/gif":
            file_id = update.message.document.file_id
            new_media = f"animation:{file_id}"
        elif mime and mime.startswith("audio/"):
            file_id = update.message.document.file_id
            new_media = f"audio:{file_id}"
        else:
            await update.message.reply_text("⚠️ 不支持的文件类型，请发送支持的媒体")
            return STATE['MEDIA']
    else:
        await update.message.reply_text("⚠️ 请发送支持的媒体文件")
        return STATE['MEDIA']

    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("SELECT image_id, mode FROM submissions WHERE user_id=?", (user_id,))
            row = await c.fetchone()
            
            if not row:
                await update.message.reply_text("❌ 会话已过期，请重新发送 /start")
                return ConversationHandler.END
                
            # 初始化媒体列表 - 确保即使数据库中为空值也能正确处理
            media_list = []
            try:
                if row["image_id"]:
                    media_list = json.loads(row["image_id"])
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，创建新的空列表
                media_list = []
                
            # sqlite3.Row 对象不支持 get 方法
            mode = row["mode"] if "mode" in row.keys() else "mixed"
            mode = mode.lower() if mode else "mixed"
            
            # 根据模式设置不同的限制
            media_limit = 50 if mode == "media" else 10
            
            # 限制媒体数量
            if len(media_list) >= media_limit:
                await update.message.reply_text(f"⚠️ 已达到媒体上传上限（{media_limit}个）")
                return STATE['MEDIA']
                
            media_list.append(new_media)
            await c.execute("UPDATE submissions SET image_id=?, timestamp=? WHERE user_id=?",
                      (json.dumps(media_list), datetime.now().timestamp(), user_id))
            
            logger.info(f"当前媒体数量：{len(media_list)}")
            
            # 根据模式提供不同的提示
            if mode == "media":
                await update.message.reply_text(
                    f"✅ 已接收媒体，共计 {len(media_list)} 个。\n继续发送媒体文件，或发送 /done_media 完成上传。"
                )
            else:
                await update.message.reply_text(
                    f"✅ 已接收媒体，共计 {len(media_list)} 个。\n继续发送媒体文件，或发送 /done_media 完成上传，或发送 /skip_media 跳过该步骤。"
                )
                
    except Exception as e:
        logger.error(f"媒体保存错误: {e}")
        await update.message.reply_text("❌ 媒体保存失败，请稍后再试")
        return ConversationHandler.END
        
    return STATE['MEDIA']

@validate_state(STATE['MEDIA'])
async def done_media(update: Update, context: CallbackContext) -> int:
    """
    完成媒体上传，进入下一阶段
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"媒体上传结束，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("SELECT image_id, mode FROM submissions WHERE user_id=?", (user_id,))
            row = await c.fetchone()
            
            if not row:
                await update.message.reply_text("❌ 会话已过期，请重新发送 /start")
                return ConversationHandler.END
            
            # 检查媒体文件是否存在，增强型错误处理
            media_list = []
            try:
                if row["image_id"]:
                    media_list = json.loads(row["image_id"])
            except (json.JSONDecodeError, TypeError):
                media_list = []
                
            # sqlite3.Row 对象不支持 get 方法
            mode = row["mode"] if "mode" in row.keys() else "mixed"
            mode = mode.lower() if mode else "mixed"
            
            # 仅媒体模式下要求至少有一个媒体文件
            if mode == "media" and not media_list:
                await update.message.reply_text("⚠️ 请至少发送一个媒体文件")
                return STATE['MEDIA']
                
        # 媒体验证通过，进入标签阶段
        await update.message.reply_text("✅ 媒体接收完成，请发送标签（必选，最多30个，用逗号分隔，例如：明日方舟，原神）")
        return STATE['TAG']
        
    except Exception as e:
        logger.error(f"检索媒体错误: {e}")
        await update.message.reply_text("❌ 内部错误，请稍后再试")
        return ConversationHandler.END

@validate_state(STATE['MEDIA'])
async def skip_media(update: Update, context: CallbackContext) -> int:
    """
    跳过媒体上传，进入下一阶段
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"用户跳过媒体上传，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    
    # 检查当前模式
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("SELECT mode FROM submissions WHERE user_id=?", (user_id,))
            row = await c.fetchone()
            
            if not row:
                await update.message.reply_text("❌ 会话已过期，请重新发送 /start")
                return ConversationHandler.END
                
            # sqlite3.Row 对象不支持 get 方法
            mode = row["mode"] if "mode" in row.keys() else "mixed"
            mode = mode.lower() if mode else "mixed"
            
            # 媒体模式下不允许跳过媒体上传
            if mode == "media":
                await update.message.reply_text("⚠️ 在媒体投稿模式下，媒体文件是必选项。请上传至少一个媒体文件。")
                return STATE['MEDIA']
                
        # 非媒体模式可以跳过
        await update.message.reply_text("✅ 已跳过媒体上传，请发送标签（必选，最多30个，用逗号分隔，例如：明日方舟，原神）")
        return STATE['TAG']
        
    except Exception as e:
        logger.error(f"检查模式错误: {e}")
        await update.message.reply_text("❌ 内部错误，请稍后再试")
        return ConversationHandler.END

async def prompt_media(update: Update, context: CallbackContext) -> int:
    """
    提示用户发送媒体文件
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 当前会话状态
    """
    # 检查当前模式
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("SELECT mode FROM submissions WHERE user_id=?", (user_id,))
            row = await c.fetchone()
            
            if not row:
                await update.message.reply_text("❌ 会话已过期，请重新发送 /start")
                return ConversationHandler.END
                
            # sqlite3.Row 对象不支持 get 方法
            mode = row["mode"] if "mode" in row.keys() else "mixed"
            mode = mode.lower() if mode else "mixed"
            
            # 根据模式提供不同的提示
            if mode == "media":
                await update.message.reply_text("请发送支持的媒体文件，或发送 /done_media 完成上传")
            else:
                await update.message.reply_text("请发送支持的媒体文件，或发送 /done_media 完成上传，或发送 /skip_media 跳过媒体上传")
                
    except Exception as e:
        logger.error(f"检查模式错误: {e}")
        # 默认提示
        await update.message.reply_text("请发送支持的媒体文件，或发送 /done_media 完成上传")
    
    return STATE['MEDIA']