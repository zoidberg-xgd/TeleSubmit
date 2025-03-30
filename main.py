"""
Telegram 投稿机器人主程序
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

from config.settings import TOKEN, TIMEOUT
from models.state import STATE
from database.db_manager import init_db, cleanup_old_data
from utils.logging_config import setup_logging
from handlers.command_handlers import start, cancel, debug, catch_all
from handlers.error_handler import error_handler
from handlers.conversation_handlers import (
    handle_media, 
    done_media, 
    handle_tag, 
    handle_link, 
    handle_title, 
    handle_note, 
    handle_spoiler,
    skip_optional_link,
    skip_optional_title,
    skip_optional_note,
    prompt_media
)

# 设置日志
logger = setup_logging()

def error_callback(_, context):
    """
    处理作业队列中的错误
    """
    logger.error(f"作业队列错误: {context.error}")

async def setup_application():
    """
    初始化和配置应用程序
    """
    # 初始化数据库
    await init_db()

    # 创建应用
    application = Application.builder().token(TOKEN).build()
    
    # 会话处理器
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            STATE['MEDIA']: [
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.AUDIO | filters.Document.ALL, handle_media),
                CommandHandler('done', done_media),
                MessageHandler(filters.TEXT & ~filters.COMMAND, prompt_media)
            ],
            STATE['TAG']: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tag)],
            STATE['LINK']: [
                CommandHandler('skip_optional', skip_optional_link),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
            ],
            STATE['TITLE']: [
                CommandHandler('skip_optional', skip_optional_title),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title)
            ],
            STATE['NOTE']: [
                CommandHandler('skip_optional', skip_optional_note),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note)
            ],
            STATE['SPOILER']: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_spoiler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=TIMEOUT
    )
    
    # 添加处理器
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('debug', debug))
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
    logger.info("Bot 已启动并正在运行...")
    
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