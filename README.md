# TeleSubmit - Telegram Channel Submission Assistant
# 电报频道投稿助手

[English](#english) | [中文](#chinese)

<a id="english"></a>
## English

A Telegram bot designed to help users submit content to channels with ease. This bot supports multiple media types, tags, and optional information such as links, titles, notes, and spoiler settings.

### Features

- **Multiple Media Support**: Upload photos, videos, GIFs, and audio files
- **Batch Upload**: Submit multiple media files in a single submission
- **Required Tags**: Add searchable tags to help categorize content
- **Optional Information**: Add links, titles, and descriptions to your submission
- **Spoiler Option**: Mark sensitive content with a spoiler tag requiring users to click to view
- **Session Management**: Automatic cleanup of expired sessions
- **User-Friendly**: Step-by-step guided submission process

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/zoidberg-xgd/TeleSubmit.git
   cd TeleSubmit
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the bot:
   Edit the `config.ini` file and add your Telegram Bot Token and Channel ID:
   ```ini
   [BOT]
   TOKEN = your_bot_token_here
   CHANNEL_ID = @your_channel_id_here
   DB_PATH = submissions.db
   TIMEOUT = 300
   ALLOWED_TAGS = 10
   ```

### Usage

1. Start the bot:
   ```bash
   python main.py
   ```

2. In Telegram, open the bot and send the `/start` command

3. Follow the step-by-step process to submit content:
   - Upload media files (required) and send `/done` when finished
   - Add tags (required)
   - Add a link (optional)
   - Add a title (optional)
   - Add a description (optional)
   - Choose whether to mark media as spoilers

### Commands

- `/start` - Begin a new submission
- `/done` - Complete media upload
- `/skip_optional` - Skip all remaining optional fields
- `/cancel` - Cancel the current submission
- `/debug` - Debug command (for development use)

### Requirements

- Python 3.7+
- python-telegram-bot>=20.0
- aiosqlite>=0.17.0

### License

MIT License

---

<a id="chinese"></a>
## 中文

一个帮助用户轻松向频道提交内容的 Telegram 机器人。该机器人支持多种媒体类型、标签，以及可选的链接、标题、简介和剧透设置。

### 功能特点

- **多媒体支持**：上传照片、视频、GIF 和音频文件
- **批量上传**：在一次提交中上传多个媒体文件
- **必选标签**：添加可搜索的标签，帮助分类内容
- **可选信息**：为提交添加链接、标题和说明
- **剧透选项**：将敏感内容标记为剧透，需要用户点击才能查看
- **会话管理**：自动清理过期的会话
- **用户友好**：逐步引导式提交流程

### 安装

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
   编辑 `config.ini` 文件，添加您的 Telegram 机器人令牌和频道 ID：
   ```ini
   [BOT]
   TOKEN = your_bot_token_here
   CHANNEL_ID = @your_channel_id_here
   DB_PATH = submissions.db
   TIMEOUT = 300
   ALLOWED_TAGS = 10
   ```

### 使用方法

1. 启动机器人：
   ```bash
   python main.py
   ```

2. 在 Telegram 中，打开机器人并发送 `/start` 命令

3. 按照逐步流程提交内容：
   - 上传媒体文件（必选），完成后发送 `/done`
   - 添加标签（必选）
   - 添加链接（可选）
   - 添加标题（可选）
   - 添加简介（可选）
   - 选择是否将媒体标记为剧透

### 命令

- `/start` - 开始新的提交
- `/done` - 完成媒体上传
- `/skip_optional` - 跳过所有剩余的可选字段
- `/cancel` - 取消当前提交
- `/debug` - 调试命令（用于开发）

### 要求

- Python 3.7+
- python-telegram-bot>=20.0
- aiosqlite>=0.17.0

### 许可证

MIT 许可证
