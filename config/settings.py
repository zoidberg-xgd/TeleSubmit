"""
配置文件读取和变量定义模块
"""
import os
import configparser

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.ini')

# 读取配置文件
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

# 从环境变量或配置文件获取配置
TOKEN = os.getenv('TOKEN', config.get('BOT', 'TOKEN'))
CHANNEL_ID = os.getenv('CHANNEL_ID', config.get('BOT', 'CHANNEL_ID'))
DB_PATH = config.get('BOT', 'DB_PATH', fallback='submissions.db')
TIMEOUT = config.getint('BOT', 'TIMEOUT', fallback=300)    # 会话超时时间（秒）
ALLOWED_TAGS = config.getint('BOT', 'ALLOWED_TAGS', fallback=10)
NET_TIMEOUT = 120   # 网络请求超时时间（秒）