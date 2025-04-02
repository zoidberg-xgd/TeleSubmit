# TeleSubmit - 电报频道投稿助手

一个帮助用户轻松向频道提交内容的 Telegram 机器人。该机器人支持媒体文件和文档文件，具有灵活的配置选项。

## 功能特点

- **多种提交类型**:
  - **媒体模式**: 上传照片、视频、GIF 和音频文件
  - **文档模式**: 上传文档文件（PDF、DOC、TXT 等）
  - **混合模式**: 在一次提交中同时支持媒体和文档上传
  
- **可配置模式**: 根据需要选择仅媒体、仅文档或混合模式

- **批量上传**: 在一次提交中上传多个文件（媒体模式最多50个文件，文档模式最多10个文件）

- **必选标签**: 添加可搜索的标签，帮助分类内容

- **可选信息**: 为提交添加链接、标题和说明

- **剧透选项**: 将敏感内容标记为剧透，需要用户点击才能查看

- **会话管理**: 自动清理过期的会话

- **用户友好**: 逐步引导式提交流程

- **所有者与黑名单**:
  - 设置机器人所有者，专享管理权限
  - 黑名单功能，禁止特定用户使用机器人
  - 投稿人信息显示，方便追踪内容来源

## 项目结构

```
telegram_submission_bot/
├── config/                   # 配置设置
│   ├── __init__.py
│   └── settings.py
├── database/                 # 数据库操作
│   ├── __init__.py
│   └── db_manager.py
├── handlers/                 # 消息处理器
│   ├── __init__.py
│   ├── command_handlers.py
│   ├── document_handlers.py
│   ├── media_handlers.py
│   ├── mode_selection.py
│   ├── publish.py
│   ├── submit_handlers.py
│   └── error_handler.py
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── blacklist.py         # 黑名单管理
│   ├── logging_config.py
│   └── helper_functions.py
├── models/                   # 数据模型
│   ├── __init__.py
│   └── state.py
├── config.ini               # 配置文件
├── main.py                  # 主程序
└── requirements.txt         # 依赖项
```

## 安装

1. 克隆仓库：
   ```bash
   git clone https://github.com/zoidberg-xgd/TeleSubmit.git
   cd TeleSubmit
   ```

2. 安装所需的包：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置机器人：
   编辑 `config.ini` 文件，添加您的 Telegram 机器人令牌、频道 ID 和所有者 ID：
   ```ini
   [BOT]
   TOKEN = your_bot_token_here
   CHANNEL_ID = @your_channel_id_here
   DB_PATH = submissions.db
   TIMEOUT = 300
   ALLOWED_TAGS = 30
   # 选项: MEDIA, DOCUMENT, MIXED
   BOT_MODE = MIXED
   # 设置机器人所有者的Telegram数字用户ID（必须是数字ID，不能是用户名）
   OWNER_ID = 123456789
   # 是否在投稿内容尾部显示投稿人信息（True/False）
   SHOW_SUBMITTER = True
   ```

## 使用方法

1. 启动机器人：
   ```bash
   python main.py
   ```

2. 在 Telegram 中，打开机器人并发送 `/start` 命令

3. 如果在混合模式下，选择提交类型（媒体或文档）

4. 按照逐步流程提交内容：
   - 上传媒体/文档文件，完成后发送 `/done_media` 或 `/done_doc`
   - 添加标签（必选）
   - 添加链接（可选）
   - 添加标题（可选）
   - 添加简介（可选）
   - 选择是否将内容标记为剧透

## 命令

### 普通用户命令
- `/start` - 开始新的提交
- `/done_doc` - 完成文档上传
- `/done_media` - 完成媒体上传
- `/skip_media` - 跳过媒体上传（混合模式下文档上传后）
- `/skip_optional` - 跳过所有剩余的可选字段
- `/cancel` - 取消当前提交
- `/debug` - 调试命令（用于开发）

### 管理员命令（仅所有者可用）
- `/blacklist_add <用户ID> [原因]` - 将用户添加到黑名单
- `/blacklist_remove <用户ID>` - 从黑名单中移除用户
- `/blacklist_list` - 显示当前黑名单列表

## 黑名单功能

1. **获取用户ID**：
   - 通过投稿内容尾部的"投稿人"链接查看用户资料
   - 使用 [@userinfobot](https://t.me/userinfobot) 或 [@RawDataBot](https://t.me/RawDataBot) 获取用户的数字ID

2. **管理黑名单**：
   - 将用户添加到黑名单：`/blacklist_add 123456789 违规内容`
   - 从黑名单中移除用户：`/blacklist_remove 123456789`
   - 查看当前黑名单列表：`/blacklist_list`

3. **配置选项**：
   - 在 `config.ini` 中设置 `SHOW_SUBMITTER = True` 可在投稿尾部显示投稿人信息
   - 设置 `SHOW_SUBMITTER = False` 可隐藏投稿人信息

## 要求

- Python 3.7+
- python-telegram-bot>=20.0
- aiosqlite>=0.17.0

## 许可证

MIT 许可证