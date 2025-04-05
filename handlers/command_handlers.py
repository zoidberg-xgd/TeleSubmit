"""
命令处理器模块
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from database.db_manager import get_db
from utils.blacklist import (
    is_owner, 
    add_to_blacklist, 
    remove_from_blacklist, 
    get_blacklist, 
    is_blacklisted
)
from config.settings import OWNER_ID, NOTIFY_OWNER

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
    调试命令，测试各种功能
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    user_id = update.effective_user.id
    logger.info(f"收到调试命令，user_id: {user_id}")
    
    # 检查是否为所有者
    if not is_owner(user_id):
        logger.warning(f"非所有者用户 {user_id} 尝试使用调试命令")
        await update.message.reply_text("⚠️ 只有机器人所有者才能使用此命令")
        return
    
    # 获取当前配置信息
    config_info = (
        f"📊 当前配置信息:\n\n"
        f"OWNER_ID: {OWNER_ID} (类型: {type(OWNER_ID)})\n"
        f"NOTIFY_OWNER: {NOTIFY_OWNER}\n"
    )
    
    await update.message.reply_text(config_info)
    
    # 测试通知功能
    try:
        logger.info("测试向所有者发送通知...")
        test_notification = (
            f"🔔 这是一条测试通知\n\n"
            f"如果您看到这条消息，说明通知功能正常工作。\n"
            f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        
        # 确保OWNER_ID被转换为整数
        try:
            owner_id_int = int(OWNER_ID)
            await context.bot.send_message(
                chat_id=owner_id_int,
                text=test_notification
            )
            logger.info(f"测试通知发送成功")
            await update.message.reply_text("✅ 测试通知已发送，请检查您是否收到")
        except ValueError as e:
            error_msg = f"❌ OWNER_ID格式不正确，无法转换为整数: {e}"
            logger.error(error_msg)
            await update.message.reply_text(error_msg)
        except Exception as e:
            error_msg = f"❌ 发送测试通知失败: {str(e)}"
            logger.error(error_msg)
            await update.message.reply_text(error_msg)
    except Exception as e:
        error_msg = f"❌ 测试通知过程中发生错误: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(error_msg)
    
    # 返回调试结果
    await update.message.reply_text("🔍 调试命令执行完毕")

async def catch_all(update: Update, context: CallbackContext):
    """
    捕获所有未处理的消息
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    logger.debug(f"收到未知消息: {update}")

async def blacklist_add(update: Update, context: CallbackContext):
    """
    添加用户到黑名单
    
    命令格式: /blacklist_add <user_id> [reason]
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    user_id = update.effective_user.id
    
    # 检查是否为所有者
    if not is_owner(user_id):
        logger.warning(f"非所有者用户 {user_id} 尝试使用黑名单添加命令")
        await update.message.reply_text("⚠️ 只有机器人所有者才能使用此命令")
        return
    
    # 检查参数
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text("⚠️ 使用方法: /blacklist_add <user_id> [原因]")
        return
    
    try:
        target_user_id = int(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "未指定原因"
        
        # 添加到黑名单
        success = await add_to_blacklist(target_user_id, reason)
        if success:
            await update.message.reply_text(f"✅ 已将用户 {target_user_id} 添加到黑名单\n原因: {reason}")
        else:
            await update.message.reply_text(f"❌ 添加用户 {target_user_id} 到黑名单时出错")
    except ValueError:
        await update.message.reply_text("⚠️ 用户ID必须是数字")
    except Exception as e:
        logger.error(f"处理黑名单添加命令时出错: {e}")
        await update.message.reply_text("❌ 处理命令时发生错误")

async def blacklist_remove(update: Update, context: CallbackContext):
    """
    从黑名单中移除用户
    
    命令格式: /blacklist_remove <user_id>
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    user_id = update.effective_user.id
    
    # 检查是否为所有者
    if not is_owner(user_id):
        logger.warning(f"非所有者用户 {user_id} 尝试使用黑名单移除命令")
        await update.message.reply_text("⚠️ 只有机器人所有者才能使用此命令")
        return
    
    # 检查参数
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text("⚠️ 使用方法: /blacklist_remove <user_id>")
        return
    
    try:
        target_user_id = int(args[0])
        
        # 从黑名单中移除
        success = await remove_from_blacklist(target_user_id)
        if success:
            await update.message.reply_text(f"✅ 已将用户 {target_user_id} 从黑名单中移除")
        else:
            await update.message.reply_text(f"❓ 用户 {target_user_id} 不在黑名单中")
    except ValueError:
        await update.message.reply_text("⚠️ 用户ID必须是数字")
    except Exception as e:
        logger.error(f"处理黑名单移除命令时出错: {e}")
        await update.message.reply_text("❌ 处理命令时发生错误")

async def blacklist_list(update: Update, context: CallbackContext):
    """
    列出所有黑名单用户
    
    命令格式: /blacklist_list
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    user_id = update.effective_user.id
    
    # 检查是否为所有者
    if not is_owner(user_id):
        logger.warning(f"非所有者用户 {user_id} 尝试使用黑名单列表命令")
        await update.message.reply_text("⚠️ 只有机器人所有者才能使用此命令")
        return
    
    try:
        # 获取黑名单
        blacklist = await get_blacklist()
        
        if not blacklist:
            await update.message.reply_text("📋 黑名单为空")
            return
        
        # 格式化黑名单消息
        message = "📋 **黑名单用户列表**:\n\n"
        for i, user in enumerate(blacklist, 1):
            message += f"{i}. ID: `{user['user_id']}`\n"
            message += f"   原因: {user['reason']}\n"
            message += f"   添加时间: {user['added_at']}\n\n"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"处理黑名单列表命令时出错: {e}")
        await update.message.reply_text("❌ 获取黑名单时发生错误")