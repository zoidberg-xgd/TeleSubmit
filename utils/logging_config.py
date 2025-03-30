"""
日志配置模块
"""
import logging

class TimeoutMessageFilter(logging.Filter):
    """
    超时消息过滤器，将超时错误降级为警告
    """
    def filter(self, record):
        # 如果是ERROR级别且消息中包含超时关键词
        if record.levelno == logging.ERROR and any(kw in record.getMessage().lower() 
                                                  for kw in ["timeout", "超时", "timed out"]):
            # 将级别降为WARNING
            record.levelno = logging.WARNING
            record.levelname = "WARNING"
        return True

# 配置基本日志
def setup_logging():
    """
    设置日志配置
    """
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO  # 将日志级别调整为 INFO
    )
    logger = logging.getLogger(__name__)
    logger.addFilter(TimeoutMessageFilter())
    return logger