"""
黑名单管理模块
"""
import logging
import aiosqlite
from typing import List, Set, Optional

from database.db_manager import get_db
from config.settings import OWNER_ID

logger = logging.getLogger(__name__)

# 内存中的黑名单缓存
_blacklist: Set[int] = set()

# 自定义黑名单过滤器函数
def blacklist_filter(update):
    """过滤黑名单用户"""
    if update.effective_user and is_blacklisted(update.effective_user.id):
        logger.warning(f"拦截黑名单用户: {update.effective_user.id}")
        return False
    return True

async def init_blacklist():
    """初始化黑名单表并加载到内存"""
    try:
        async with get_db() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    user_id INTEGER PRIMARY KEY,
                    reason TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.commit()
            
            # 加载黑名单到内存
            async with conn.execute("SELECT user_id FROM blacklist") as cursor:
                rows = await cursor.fetchall()
                _blacklist.clear()
                for row in rows:
                    _blacklist.add(row[0])
                    
        logger.info(f"黑名单已初始化，当前有 {len(_blacklist)} 个用户")
    except Exception as e:
        logger.error(f"初始化黑名单时出错: {e}")

async def add_to_blacklist(user_id: int, reason: str = "未指定原因") -> bool:
    """
    添加用户到黑名单
    
    Args:
        user_id: 要添加的用户ID
        reason: 添加原因
        
    Returns:
        bool: 是否成功添加
    """
    try:
        async with get_db() as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO blacklist (user_id, reason) VALUES (?, ?)",
                (user_id, reason)
            )
            await conn.commit()
            
        # 更新内存缓存
        _blacklist.add(user_id)
        logger.info(f"已将用户 {user_id} 添加到黑名单，原因: {reason}")
        return True
    except Exception as e:
        logger.error(f"添加用户到黑名单时出错: {e}")
        return False

async def remove_from_blacklist(user_id: int) -> bool:
    """
    从黑名单中移除用户
    
    Args:
        user_id: 要移除的用户ID
        
    Returns:
        bool: 是否成功移除
    """
    try:
        async with get_db() as conn:
            await conn.execute("DELETE FROM blacklist WHERE user_id = ?", (user_id,))
            await conn.commit()
            
            if user_id in _blacklist:
                _blacklist.remove(user_id)
                logger.info(f"已将用户 {user_id} 从黑名单中移除")
                return True
            else:
                logger.info(f"用户 {user_id} 不在黑名单中")
                return False
    except Exception as e:
        logger.error(f"从黑名单中移除用户时出错: {e}")
        return False

async def get_blacklist() -> List[dict]:
    """
    获取完整黑名单
    
    Returns:
        List[dict]: 黑名单用户列表，每个用户包含 user_id, reason, added_at
    """
    try:
        async with get_db() as conn:
            async with conn.execute(
                "SELECT user_id, reason, added_at FROM blacklist ORDER BY added_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {"user_id": row[0], "reason": row[1], "added_at": row[2]}
                    for row in rows
                ]
    except Exception as e:
        logger.error(f"获取黑名单时出错: {e}")
        return []

def is_blacklisted(user_id: int) -> bool:
    """
    检查用户是否在黑名单中
    
    Args:
        user_id: 要检查的用户ID
        
    Returns:
        bool: 用户是否在黑名单中
    """
    return user_id in _blacklist

def is_owner(user_id: int) -> bool:
    """
    检查用户是否为机器人所有者
    
    Args:
        user_id: 要检查的用户ID
        
    Returns:
        bool: 用户是否为机器人所有者
    """
    if not OWNER_ID:
        return False
    return str(user_id) == OWNER_ID 