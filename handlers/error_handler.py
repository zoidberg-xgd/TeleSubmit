"""
错误处理模块
"""
import logging
import asyncio
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext
from telegram.error import (
    TelegramError, 
    Forbidden, 
    NetworkError, 
    BadRequest,
    TimedOut,
    ChatMigrated,
    RetryAfter,
    InvalidToken
)

logger = logging.getLogger(__name__)

# 最大重试次数
MAX_RETRY_ATTEMPTS = 3

async def error_handler(update: object, context: CallbackContext) -> None:
    """
    处理 Telegram bot 运行中的错误
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文，包含错误信息
    """
    # 获取异常和追踪信息
    error = context.error
    trace = "".join(traceback.format_tb(error.__traceback__))
    
    # 记录详细错误日志
    error_msg = f"处理更新时发生异常 - 类型:{type(error).__name__}, 消息:{str(error)}"
    logger.error(error_msg)
    logger.debug(f"异常追踪:\n{trace}")
    
    # 尝试获取用户信息（如果有）
    user_info = ""
    if isinstance(update, Update) and update.effective_user:
        user_id = update.effective_user.id
        username = update.effective_user.username or "无用户名"
        user_info = f"用户ID: {user_id}, 用户名: @{username}"
        logger.error(f"错误涉及用户: {user_info}")
    
    # 处理不同类型的错误
    if isinstance(error, asyncio.TimeoutError):
        await handle_timeout_error(update, context)
    elif isinstance(error, BadRequest):
        await handle_bad_request(update, context, error)
    elif isinstance(error, Forbidden):
        await handle_forbidden_error(update, context, error)
    elif isinstance(error, NetworkError) or isinstance(error, TimedOut):
        await handle_network_error(update, context, error)
    elif isinstance(error, RetryAfter):
        await handle_retry_after(update, context, error)
    else:
        await handle_general_error(update, context, error)

async def handle_timeout_error(update, context):
    """处理超时错误"""
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ 网络请求超时，请稍等片刻再试。如果问题持续，请发送 /start 重新开始。"
            )
        except Exception as e:
            logger.error(f"回复超时错误消息失败: {e}")

async def handle_bad_request(update, context, error):
    """处理错误请求"""
    if isinstance(update, Update) and update.effective_message:
        try:
            # 检查常见的 BadRequest 错误
            error_text = str(error).lower()
            
            if "message is not modified" in error_text:
                # 消息未修改，忽略即可
                logger.info("忽略'消息未修改'错误")
                return
            elif "message to edit not found" in error_text:
                logger.info("忽略'未找到要编辑的消息'错误")
                return
            elif "query is too old" in error_text:
                await update.effective_message.reply_text(
                    "此操作已过期，请重新开始。"
                )
            elif "have no rights" in error_text or "not enough rights" in error_text:
                await update.effective_message.reply_text(
                    "机器人权限不足，无法执行此操作。请联系管理员。"
                )
            else:
                await update.effective_message.reply_text(
                    "⚠️ 请求格式错误，请检查输入并重试。"
                )
        except Exception as e:
            logger.error(f"回复 BadRequest 错误消息失败: {e}")

async def handle_forbidden_error(update, context, error):
    """处理禁止访问错误"""
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ 机器人无权执行此操作。可能是权限不足或被用户阻止。"
            )
        except Exception as e:
            logger.error(f"回复 Forbidden 错误消息失败: {e}")

async def handle_network_error(update, context, error):
    """处理网络错误"""
    # 记录网络错误但不一定向用户显示
    logger.warning(f"发生网络错误: {error}")
    
    # 分析网络错误类型
    error_msg = str(error).lower()
    
    # 检查网络错误的具体类型
    if isinstance(error, TimedOut):
        retry_msg = "操作超时，请稍后再试。"
    elif "connection" in error_msg and "reset" in error_msg:
        retry_msg = "网络连接被重置，请稍后重试。"
    elif "proxy" in error_msg:
        retry_msg = "代理连接问题，请检查网络设置。"
    elif "ssl" in error_msg:
        retry_msg = "安全连接问题，请稍后再试。"
    else:
        retry_msg = "网络连接出现问题，请稍后再试。"
    
    # 尝试重新连接或简单通知用户
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(f"⚠️ {retry_msg}")
        except Exception as e:
            logger.error(f"回复网络错误消息失败: {e}")
            # 最后尝试通过其他方式发送
            try:
                if update.effective_chat:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"⚠️ 网络问题，请稍后再试。"
                    )
            except:
                pass

async def handle_retry_after(update, context, error):
    """处理需要重试的错误"""
    retry_seconds = error.retry_after
    logger.warning(f"接收到限流通知，需等待 {retry_seconds} 秒后重试")
    
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ 机器人被限流，请在 {retry_seconds} 秒后重试。"
            )
        except Exception as e:
            logger.error(f"回复限流错误消息失败: {e}")

async def handle_general_error(update, context, error):
    """处理一般性错误"""
    if isinstance(update, Update) and update.effective_message:
        try:
            # 创建错误报告按钮
            keyboard = [
                [InlineKeyboardButton("重试", callback_data="retry_last_action")],
                [InlineKeyboardButton("重新开始", callback_data="restart")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.effective_message.reply_text(
                "⚠️ 对话处理过程中发生错误，请稍后再试或重新开始。\n"
                "如果问题持续出现，请联系管理员。",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"回复一般错误消息失败: {e}")
            # 最后的尝试 - 非常简单的消息
            try:
                await update.effective_message.reply_text("⚠️ 出现错误，请重新开始对话。")
            except:
                pass