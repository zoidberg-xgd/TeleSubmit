"""
Telegram 投稿机器人主程序
支持媒体和文档投稿
"""
import asyncio
import logging
import platform
import os
import signal
import sys
from datetime import datetime, time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
    ApplicationHandlerStop,
    CallbackQueryHandler
)
from dotenv import load_dotenv

# 配置相关导入
from config.settings import TOKEN, TIMEOUT, BOT_MODE, MODE_MEDIA, MODE_DOCUMENT, MODE_MIXED
from models.state import STATE

# 数据库相关导入
from database.db_manager import init_db, cleanup_old_data, get_db
from utils.database import (
    get_user_state, 
    delete_user_state, 
    is_blacklisted, 
    initialize_database
)

# 工具函数导入
from utils.logging_config import setup_logging, cleanup_old_logs
from utils.helper_functions import CONFIG

# 处理程序导入 - 按功能分组
# 基础命令
from handlers.start import start
from handlers.help import help_command
from handlers.cancel import cancel
from handlers.settings import settings, settings_callback

# 黑名单管理
from handlers.blacklist import manage_blacklist, init_blacklist, blacklist_filter
from handlers.command_handlers import blacklist_add, blacklist_remove, blacklist_list, catch_all, debug

# 投稿处理
from handlers.publish import publish_submission
from handlers.text_handlers import handle_text, collect_extra
from handlers.image_handlers import handle_image, done_image
from handlers.document_handlers import handle_document, done_document

# 不同投稿模式支持
from handlers.mode_selection import select_mode
from handlers.document_handlers import handle_doc, done_doc, prompt_doc
from handlers.media_handlers import handle_media, done_media, skip_media, prompt_media
from handlers.submit_handlers import (
    handle_tag, 
    handle_link, 
    handle_title, 
    handle_note, 
    handle_spoiler,
    skip_optional_link,
    skip_optional_title,
    skip_optional_note
)

# 错误处理
from handlers.error_handler import error_handler

# 设置日志
logger = logging.getLogger(__name__)
setup_logging()

# 加载环境变量
load_dotenv()

# 全局变量
TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT", "900"))  # 默认15分钟

# 黑名单过滤函数包装器
def check_blacklist(handler_func):
    """黑名单过滤函数包装器"""
    async def wrapper(update, context):
        # 先进行黑名单检查
        if not blacklist_filter(update):
            # 如果在黑名单中，直接返回
            return
        # 不在黑名单中，调用原始处理函数
        return await handler_func(update, context)
    return wrapper

# 会话超时检查函数
async def check_conversation_timeout(update: Update, context: CallbackContext) -> None:
    """
    检查会话是否超时的处理函数
    
    Args:
        update: Telegram 更新对象
        context: 回调上下文
    """
    if not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    # 跳过检查命令消息
    if update.message and update.message.text and update.message.text.startswith('/'):
        logger.debug(f"跳过对命令消息的超时检查: {update.message.text}")
        return
    
    # 检查用户是否在黑名单中
    if is_blacklisted(user_id):
        logger.warning(f"黑名单用户 {user_id} 尝试发送消息")
        await update.message.reply_text("❌ 您已被列入黑名单，无法使用此机器人。")
        return ApplicationHandlerStop()
    
    # 尝试获取用户会话状态
    try:
        user_state = get_user_state(user_id)
        
        # 如果用户没有会话，允许正常流程继续
        if not user_state:
            logger.debug(f"用户 {user_id} 没有活跃会话，不检查超时")
            return
        
        # 检查超时
        import time
        current_time = time.time()
        last_activity = user_state.get("last_activity", 0)
        time_diff = current_time - last_activity
        
        if time_diff > TIMEOUT_SECONDS:
            logger.info(f"用户 {user_id} 会话超时 ({time_diff:.2f}秒 > {TIMEOUT_SECONDS}秒)")
            
            # 删除用户会话数据
            delete_user_state(user_id)
            
            # 向用户发送超时通知
            try:
                await update.message.reply_text(
                    "⏱️ 您的会话已超时。请发送 /start 重新开始。"
                )
            except Exception as e:
                logger.error(f"发送超时通知失败: {e}")
            
            return ApplicationHandlerStop()
        
        logger.debug(f"用户 {user_id} 会话活跃 ({time_diff:.2f}秒 < {TIMEOUT_SECONDS}秒)")
    except Exception as e:
        logger.error(f"检查会话超时时发生错误: {e}")
        # 出错时不阻止消息处理继续，而是让正常流程继续
    
    return

async def setup_application():
    """
    初始化和配置应用程序
    """
    # 初始化数据库
    await init_db()
    
    # 初始化黑名单
    await init_blacklist()

    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 会话处理器
    states = {}
    
    # 所有模式都需要的通用状态处理
    states[STATE['TAG']] = [MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(handle_tag))]
    states[STATE['LINK']] = [
        CommandHandler('skip_optional', skip_optional_link),
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(handle_link))
    ]
    states[STATE['TITLE']] = [
        CommandHandler('skip_optional', skip_optional_title),
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(handle_title))
    ]
    states[STATE['NOTE']] = [
        CommandHandler('skip_optional', skip_optional_note),
        MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(handle_note))
    ]
    states[STATE['SPOILER']] = [MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(handle_spoiler))]
    
    # 根据工作模式添加特定的状态处理
    if BOT_MODE == MODE_MEDIA:
        # 仅媒体模式
        logger.info("初始化媒体模式处理器")
        states[STATE['MEDIA']] = [
            MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.AUDIO |
                        filters.Document.Category("animation") | filters.Document.AUDIO, 
                        check_blacklist(handle_media)),
            CommandHandler('done_media', done_media),
            MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(prompt_media))
        ]
    elif BOT_MODE == MODE_DOCUMENT:
        # 仅文档模式
        logger.info("初始化文档模式处理器")
        states[STATE['DOC']] = [
            MessageHandler(filters.Document.ALL, check_blacklist(handle_doc)),
            CommandHandler('done_doc', done_doc),
            MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(prompt_doc))
        ]
        
        # 在仅文档模式下也需要添加媒体状态处理器
        states[STATE['MEDIA']] = [
            MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.AUDIO |
                        filters.Document.Category("animation") | filters.Document.AUDIO, 
                        check_blacklist(handle_media)),
            CommandHandler('done_media', done_media),
            CommandHandler('skip_media', skip_media),
            MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(prompt_media))
        ]
    else:
        # 模式选择
        logger.info("初始化混合模式处理器")
        states[STATE['START_MODE']] = [MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(select_mode))]
        
        # 文档处理
        states[STATE['DOC']] = [
            MessageHandler(filters.Document.ALL, check_blacklist(handle_doc)),
            CommandHandler('done_doc', done_doc),
            MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(prompt_doc))
        ]
        
        # 媒体处理
        states[STATE['MEDIA']] = [
            MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.AUDIO |
                        filters.Document.Category("animation") | filters.Document.AUDIO, 
                        check_blacklist(handle_media)),
            CommandHandler('done_media', done_media),
            CommandHandler('skip_media', skip_media),
            MessageHandler(filters.TEXT & ~filters.COMMAND, check_blacklist(prompt_media))
        ]
    
    # 创建会话处理器
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states=states,
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=TIMEOUT,
        name="main_conversation",
        persistent=False
    )
    
    # 添加处理器
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('debug', debug))
    
    # 添加黑名单管理命令
    application.add_handler(CommandHandler('blacklist_add', blacklist_add))
    application.add_handler(CommandHandler('blacklist_remove', blacklist_remove))
    application.add_handler(CommandHandler('blacklist_list', blacklist_list))
    
    # 添加超时检查处理器(放在最优先组)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_conversation_timeout), group=0)
    
    # 添加会话处理器
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("submit", start)],
        states={
            STATE['TEXT']: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            STATE['IMAGE']: [
                MessageHandler(filters.PHOTO | filters.CAPTION, handle_image),
                CommandHandler("done_img", done_image)
            ],
            STATE['DOC']: [
                MessageHandler(filters.Document.ALL, handle_document),
                CommandHandler("done_doc", done_document)
            ],
            STATE['EXTRA']: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_extra)],
            STATE['PUBLISH']: [
                CallbackQueryHandler(publish_submission, pattern="^publish$"),
                CallbackQueryHandler(cancel, pattern="^cancel$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="submission_conversation",
        persistent=False,
    )
    
    application.add_handler(conv_handler, group=2)
    
    # 添加回调查询处理器
    application.add_handler(CallbackQueryHandler(settings_callback), group=3)
    
    # 添加未处理消息的捕获处理器 (最低优先级组)
    application.add_handler(MessageHandler(filters.ALL, catch_all), group=999)
    application.add_error_handler(error_handler)
    
    # 添加周期性清理任务
    job_queue = application.job_queue
    job_queue.run_repeating(
        lambda context: asyncio.create_task(cleanup_old_data()), 
        interval=300, 
        first=10
    )
    
    # 添加周期性清理日志任务
    def clean_logs_job(context):
        """定期清理日志文件"""
        logger.info("执行定期日志清理任务")
        cleanup_old_logs("logs")
        
    # 每天凌晨3点执行一次日志清理
    job_queue.run_daily(clean_logs_job, time=datetime.time(hour=3, minute=0))
    
    return application

async def main():
    """
    主函数 - 设置并启动机器人
    """
    logger.info(f"启动TeleSubmit机器人。版本: {CONFIG.get('VERSION', '0.1.0')}")
    logger.info(f"会话超时时间: {TIMEOUT_SECONDS}秒")
    
    # 初始化数据库
    await init_db()
    # 初始化用户会话数据库
    initialize_database()
    # 初始化黑名单
    await init_blacklist()
    
    # 创建应用程序
    token = TOKEN
    if not token:
        logger.error("未设置TELEGRAM_BOT_TOKEN环境变量")
        sys.exit(1)
    
    try:
        application = Application.builder().token(token).build()
        
        # 注册错误处理
        application.add_error_handler(error_handler)
        
        # 注册命令处理器
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("settings", settings))
        application.add_handler(CommandHandler("blacklist", manage_blacklist), group=1)
        
        # 注册会话超时检查处理器 (最高优先级组)
        application.add_handler(MessageHandler(filters.ALL, check_conversation_timeout), group=0)
        
        # 添加会话处理器
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("submit", start)],
            states={
                STATE['TEXT']: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
                STATE['IMAGE']: [
                    MessageHandler(filters.PHOTO | filters.CAPTION, handle_image),
                    CommandHandler("done_img", done_image)
                ],
                STATE['DOC']: [
                    MessageHandler(filters.Document.ALL, handle_document),
                    CommandHandler("done_doc", done_document)
                ],
                STATE['EXTRA']: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_extra)],
                STATE['PUBLISH']: [
                    CallbackQueryHandler(publish_submission, pattern="^publish$"),
                    CallbackQueryHandler(cancel, pattern="^cancel$")
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel)],
            name="submission_conversation",
            persistent=False,
        )
        
        application.add_handler(conv_handler, group=2)
        
        # 添加回调查询处理器
        application.add_handler(CallbackQueryHandler(settings_callback), group=3)
        
        # 添加黑名单管理命令
        application.add_handler(CommandHandler('blacklist_add', blacklist_add))
        application.add_handler(CommandHandler('blacklist_remove', blacklist_remove))
        application.add_handler(CommandHandler('blacklist_list', blacklist_list))
        
        # 添加未处理消息的捕获处理器 (最低优先级组)
        application.add_handler(MessageHandler(filters.ALL, catch_all), group=999)
        
        # 添加周期性清理任务
        job_queue = application.job_queue
        job_queue.run_repeating(
            lambda context: asyncio.create_task(cleanup_old_data()), 
            interval=300, 
            first=10
        )
        
        # 添加周期性清理日志任务
        def clean_logs_job(context):
            """定期清理日志文件"""
            logger.info("执行定期日志清理任务")
            cleanup_old_logs("logs")
            
        # 每天凌晨3点执行一次日志清理
        job_queue.run_daily(clean_logs_job, time=datetime.time(hour=3, minute=0))
        
        # 注册信号处理器 (仅在非Windows平台上)
        if platform.system() != "Windows":
            register_signal_handlers(application)
        
        # 启动机器人
        logger.info("机器人已启动，按Ctrl+C退出")
        try:
            await application.run_polling(allowed_updates=Application.ALL_TYPES)
        except asyncio.CancelledError:
            logger.info("轮询已取消")
    except Exception as e:
        logger.critical(f"启动机器人时发生严重错误: {e}", exc_info=True)
        sys.exit(1)
        
    logger.info("机器人已停止")

def register_signal_handlers(app):
    """注册信号处理函数"""
    for sig in [signal.SIGINT, signal.SIGTERM]:
        asyncio.get_event_loop().add_signal_handler(
            sig, lambda: asyncio.create_task(graceful_shutdown(app))
        )
    logger.info("已注册信号处理器")

async def graceful_shutdown(app):
    """优雅关闭应用程序"""
    logger.info("接收到关闭信号，正在优雅关闭...")
    await app.stop()
    logger.info("应用程序已安全关闭")

if __name__ == "__main__":
    try:
        # 根据系统和Python版本设置正确的事件循环策略
        if platform.system() == "Windows":
            # Windows需要使用特定策略
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Python 3.10+ 推荐的方式
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序中断，正在退出...")
    except Exception as e:
        logger.error(f"发生异常: {e}", exc_info=True)
        sys.exit(1)