"""
投稿发布模块
"""
import json
import logging
import asyncio
from telegram import (
    Update,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument
)
from telegram.ext import ConversationHandler, CallbackContext

from config.settings import CHANNEL_ID, NET_TIMEOUT
from database.db_manager import get_db, cleanup_old_data
from utils.helper_functions import build_caption, safe_send

logger = logging.getLogger(__name__)

async def publish_submission(update: Update, context: CallbackContext) -> int:
    """
    发布投稿到频道
    
    处理逻辑:
    1. 仅媒体模式: 将媒体发送到频道
    2. 仅文档模式或文档优先模式: 
       - 若同时有媒体和文档，则以媒体为主贴，文档组合作为回复
       - 若仅有文档，则以文档进行组合发送（说明文本放在最后一条）
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 会话结束状态
    """
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("SELECT * FROM submissions WHERE user_id=?", (user_id,))
            data = await c.fetchone()
        
        if not data:
            await update.message.reply_text("❌ 数据异常，请重新发送 /start")
            return ConversationHandler.END

        caption = build_caption(data)
        
        # 解析媒体和文档数据，增强型错误处理
        media_list = []
        doc_list = []
        
        try:
            if data["image_id"]:
                media_list = json.loads(data["image_id"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"解析媒体数据失败，user_id: {user_id}")
            media_list = []
            
        try:
            if data["document_id"]:
                doc_list = json.loads(data["document_id"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"解析文档数据失败，user_id: {user_id}")
            doc_list = []
        
        if not media_list and not doc_list:
            await update.message.reply_text("❌ 未检测到任何上传文件，请重新发送 /start")
            return ConversationHandler.END

        spoiler_flag = True if data["spoiler"].lower() == "true" else False
        sent_message = None
        
        # 处理媒体文件
        if media_list:
            sent_message = await handle_media_publish(context, media_list, caption, spoiler_flag)
        
        # 处理文档文件
        if doc_list:
            if sent_message:
                # 如果已经发送了媒体，则文档作为回复
                await handle_document_publish(
                    context, 
                    doc_list, 
                    None,  # 不需要重复发送说明，回复到主贴即可
                    sent_message.message_id
                )
            else:
                # 如果只有文档，直接发送
                sent_message = await handle_document_publish(context, doc_list, caption)
        
        # 处理结果
        if not sent_message:
            await update.message.reply_text("❌ 内容发送失败，请稍后再试")
            return ConversationHandler.END
            
        # 生成投稿链接
        if CHANNEL_ID.startswith('@'):
            channel_username = CHANNEL_ID.lstrip('@')
            submission_link = f"https://t.me/{channel_username}/{sent_message.message_id}"
        else:
            submission_link = "频道无公开链接"

        await update.message.reply_text(
            f"🎉 投稿已成功发布到频道！\n点击以下链接查看投稿：\n{submission_link}"
        )
        
    except Exception as e:
        logger.error(f"发布投稿失败: {e}")
        await update.message.reply_text(f"❌ 发布失败，请联系管理员。错误信息：{str(e)}")
    finally:
        # 清理用户会话数据
        try:
            async with get_db() as conn:
                c = await conn.cursor()
                await c.execute("DELETE FROM submissions WHERE user_id=?", (user_id,))
            logger.info(f"已删除用户 {user_id} 的投稿记录")
        except Exception as e:
            logger.error(f"删除数据错误: {e}")
        
        # 清理过期数据
        await cleanup_old_data()
    
    return ConversationHandler.END

async def handle_media_publish(context, media_list, caption, spoiler_flag):
    """
    处理媒体发布
    
    Args:
        context: 回调上下文
        media_list: 媒体列表
        caption: 说明文本
        spoiler_flag: 是否剧透标志
        
    Returns:
        发送的消息对象或None
    """
    # 单个媒体处理
    if len(media_list) == 1:
        typ, file_id = media_list[0].split(":", 1)
        try:
            if typ == "photo":
                return await safe_send(
                    context.bot.send_photo,
                    chat_id=CHANNEL_ID,
                    photo=file_id,
                    caption=caption,
                    parse_mode='HTML',
                    has_spoiler=spoiler_flag
                )
            elif typ == "video":
                return await safe_send(
                    context.bot.send_video,
                    chat_id=CHANNEL_ID,
                    video=file_id,
                    caption=caption,
                    parse_mode='HTML',
                    has_spoiler=spoiler_flag
                )
            elif typ == "animation":
                return await safe_send(
                    context.bot.send_animation,
                    chat_id=CHANNEL_ID,
                    animation=file_id,
                    caption=caption,
                    parse_mode='HTML',
                    has_spoiler=spoiler_flag
                )
            elif typ == "audio":
                return await safe_send(
                    context.bot.send_audio,
                    chat_id=CHANNEL_ID,
                    audio=file_id,
                    caption=caption,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"发送单条媒体失败: {e}")
            return None
    
    # 多个媒体处理 - 针对大量媒体文件的情况（最多50个）
    else:
        try:
            # 尝试组合发送媒体组（Telegram限制每组最多10个）
            all_sent_messages = []
            first_message = None
            
            # 将媒体列表分成每组最多10个项目
            for chunk_index in range(0, len(media_list), 10):
                media_chunk = media_list[chunk_index:chunk_index + 10]
                media_group = []
                
                for i, m in enumerate(media_chunk):
                    typ, file_id = m.split(":", 1)
                    if typ == "photo":
                        media_group.append(InputMediaPhoto(
                            media=file_id,
                            # 只在第一组的第一个媒体添加说明
                            caption=caption if (chunk_index == 0 and i == 0) else None,
                            parse_mode='HTML' if (chunk_index == 0 and i == 0) else None,
                            has_spoiler=spoiler_flag
                        ))
                    elif typ == "video":
                        media_group.append(InputMediaVideo(
                            media=file_id,
                            caption=caption if (chunk_index == 0 and i == 0) else None,
                            parse_mode='HTML' if (chunk_index == 0 and i == 0) else None,
                            has_spoiler=spoiler_flag
                        ))
                    elif typ == "animation":
                        media_group.append(InputMediaAnimation(
                            media=file_id,
                            caption=caption if (chunk_index == 0 and i == 0) else None,
                            parse_mode='HTML' if (chunk_index == 0 and i == 0) else None,
                            has_spoiler=spoiler_flag
                        ))
                    elif typ == "audio":
                        media_group.append(InputMediaAudio(
                            media=file_id,
                            caption=caption if (chunk_index == 0 and i == 0) else None,
                            parse_mode='HTML' if (chunk_index == 0 and i == 0) else None
                        ))
                
                # 发送当前组
                if chunk_index == 0:
                    # 第一组直接发送
                    sent_messages = await safe_send(
                        context.bot.send_media_group,
                        chat_id=CHANNEL_ID,
                        media=media_group
                    )
                    
                    if sent_messages and len(sent_messages) > 0:
                        all_sent_messages.extend(sent_messages)
                        first_message = sent_messages[0]  # 保存第一条消息，用于回复
                else:
                    # 后续组作为回复发送
                    sent_messages = await safe_send(
                        context.bot.send_media_group,
                        chat_id=CHANNEL_ID,
                        media=media_group,
                        reply_to_message_id=first_message.message_id if first_message else None
                    )
                    
                    if sent_messages and len(sent_messages) > 0:
                        all_sent_messages.extend(sent_messages)
            
            # 返回第一条消息
            return first_message if first_message else (all_sent_messages[0] if all_sent_messages else None)
        except Exception as e:
            logger.error(f"发送媒体组失败: {e}")
            return None

async def handle_document_publish(context, doc_list, caption=None, reply_to_message_id=None):
    """
    处理文档发布
    
    Args:
        context: 回调上下文
        doc_list: 文档列表
        caption: 说明文本，如果为None则不添加说明
        reply_to_message_id: 回复的消息ID，如果为None则创建新消息
        
    Returns:
        发送的消息对象或None
    """
    if len(doc_list) == 1 and caption is not None:
        # 单个文档处理
        _, file_id = doc_list[0].split(":", 1)
        try:
            return await safe_send(
                context.bot.send_document,
                chat_id=CHANNEL_ID,
                document=file_id,
                caption=caption,
                parse_mode='HTML',
                reply_to_message_id=reply_to_message_id
            )
        except Exception as e:
            logger.error(f"发送单个文档失败: {e}")
            return None
    else:
        # 多个文档处理，使用文档组
        try:
            doc_media_group = []
            for i, doc_item in enumerate(doc_list):
                _, file_id = doc_item.split(":", 1)
                # 只在最后一个文档添加说明，且caption不为None
                caption_to_use = caption if (i == len(doc_list) - 1 and caption is not None) else None
                doc_media_group.append(InputMediaDocument(
                    media=file_id,
                    caption=caption_to_use,
                    parse_mode='HTML' if caption_to_use else None
                ))
            
            sent_docs = await safe_send(
                context.bot.send_media_group,
                chat_id=CHANNEL_ID,
                media=doc_media_group,
                reply_to_message_id=reply_to_message_id
            )
            
            if sent_docs and len(sent_docs) > 0:
                return sent_docs[0]
            return None
        except Exception as e:
            logger.error(f"发送文档组失败: {e}")
            return None