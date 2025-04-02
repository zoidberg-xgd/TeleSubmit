"""
Telegram 投稿机器人主程序
支持媒体和文档投稿
"""
import asyncio
import logging
import platform
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

from config.settings import TOKEN, TIMEOUT, BOT_MODE, MODE_MEDIA, MODE_DOCUMENT, MODE_MIXED
from models.state import STATE
from database.db_manager import init_db, cleanup_old_data
from utils.logging_config import setup_logging
from utils.blacklist import init_blacklist, blacklist_filter
from handlers.mode_selection import start, select_mode
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
from handlers.command_handlers import (
    cancel, 
    debug, 
    catch_all,
    blacklist_add,
    blacklist_remove,
    blacklist_list
)
from handlers.error_handler import error_handler

# 设置日志
logger = setup_logging()

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
        conversation_timeout=TIMEOUT
    )
    
    # 添加处理器
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('debug', debug))
    
    # 添加黑名单管理命令
    application.add_handler(CommandHandler('blacklist_add', blacklist_add))
    application.add_handler(CommandHandler('blacklist_remove', blacklist_remove))
    application.add_handler(CommandHandler('blacklist_list', blacklist_list))
    
    # 默认消息处理器
    application.add_handler(MessageHandler(filters.ALL, catch_all))
    application.add_error_handler(error_handler)
    
    # 添加周期性清理任务
    job_queue = application.job_queue
    job_queue.run_repeating(
        lambda context: asyncio.create_task(cleanup_old_data()), 
        interval=300, 
        first=10
    )
    
    return application

async def main():
    """
    主函数 - 设置并启动机器人
    """
    # 配置应用
    app = await setup_application()
    
    # 启动机器人，停止信号时优雅退出
    await app.initialize()
    await app.start()
    logger.info(f"Bot 已启动并正在运行（模式: {BOT_MODE}）...")
    
    try:
        await app.updater.start_polling()
        # 保持应用运行
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("接收到退出信号，正在停止...")
    finally:
        # 确保应用干净地关闭
        await app.stop()
        await app.shutdown()
        logger.info("Bot 已停止")

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