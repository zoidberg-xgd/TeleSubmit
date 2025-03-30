"""
数据库管理模块
"""
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import aiosqlite

from config.settings import DB_PATH, TIMEOUT

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_db():
    """
    数据库连接上下文管理器
    
    Yields:
        aiosqlite.Connection: 数据库连接对象
    """
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
        await conn.commit()
    except Exception as e:
        await conn.rollback()
        raise e
    finally:
        await conn.close()

async def init_db():
    """
    初始化数据库，创建表结构
    """
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            c = await conn.cursor()
            await c.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    user_id INTEGER PRIMARY KEY,
                    link TEXT,
                    image_id TEXT,
                    tags TEXT,
                    title TEXT,
                    note TEXT,
                    spoiler TEXT,
                    timestamp REAL
                )
            ''')
            await conn.commit()
            # 检查并添加缺失的列
            await c.execute("PRAGMA table_info(submissions)")
            columns = [info[1] for info in await c.fetchall()]
            if "title" not in columns:
                await c.execute("ALTER TABLE submissions ADD COLUMN title TEXT")
                await conn.commit()
                logger.info("已添加 'title' 列到 submissions 表")
            if "note" not in columns:
                await c.execute("ALTER TABLE submissions ADD COLUMN note TEXT")
                await conn.commit()
                logger.info("已添加 'note' 列到 submissions 表")
            if "spoiler" not in columns:
                await c.execute("ALTER TABLE submissions ADD COLUMN spoiler TEXT")
                await conn.commit()
                logger.info("已添加 'spoiler' 列到 submissions 表")
            logger.info("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化错误: {e}")

async def cleanup_old_data():
    """
    清理过期的会话数据
    """
    try:
        # 首先检查表是否存在
        async with aiosqlite.connect(DB_PATH) as conn:
            c = await conn.cursor()
            await c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='submissions'")
            table_exists = await c.fetchone()
            
        if not table_exists:
            logger.warning("submissions 表不存在，跳过清理")
            return
            
        # 如果表存在，执行清理
        async with get_db() as conn:
            c = await conn.cursor()
            cutoff = datetime.now().timestamp() - TIMEOUT
            await c.execute("DELETE FROM submissions WHERE timestamp < ?", (cutoff,))
            logger.info("已清理过期数据")
    except Exception as e:
        logger.error(f"清理过期数据失败: {e}")