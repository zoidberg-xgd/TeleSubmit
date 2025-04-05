# TeleSubmit - 电报频道投稿助手

一个帮助用户轻松向频道提交内容的 Telegram 机器人。支持媒体文件和文档文件，具有灵活的配置选项和强大的错误处理机制。

## 功能特点

- **多种提交类型**:
  - **媒体模式**: 上传照片、视频、GIF 和音频文件
  - **文档模式**: 上传文档文件（PDF、DOC、TXT 等）
  - **混合模式**: 在一次提交中同时支持媒体和文档上传
  
- **批量上传**: 媒体模式最多50个文件，文档模式最多10个文件

- **标签系统**: 添加可搜索的标签，帮助分类内容（必选字段）

- **丰富元数据**: 为提交添加链接、标题和说明（可选字段）

- **剧透标记**: 将敏感内容标记为剧透，需要用户点击才能查看

- **会话管理**: 自动清理过期的会话，优化资源使用

- **用户友好**: 逐步引导式提交流程，简单易用

- **权限控制**:
  - 设置机器人所有者，专享管理权限
  - 黑名单功能，禁止特定用户使用机器人
  - 投稿人信息显示，方便追踪内容来源

- **高可靠性**:
  - 完善的错误处理机制
  - 网络请求重试逻辑
  - 数据库操作安全保障

## 安装指南

1. **克隆仓库**:
   ```bash
   git clone https://github.com/zoidberg-xgd/TeleSubmit.git
   cd TeleSubmit
   ```

2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

3. **配置机器人**:
   ```bash
   # 复制示例配置文件
   cp config.ini.example config.ini
   
   # 或使用环境变量配置
   cp .env.example .env
   
   # 编辑配置文件，填入您的Telegram机器人令牌、频道ID和所有者ID
   nano config.ini
   ```

4. **启动机器人**:
   ```bash
   python main.py
   ```

## 配置说明

### 基本配置 (config.ini)

```ini
[BOT]
# Telegram机器人令牌
TOKEN = your_bot_token_here

# 目标频道ID
CHANNEL_ID = @your_channel_name

# 数据库文件路径
DB_PATH = submissions.db

# 会话超时时间（秒）
TIMEOUT = 300

# 最多允许的标签数量
ALLOWED_TAGS = 30

# 机器人工作模式: MEDIA, DOCUMENT, MIXED
BOT_MODE = MIXED

# 机器人所有者ID
OWNER_ID = your_user_id_here

# 是否显示投稿人信息
SHOW_SUBMITTER = True

# 是否向所有者发送投稿通知
NOTIFY_OWNER = True
```

### 环境变量配置 (.env)

也可以使用环境变量方式配置（推荐用于生产环境）:

```
TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_name
OWNER_ID=your_user_id_here
SESSION_TIMEOUT=300
DB_PATH=submissions.db
BOT_MODE=MIXED
SHOW_SUBMITTER=True
NOTIFY_OWNER=True
```

## 使用方法

1. 在 Telegram 中，搜索并打开您配置的机器人

2. 发送 `/start` 命令开始新的提交

3. 根据提示选择提交类型（如果在混合模式下）

4. 按照逐步流程提交内容:
   - 上传文件，完成后发送 `/done_media` 或 `/done_doc`
   - 添加标签（必选，使用空格分隔多个标签）
   - 添加链接（可选，可跳过）
   - 添加标题（可选，可跳过）
   - 添加简介（可选，可跳过）
   - 选择是否将内容标记为剧透
   - 确认提交

## 命令列表

### 普通用户命令
- `/start` - 开始新的提交
- `/done_doc` - 完成文档上传
- `/done_media` - 完成媒体上传
- `/skip_media` - 跳过媒体上传
- `/skip_optional` - 跳过剩余可选字段
- `/cancel` - 取消当前提交

### 管理员命令（仅所有者可用）
- `/blacklist_add <用户ID> [原因]` - 将用户添加到黑名单
- `/blacklist_remove <用户ID>` - 从黑名单中移除用户
- `/blacklist_list` - 显示当前黑名单列表
- `/debug` - 显示系统调试信息

## 项目结构

```
TeleSubmit/
│
├── config/                   # 配置设置
│   ├── __init__.py
│   └── settings.py           # 配置加载与管理
│
├── database/                 # 数据库操作
│   ├── __init__.py
│   └── db_manager.py         # 数据库管理
│
├── handlers/                 # 消息处理器
│   ├── __init__.py
│   ├── command_handlers.py   # 命令处理
│   ├── conversation_handlers.py # 会话处理
│   ├── document_handlers.py  # 文档处理
│   ├── error_handler.py      # 错误处理
│   ├── media_handlers.py     # 媒体处理
│   ├── mode_selection.py     # 模式选择
│   ├── publish.py            # 发布逻辑
│   └── submit_handlers.py    # 提交处理
│
├── models/                   # 数据模型
│   ├── __init__.py
│   └── state.py              # 状态定义
│
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── blacklist.py          # 黑名单管理
│   ├── database.py           # 数据库工具
│   ├── helper_functions.py   # 辅助功能
│   └── logging_config.py     # 日志配置
│
├── logs/                     # 日志目录 (自动创建)
├── .env.example              # 环境变量示例
├── .gitignore                # Git忽略文件
├── config.ini.example        # 配置文件示例
├── main.py                   # 主程序
├── README.md                 # 说明文档
└── requirements.txt          # 依赖项
```

## 黑名单功能使用指南

1. **获取用户ID**:
   - 使用 [@userinfobot](https://t.me/userinfobot) 获取用户的数字ID
   - 通过投稿内容尾部的"投稿人"链接查看用户资料
   - 接收机器人发送的投稿通知（当`NOTIFY_OWNER=True`时）

2. **管理命令**:
   - 添加黑名单: `/blacklist_add 123456789 违规内容`
   - 移除黑名单: `/blacklist_remove 123456789`
   - 查看黑名单: `/blacklist_list`

## 系统要求

- Python 3.7+
- python-telegram-bot >= 20.0
- aiosqlite >= 0.17.0

## 许可证

MIT 许可证