"""
工具函数模块
"""
import re
import json
import asyncio
import logging
from functools import lru_cache, wraps
from datetime import datetime
from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from config.settings import ALLOWED_TAGS, NET_TIMEOUT
from database.db_manager import get_db

logger = logging.getLogger(__name__)

# 标签分割正则表达式
TAG_SPLIT_PATTERN = re.compile(r'[,\s，]+')

@lru_cache(maxsize=128)
def process_tags(raw_tags: str) -> tuple:
    """
    处理标签字符串
    
    Args:
        raw_tags: 原始标签字符串
        
    Returns:
        tuple: (成功标志, 处理后的标签字符串)
    """
    try:
        # 使用预编译的正则表达式分割标签
        tags = [t.strip().lower() for t in TAG_SPLIT_PATTERN.split(raw_tags) if t.strip()]
        tags = tags[:ALLOWED_TAGS]
        
        # 确保每个标签前加上#，如果标签已经有#，则不重复添加
        processed = [f"#{tag}" if not tag.startswith("#") else tag for tag in tags]
        
        # 处理标签长度超过30的情况
        processed = [tag[:30] if len(tag) > 0 else tag for tag in processed]
        
        # 使用空格拼接标签，得到正确的格式
        return True, ' '.join(processed)
    except Exception as e:
        logger.error(f"标签处理错误: {e}")
        return False, ""

def escape_markdown(text: str) -> str:
    """
    转义 HTML 中的特殊字符
    
    Args:
        text: 需要转义的文本
        
    Returns:
        str: 转义后的文本
    """
    escape_chars = r'\_*[]()~>#+-=|{}.!'
    return ''.join(f"\\{c}" if c in escape_chars else c for c in text)

def build_caption(data) -> str:
    """
    构建媒体说明文本
    
    Args:
        data: 包含投稿信息的数据对象
        
    Returns:
        str: 格式化的说明文本
    """
    MAX_CAPTION_LENGTH = 1024  # Telegram 的最大 caption 长度

    def get_link_part(link: str) -> str:
        return f"🔗 链接： {link}" if link else ""
    
    def get_title_part(title: str) -> str:
        return f"🔖 标题： \n【{title}】" if title else ""
    
    def get_note_part(note: str) -> str:
        # "简介"部分要求第一行为标签，后面跟内容
        return f"📝 简介：\n{note}" if note else ""
    
    def get_tags_part(tags: str) -> str:
        return f"🏷 Tags: {tags}" if tags else ""
    
    def get_spoiler_part(spoiler: str) -> str:
        return "⚠️点击查看⚠️" if spoiler.lower() == "true" else ""

    # 收集各部分，只有内容不为空时才添加，避免产生多余的换行
    parts = []
    link = get_link_part(data["link"])
    if link:
        parts.append(link)
    title = get_title_part(data["title"])
    if title:
        parts.append(title)
    note = get_note_part(data["note"])
    if note:
        parts.append(note)
    tags = get_tags_part(data["tags"])
    if tags:
        parts.append(tags)
    
    # 将各部分按换行符连接，避免空值带来多余换行
    caption_body = "\n".join(parts)
    spoiler = get_spoiler_part(data["spoiler"])
    
    # 如果存在正文内容且有剧透提示，则剧透提示单独占一行
    if caption_body:
        full_caption = f"{spoiler}\n{caption_body}" if spoiler else caption_body
    else:
        full_caption = spoiler

    # 如果整体长度在允许范围内，则直接返回
    if len(full_caption) <= MAX_CAPTION_LENGTH:
        return full_caption

    # 超长情况：尝试截断 note 部分（其他部分保持不变）
    fixed_parts = []
    if link:
        fixed_parts.append(link)
    if title:
        fixed_parts.append(title)
    if tags:
        fixed_parts.append(tags)
    fixed_text = "\n".join(fixed_parts)
    
    # 预留剧透提示和固定部分所占长度以及连接换行符
    prefix = f"{spoiler}\n" if spoiler and fixed_text else spoiler
    # 如果 note 存在，则需要额外一个换行符连接
    connector = "\n" if fixed_text and note else ""
    available_length = MAX_CAPTION_LENGTH - len(prefix) - len(fixed_text) - len(connector)
    truncated_note = (data["note"][:available_length] + "...") if (available_length > 0 and data["note"]) else ""
    truncated_note_part = get_note_part(truncated_note)
    
    # 重新组装各部分
    parts = []
    if link:
        parts.append(link)
    if title:
        parts.append(title)
    if truncated_note_part:
        parts.append(truncated_note_part)
    if tags:
        parts.append(tags)
    caption_body = "\n".join(parts)
    full_caption = f"{spoiler}\n{caption_body}" if spoiler and caption_body else spoiler or caption_body

    return full_caption[:MAX_CAPTION_LENGTH]

def validate_state(expected_state: int):
    """
    验证会话状态装饰器
    
    Args:
        expected_state: 期望的状态值
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: CallbackContext):
            user_id = update.effective_user.id
            try:
                async with get_db() as conn:
                    c = await conn.cursor()
                    await c.execute("SELECT timestamp FROM submissions WHERE user_id=?", (user_id,))
                    result = await c.fetchone()
                    if not result:
                        await update.message.reply_text("❌ 会话已过期，请重新发送 /start")
                        return ConversationHandler.END
            except Exception as e:
                logger.error(f"状态验证错误: {e}")
                await update.message.reply_text("❌ 内部错误，请稍后再试")
                return ConversationHandler.END
            return await func(update, context)
        return wrapper
    return decorator

async def safe_send(send_func, *args, **kwargs):
    """
    安全发送函数，包含重试逻辑
    
    Args:
        send_func: 发送函数
        args: 位置参数
        kwargs: 关键字参数
        
    Returns:
        发送结果或None（如果失败）
    """
    max_retries = 2  # 最多重试次数
    current_attempt = 0
    last_error = None
    
    while current_attempt <= max_retries:
        try:
            return await asyncio.wait_for(send_func(*args, **kwargs), timeout=NET_TIMEOUT)
        except asyncio.TimeoutError:
            current_attempt += 1
            last_error = f"网络请求超时 (尝试 {current_attempt}/{max_retries + 1})"
            # 只有在最后一次尝试失败时才记录
            if current_attempt > max_retries:
                logger.warning(last_error)
            else:
                # 非最后一次尝试，只打印调试信息
                logger.debug(f"发送超时，正在重试 ({current_attempt}/{max_retries + 1})...")
                await asyncio.sleep(2)  # 等待2秒后重试
        except Exception as e:
            # 其他错误直接抛出
            last_error = str(e)
            logger.error(f"发送失败: {e}")
            raise e
    
    # 所有重试都失败，但我们不想中断流程，所以返回 None
    return None