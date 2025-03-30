"""
会话处理器模块
"""
import json
import logging
from datetime import datetime
from telegram import (
    Update,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
    InputMediaAudio
)
from telegram.ext import ConversationHandler, CallbackContext

from config.settings import CHANNEL_ID
from models.state import STATE
from database.db_manager import get_db
from utils.helper_functions import (
    process_tags, 
    build_caption, 
    validate_state, 
    safe_send
)

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
        elif mime.startswith("audio/"):
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
            await c.execute("SELECT image_id FROM submissions WHERE user_id=?", (user_id,))
            row = await c.fetchone()
            media_list = json.loads(row["image_id"]) if row and row["image_id"] else []
            media_list.append(new_media)
            await c.execute("UPDATE submissions SET image_id=? WHERE user_id=?",
                      (json.dumps(media_list), user_id))
        logger.info(f"当前媒体数量：{len(media_list)}")
        await update.message.reply_text(f"✅ 已接收媒体，共计 {len(media_list)} 个。\n继续发送媒体文件，或发送 /done 完成上传。")
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
            await c.execute("SELECT image_id FROM submissions WHERE user_id=?", (user_id,))
            row = await c.fetchone()
            if not row or not row["image_id"]:
                await update.message.reply_text("⚠️ 请至少发送一个媒体文件")
                return STATE['MEDIA']
    except Exception as e:
        logger.error(f"检索媒体错误: {e}")
        await update.message.reply_text("❌ 内部错误，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 媒体接收完成，请发送标签（必选，最多30个，用逗号分隔，例如：明日方舟，原神）")
    return STATE['TAG']

@validate_state(STATE['TAG'])
async def handle_tag(update: Update, context: CallbackContext) -> int:
    """
    处理标签输入
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"处理标签输入，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    raw_tags = update.message.text.strip()
    success, processed_tags = process_tags(raw_tags)
    if not success or not processed_tags:
        await update.message.reply_text("❌ 标签格式错误，请重新输入（最多30个，用逗号分隔）")
        return STATE['TAG']
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET tags=? WHERE user_id=?",
                      (processed_tags, user_id))
        logger.info(f"标签保存成功，user_id: {user_id}")
    except Exception as e:
        logger.error(f"标签保存错误: {e}")
        await update.message.reply_text("❌ 标签保存失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text(
        "✅ 标签已保存，请发送链接（可选，不需要请回复 “无” 或发送 /skip_optional 跳过后面的所有可选项 。需填写请以 http:// 或 https:// 开头）"
    )
    return STATE['LINK']

@validate_state(STATE['LINK'])
async def handle_link(update: Update, context: CallbackContext) -> int:
    """
    处理链接输入
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"处理链接输入，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    link = update.message.text.strip()
    if link.lower() == "无":
        link = ""
    elif not link.startswith(('http://', 'https://')):
        await update.message.reply_text("⚠️ 链接格式不正确，请以 http:// 或 https:// 开头，或回复“无”跳过")
        return STATE['LINK']
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET link=? WHERE user_id=?",
                      (link, user_id))
        logger.info(f"链接保存成功，user_id: {user_id}")
    except Exception as e:
        logger.error(f"链接保存错误: {e}")
        await update.message.reply_text("❌ 链接保存失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 链接已保存，请发送标题（可选，不需要请回复 “无” 或发送 /skip_optional 跳过后面的所有可选项）")
    return STATE['TITLE']

@validate_state(STATE['TITLE'])
async def handle_title(update: Update, context: CallbackContext) -> int:
    """
    处理标题输入
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"处理标题输入，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    title = update.message.text.strip()
    title_to_store = "" if title.lower() == "无" else title[:100]
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET title=? WHERE user_id=?",
                      (title_to_store, user_id))
        logger.info(f"标题保存成功，user_id: {user_id}")
    except Exception as e:
        logger.error(f"标题保存错误: {e}")
        await update.message.reply_text("❌ 标题保存失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 标题已保存，请发送简介（可选，不需要请回复 “无” 或发送 /skip_optional 跳过后面的所有可选项）")
    return STATE['NOTE']

@validate_state(STATE['NOTE'])
async def handle_note(update: Update, context: CallbackContext) -> int:
    """
    处理简介输入
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"处理简介输入，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    note = update.message.text.strip()
    note_to_store = "" if note.lower() == "无" else note[:600]
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET note=? WHERE user_id=?",
                      (note_to_store, user_id))
        logger.info(f"简介保存成功，user_id: {user_id}")
    except Exception as e:
        logger.error(f"简介保存错误: {e}")
        await update.message.reply_text("❌ 简介保存失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 简介已保存，请问是否将所有媒体设为剧透（点击查看）？回复 “否” 或 “是”")
    return STATE['SPOILER']

@validate_state(STATE['SPOILER'])
async def handle_spoiler(update: Update, context: CallbackContext) -> int:
    """
    处理剧透设置
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态或结束状态
    """
    logger.info(f"处理剧透选择，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    answer = update.message.text.strip()
    # 用户回复"是"则设为剧透，否则为非剧透
    spoiler_flag = True if answer == "是" else False
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET spoiler=? WHERE user_id=?",
                      ("true" if spoiler_flag else "false", user_id))
        logger.info(f"剧透选择保存成功，user_id: {user_id}，spoiler: {spoiler_flag}")
    except Exception as e:
        logger.error(f"剧透保存错误: {e}")
        await update.message.reply_text("❌ 剧透选择保存失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 剧透选择已保存，正在发布投稿……")
    return await publish_submission(update, context)

# 跳过可选项的处理函数
async def skip_optional_link(update: Update, context: CallbackContext) -> int:
    """
    跳过链接及后续可选项
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"跳过链接、标题、简介，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            # 链接、标题、简介均设置为默认空值
            await c.execute("UPDATE submissions SET link=? WHERE user_id=?", ("", user_id))
            await c.execute("UPDATE submissions SET title=? WHERE user_id=?", ("", user_id))
            await c.execute("UPDATE submissions SET note=? WHERE user_id=?", ("", user_id))
    except Exception as e:
        logger.error(f"/skip_optional 执行错误: {e}")
        await update.message.reply_text("❌ 跳过可选项失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 链接、标题、简介已跳过，请问是否将所有媒体设为剧透（点击查看）？回复 “否” 或 “是”")
    return STATE['SPOILER']

async def skip_optional_title(update: Update, context: CallbackContext) -> int:
    """
    跳过标题及后续可选项
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"跳过标题、简介，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET title=? WHERE user_id=?", ("", user_id))
            await c.execute("UPDATE submissions SET note=? WHERE user_id=?", ("", user_id))
    except Exception as e:
        logger.error(f"/skip_optional 执行错误: {e}")
        await update.message.reply_text("❌ 跳过可选项失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 标题、简介已跳过，请问是否将所有媒体设为剧透（点击查看）？回复 “否” 或 “是”")
    return STATE['SPOILER']

async def skip_optional_note(update: Update, context: CallbackContext) -> int:
    """
    跳过简介
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 下一个会话状态
    """
    logger.info(f"跳过简介，user_id: {update.effective_user.id}")
    user_id = update.effective_user.id
    try:
        async with get_db() as conn:
            c = await conn.cursor()
            await c.execute("UPDATE submissions SET note=? WHERE user_id=?", ("", user_id))
    except Exception as e:
        logger.error(f"/skip_optional 执行错误: {e}")
        await update.message.reply_text("❌ 跳过可选项失败，请稍后再试")
        return ConversationHandler.END
    await update.message.reply_text("✅ 简介已跳过，请问是否将所有媒体设为剧透（点击查看）？回复 “否” 或 “是”")
    return STATE['SPOILER']

async def prompt_media(update: Update, context: CallbackContext) -> int:
    """
    提示用户发送媒体文件
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 当前会话状态
    """
    await update.message.reply_text("请发送支持的媒体文件，或发送 /done 完成上传")
    return STATE['MEDIA']

async def publish_submission(update: Update, context: CallbackContext) -> int:
    """
    发布投稿到频道
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
        
    Returns:
        int: 结束会话状态
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
        media_json = data["image_id"]
        media_list = json.loads(media_json) if media_json else []
        if not media_list:
            await update.message.reply_text("❌ 未检测到媒体文件，请重新发送 /start")
            return ConversationHandler.END

        # 根据数据库中 spoiler 字段判断是否添加剧透效果
        spoiler_flag = True if data["spoiler"].lower() == "true" else False

        sent_message = None
        # 单个媒体文件处理
        if len(media_list) == 1:
            typ, file_id = media_list[0].split(":", 1)
            try:
                if typ == "photo":
                    sent_message = await safe_send(
                        context.bot.send_photo,
                        chat_id=CHANNEL_ID,
                        photo=file_id,
                        caption=caption,
                        parse_mode='HTML',
                        has_spoiler=spoiler_flag
                    )
                elif typ == "video":
                    sent_message = await safe_send(
                        context.bot.send_video,
                        chat_id=CHANNEL_ID,
                        video=file_id,
                        caption=caption,
                        parse_mode='HTML',
                        has_spoiler=spoiler_flag
                    )
                elif typ == "animation":
                    sent_message = await safe_send(
                        context.bot.send_animation,
                        chat_id=CHANNEL_ID,
                        animation=file_id,
                        caption=caption,
                        parse_mode='HTML',
                        has_spoiler=spoiler_flag
                    )
                elif typ == "audio":
                    sent_message = await safe_send(
                        context.bot.send_audio,
                        chat_id=CHANNEL_ID,
                        audio=file_id,
                        caption=caption,
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text("❌ 不支持的媒体类型")
                    return ConversationHandler.END
            except Exception as e:
                logger.error(f"发送单条媒体失败: {e}")
                await update.message.reply_text(f"❌ 媒体发送失败: {str(e)}")
                return ConversationHandler.END
        else:
            # 优先尝试组合发送媒体组（仅支持 photo、video、animation）
            allowed_group_types = {"photo", "video", "animation"}
            if all(m.split(":", 1)[0] in allowed_group_types for m in media_list):
                media_group = []
                for i, m in enumerate(media_list):
                    typ, file_id = m.split(":", 1)
                    if typ == "photo":
                        media_group.append(InputMediaPhoto(
                            media=file_id,
                            caption=caption if i == 0 else None,
                            has_spoiler=spoiler_flag
                        ))
                    elif typ == "video":
                        media_group.append(InputMediaVideo(
                            media=file_id,
                            caption=caption if i == 0 else None,
                            has_spoiler=spoiler_flag
                        ))
                    elif typ == "animation":
                        media_group.append(InputMediaAnimation(
                            media=file_id,
                            caption=caption if i == 0 else None,
                            has_spoiler=spoiler_flag
                        ))
                sent_messages = []
                try:
                    # 发送主媒体组（最多10个）
                    main_chunk = media_group[:10]
                    main_messages = await safe_send(
                        context.bot.send_media_group,
                        chat_id=CHANNEL_ID,
                        media=main_chunk
                    )
                    sent_messages.extend(main_messages)
                    parent_message_id = main_messages[0].message_id
                except Exception as e:
                    logger.error(f"发送主媒体组失败: {e}")
                    await update.message.reply_text("❌ 主媒体组发送失败，请稍后再试")
                    return ConversationHandler.END

                if len(media_group) > 10:
                    extra_media = media_group[10:]
                    for i in range(0, len(extra_media), 10):
                        chunk = extra_media[i:i+10]
                        try:
                            extra_messages = await safe_send(
                                context.bot.send_media_group,
                                chat_id=CHANNEL_ID,
                                media=chunk,
                                reply_to_message_id=parent_message_id
                            )
                            sent_messages.extend(extra_messages)
                        except Exception as e:
                            logger.error(f"发送额外媒体组块 {i//10+1} 失败: {e}")
                sent_message = sent_messages[0]
            else:
                # 若部分媒体不支持组合，则分开发送
                for i, m in enumerate(media_list):
                    typ, file_id = m.split(":", 1)
                    try:
                        if typ == "photo":
                            if i == 0:
                                sent_message = await safe_send(
                                    context.bot.send_photo,
                                    chat_id=CHANNEL_ID,
                                    photo=file_id,
                                    caption=caption,
                                    parse_mode='HTML',
                                    has_spoiler=spoiler_flag
                                )
                            else:
                                await safe_send(
                                    context.bot.send_photo,
                                    chat_id=CHANNEL_ID,
                                    photo=file_id,
                                    reply_to_message_id=sent_message.message_id,
                                    has_spoiler=spoiler_flag
                                )
                        elif typ == "video":
                            if i == 0:
                                sent_message = await safe_send(
                                    context.bot.send_video,
                                    chat_id=CHANNEL_ID,
                                    video=file_id,
                                    caption=caption,
                                    parse_mode='HTML',
                                    has_spoiler=spoiler_flag
                                )
                            else:
                                await safe_send(
                                    context.bot.send_video,
                                    chat_id=CHANNEL_ID,
                                    video=file_id,
                                    reply_to_message_id=sent_message.message_id,
                                    has_spoiler=spoiler_flag
                                )
                        elif typ == "animation":
                            if i == 0:
                                sent_message = await safe_send(
                                    context.bot.send_animation,
                                    chat_id=CHANNEL_ID,
                                    animation=file_id,
                                    caption=caption,
                                    parse_mode='HTML',
                                    has_spoiler=spoiler_flag
                                )
                            else:
                                await safe_send(
                                    context.bot.send_animation,
                                    chat_id=CHANNEL_ID,
                                    animation=file_id,
                                    reply_to_message_id=sent_message.message_id,
                                    has_spoiler=spoiler_flag
                                )
                        elif typ == "audio":
                            if i == 0:
                                sent_message = await safe_send(
                                    context.bot.send_audio,
                                    chat_id=CHANNEL_ID,
                                    audio=file_id,
                                    caption=caption,
                                    parse_mode='HTML'
                                )
                            else:
                                await safe_send(
                                    context.bot.send_audio,
                                    chat_id=CHANNEL_ID,
                                    audio=file_id,
                                    reply_to_message_id=sent_message.message_id
                                )
                    except Exception as e:
                        logger.error(f"发送媒体 {i+1}（类型: {typ}）失败: {e}")
                if not sent_message:
                    await update.message.reply_text("❌ 所有媒体发送均失败，请稍后再试")
                    return ConversationHandler.END

        logger.info(f"投稿发布成功，user_id: {user_id}")
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
        try:
            async with get_db() as conn:
                c = await conn.cursor()
                await c.execute("DELETE FROM submissions WHERE user_id=?", (user_id,))
            logger.info(f"已删除用户 {user_id} 的投稿记录")
        except Exception as e:
            logger.error(f"删除数据错误: {e}")
    
    from database.db_manager import cleanup_old_data
    await cleanup_old_data()
    return ConversationHandler.END