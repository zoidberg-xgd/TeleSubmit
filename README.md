# TeleSubmit - 电报频道投稿助手

一个帮助用户轻松向频道提交内容的 Telegram 机器人。支持媒体文件和文档文件的灵活投稿，提供流畅的用户体验和强大的错误处理机制。

## 功能特点

- **多种提交模式**:
  - **媒体模式**: 上传照片、视频、GIF 和音频文件
  - **文档模式**: 上传文档文件（PDF、DOC、ZIP、RAR等压缩包等）
  - **混合模式**: 在一次提交中同时支持媒体和文档上传
  
- **灵活的模式切换**:
  - 在媒体模式下可一键切换到文档模式
  - 动态适应不同类型的文件投稿需求

- **批量上传**: 
  - 媒体模式下支持大量媒体上传（最多50个，自动分组发送）
  - 文档模式下最多上传10个文件
  - 文档模式下的媒体附件最多10个
  - 支持多种格式混合上传
  - 自动处理说明文本过长的情况，确保所有媒体都能正确发送

- **标签系统**: 添加可搜索的标签，帮助分类内容（必选字段，最多30个）

- **丰富元数据**: 为提交添加链接、标题和说明（可选字段）

- **剧透标记**: 将敏感内容标记为剧透，需要用户点击才能查看

- **会话管理**: 
  - 自动清理过期的会话，优化资源使用
  - 会话状态验证，确保操作顺序正确
  - 超时自动结束，防止资源浪费

- **用户友好**: 
  - 逐步引导式提交流程，简单易用
  - 清晰的错误提示和操作指南
  - 简化的提示消息，减少用户阅读负担

- **权限控制**:
  - 设置机器人所有者，专享管理权限
  - 黑名单功能，禁止特定用户使用机器人
  - 投稿人信息显示，方便追踪内容来源

- **高可靠性**:
  - 完善的错误处理和日志记录机制
  - 网络请求安全重试
  - 数据库操作事务保障
  - 异常状态自动恢复

## 快速开始

### 🚀 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/zoidberg-xgd/TeleSubmit.git
cd TeleSubmit

# 2. 给脚本添加执行权限
chmod +x deploy.sh

# 3. 运行一键部署
./deploy.sh
```

首次运行会自动创建配置文件 `config.ini`，按提示编辑后再次运行 `./deploy.sh` 即可启动机器人。

## 安装指南

### 方式一：Docker 部署（推荐）⭐

使用 Docker 部署是最简单快捷的方式，无需手动安装 Python 环境和依赖。

**优势**:
- ✅ 环境隔离，避免依赖冲突
- ✅ 一键启动，无需手动配置 Python 环境
- ✅ 自动重启，提高服务稳定性
- ✅ 资源限制，防止占用过多系统资源
- ✅ 日志管理，自动轮转日志文件
- ✅ 数据持久化，容器重启数据不丢失

**系统要求**:
- Docker >= 20.10
- Docker Compose >= 1.29

#### 方法 A：一键部署脚本（最简单）

```bash
# 1. 克隆仓库
git clone https://github.com/zoidberg-xgd/TeleSubmit.git
cd TeleSubmit

# 2. 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：
- ✅ 检查 Docker 环境
- ✅ 创建配置文件（如果不存在）
- ✅ 创建必要的目录
- ✅ 构建 Docker 镜像
- ✅ 启动容器
- ✅ 检查运行状态

首次运行时会提示编辑配置文件，编辑完成后再次运行 `./deploy.sh` 即可。

#### 方法 B：手动 Docker Compose

```bash
# 1. 克隆仓库
git clone https://github.com/zoidberg-xgd/TeleSubmit.git
cd TeleSubmit

# 2. 创建配置文件
cp config.ini.example config.ini
nano config.ini  # 编辑配置

# 3. 创建必要目录
mkdir -p data logs

# 4. 启动容器
docker-compose up -d

# 5. 查看日志
docker-compose logs -f
```

#### 方法 C：使用 Makefile 命令（最方便）

```bash
# 查看所有可用命令
make help

# 一键部署
make deploy

# 常用命令
make up        # 启动容器
make down      # 停止容器
make restart   # 重启容器
make logs      # 查看日志
make status    # 查看状态
make backup    # 备份数据
make update    # 更新版本
```

#### 方法 D：使用 Docker 命令

```bash
# 1. 构建镜像
docker build -t telesubmit .

# 2. 创建目录
mkdir -p data logs

# 3. 启动容器
docker run -d \
  --name telesubmit-bot \
  --restart unless-stopped \
  -v $(pwd)/config.ini:/app/config.ini:ro \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  telesubmit

# 4. 查看日志
docker logs -f telesubmit-bot
```

### 方式二：传统部署

如果您不使用 Docker，可以按照以下步骤部署：

**系统要求**:
- Python 3.7+
- pip (Python 包管理器)

```bash
# 1. 克隆仓库
git clone https://github.com/zoidberg-xgd/TeleSubmit.git
cd TeleSubmit

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建配置文件
cp config.ini.example config.ini
nano config.ini  # 编辑配置

# 4. 启动机器人
python bot.py

# 5. 后台运行（可选）
# 使用 screen
screen -S telesubmit
python bot.py
# 按 Ctrl+A+D 退出

# 或使用 tmux
tmux new -s telesubmit
python bot.py
# 按 Ctrl+B+D 退出

# 或使用 nohup
nohup python bot.py > output.log 2>&1 &
```

## 配置说明

### 基本配置 (config.ini)

```ini
[BOT]
# Telegram机器人令牌（必填）
# 从 @BotFather 获取
TOKEN = your_bot_token_here

# 目标频道ID（必填）
# 格式: @channel_username 或 -100xxxxxxxxxx
CHANNEL_ID = @your_channel_name

# 机器人所有者ID（必填）
# 从 @userinfobot 获取您的用户ID
OWNER_ID = your_user_id_here

# 数据库文件路径（可选）
DB_PATH = submissions.db

# 会话超时时间（秒）（可选）
TIMEOUT = 300

# 最多允许的标签数量（可选）
ALLOWED_TAGS = 30

# 机器人工作模式（可选）
# MEDIA: 仅媒体模式
# DOCUMENT: 仅文档模式
# MIXED: 混合模式（推荐）
BOT_MODE = MIXED

# 是否显示投稿人信息（可选）
SHOW_SUBMITTER = True

# 是否向所有者发送投稿通知（可选）
NOTIFY_OWNER = True
```

### 环境变量配置 (.env)

也可以使用环境变量方式配置（推荐用于 Docker 部署）:

```bash
# 创建 .env 文件
cat > .env << EOF
TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_name
OWNER_ID=your_user_id_here
SESSION_TIMEOUT=300
DB_PATH=submissions.db
BOT_MODE=MIXED
SHOW_SUBMITTER=True
NOTIFY_OWNER=True
EOF
```

在 `docker-compose.yml` 中使用：

```yaml
environment:
  - BOT_TOKEN=${TOKEN}
  - CHANNEL_ID=${CHANNEL_ID}
  - OWNER_ID=${OWNER_ID}
```

## 使用方法

1. 在 Telegram 中，搜索并打开您配置的机器人

2. 发送 `/start` 命令开始新的提交

3. 根据提示选择提交类型（如果在混合模式下）:
   - 媒体模式：适用于图片、视频、GIF等媒体文件
   - 文档模式：适用于文档、压缩包等文件

4. 按照逐步流程提交内容:
   - **上传文件**：
     - 媒体模式：直接发送媒体文件（非文件附件形式），支持大批量上传（最多50个）
     - 文档模式：通过文件附件形式发送文档，最多10个
     - 完成后发送 `/done_media` 或 `/done_doc`
   - **模式切换**：
     - 在媒体模式下，如果发送了文件附件，可点击"切换到文档模式"按钮无缝切换
   - **添加标签**：必选，最多30个，用逗号分隔多个标签
   - **添加链接**：可选，可使用 `/skip_optional` 跳过
   - **添加标题**：可选，可使用 `/skip_optional` 跳过
   - **添加简介**：可选，可使用 `/skip_optional` 跳过
   - **剧透设置**：选择是否将内容标记为剧透
   - **确认提交**：最终确认并发布到频道

5. 取消投稿：随时发送 `/cancel` 取消当前投稿

## 命令列表

### 普通用户命令
- `/start` - 开始新的提交
- `/done_doc` - 完成文档上传
- `/done_media` - 完成媒体上传
- `/skip_media` - 跳过媒体上传（仅在文档/混合模式下可用）
- `/skip_optional` - 跳过当前可选字段
- `/cancel` - 取消当前提交

### 管理员命令（仅所有者可用）
- `/blacklist_add <用户ID> [原因]` - 将用户添加到黑名单
- `/blacklist_remove <用户ID>` - 从黑名单中移除用户
- `/blacklist_list` - 显示当前黑名单列表
- `/debug` - 显示系统调试信息

## Docker 管理

### 容器管理

```bash
# 启动容器
docker-compose up -d

# 停止容器
docker-compose stop

# 重启容器
docker-compose restart

# 删除容器
docker-compose down

# 重新构建并启动
docker-compose up -d --build

# 查看容器状态
docker-compose ps

# 进入容器 shell
docker-compose exec telesubmit /bin/bash
```

### 日志查看

```bash
# 实时查看日志
docker-compose logs -f

# 查看最近 100 行日志
docker-compose logs --tail=100

# 查看容器内的日志文件
docker-compose exec telesubmit tail -f /app/logs/telesubmit_$(date +%Y-%m-%d).log
```

### 资源监控

```bash
# 查看容器资源使用
docker stats telesubmit-bot

# 查看容器详细信息
docker inspect telesubmit-bot
```

### 数据备份

```bash
# 完整备份（推荐）
tar -czf telesubmit-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  config.ini data/ logs/

# 仅备份数据库
cp data/submissions.db data/submissions.db.$(date +%Y%m%d-%H%M%S).bak

# 使用 Makefile
make backup
```

### 数据恢复

```bash
# 停止容器
docker-compose down

# 恢复完整备份
tar -xzf telesubmit-backup-20241018-120000.tar.gz

# 或恢复数据库
cp data/submissions.db.20241018-120000.bak data/submissions.db

# 重启容器
docker-compose up -d
```

### 更新机器人

```bash
# 方法 1: 使用 Makefile（推荐）
make update

# 方法 2: 手动更新
# 1. 备份数据
tar -czf backup-before-update-$(date +%Y%m%d).tar.gz config.ini data/ logs/

# 2. 停止容器
docker-compose down

# 3. 拉取最新代码
git pull

# 4. 重新构建
docker-compose build --no-cache

# 5. 启动容器
docker-compose up -d

# 6. 查看日志
docker-compose logs -f
```

## 故障排查

### 容器无法启动

```bash
# 1. 查看详细日志
docker-compose logs

# 2. 检查配置文件
cat config.ini

# 3. 检查配置文件格式
docker-compose config

# 4. 检查端口占用
netstat -tlnp | grep <port>

# 5. 检查磁盘空间
df -h

# 6. 清理 Docker 缓存
docker system prune -a
```

### 机器人无响应

```bash
# 1. 检查容器状态
docker-compose ps

# 2. 查看实时日志
docker-compose logs -f

# 3. 检查网络连接
docker-compose exec telesubmit ping -c 3 api.telegram.org

# 4. 重启容器
docker-compose restart

# 5. 完全重新部署
docker-compose down
docker-compose up -d --build
```

### 权限问题

```bash
# 修复目录权限
sudo chown -R $(id -u):$(id -g) data/ logs/
chmod 755 data/ logs/

# 检查 SELinux（如果使用）
sestatus
# 如果 SELinux 导致问题，可以临时禁用
sudo setenforce 0
```

### 内存/CPU 占用过高

编辑 `docker-compose.yml` 调整资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'      # 减少 CPU 限制
      memory: 256M     # 减少内存限制
```

然后重启容器：

```bash
docker-compose down
docker-compose up -d
```

## 项目结构

```
TeleSubmit/
│
├── config/                   # 配置管理
│   ├── __init__.py
│   └── settings.py           # 配置加载与管理
│
├── database/                 # 数据库操作
│   ├── __init__.py
│   └── db_manager.py         # 数据库连接与操作
│
├── handlers/                 # 消息处理器
│   ├── __init__.py           # 处理器导出
│   ├── command_handlers.py   # 命令处理逻辑
│   ├── conversation_handlers.py # 会话流程处理
│   ├── document_handlers.py  # 文档文件处理
│   ├── error_handler.py      # 错误处理与恢复
│   ├── media_handlers.py     # 媒体文件处理
│   ├── mode_selection.py     # 提交模式选择
│   ├── publish.py            # 内容发布逻辑
│   └── submit_handlers.py    # 表单数据处理
│
├── models/                   # 数据模型
│   ├── __init__.py
│   └── state.py              # 会话状态定义
│
├── utils/                    # 实用工具
│   ├── __init__.py
│   ├── blacklist.py          # 黑名单管理功能
│   ├── database.py           # 数据库工具函数
│   ├── helper_functions.py   # 通用辅助函数
│   └── logging_config.py     # 日志配置
│
├── data/                     # 数据目录 (自动创建)
├── logs/                     # 日志目录 (自动创建)
├── .dockerignore             # Docker 忽略文件
├── .env.example              # 环境变量示例
├── .gitignore                # Git 忽略文件
├── bot.py                    # 主程序入口
├── config.ini.example        # 配置文件示例
├── deploy.sh                 # 一键部署脚本
├── docker-compose.yml        # Docker Compose 配置
├── Dockerfile                # Docker 镜像构建文件
├── Makefile                  # Make 命令快捷方式
├── README.md                 # 完整说明文档（本文件）
└── requirements.txt          # Python 依赖项清单
```

## 黑名单功能

### 获取用户ID

1. 使用 [@userinfobot](https://t.me/userinfobot) 获取用户的数字ID
2. 通过投稿内容尾部的"投稿人"链接查看用户资料
3. 接收机器人发送的投稿通知（当`NOTIFY_OWNER=True`时）

### 管理命令

```bash
# 添加黑名单
/blacklist_add 123456789 违规内容

# 移除黑名单
/blacklist_remove 123456789

# 查看黑名单
/blacklist_list
```

## 日志与调试

### 日志文件

- 日志保存在 `logs/` 目录下
- 按日期分类，格式为 `telesubmit_YYYY-MM-DD.log`
- 包含详细的操作记录和错误信息

### 调试命令

机器人所有者可发送 `/debug` 命令查看系统状态，包括：
- 活跃会话数
- 数据库状态
- 内存使用情况
- Python 版本信息

### 查看日志

```bash
# Docker 部署
docker-compose logs -f

# 传统部署
tail -f logs/telesubmit_$(date +%Y-%m-%d).log
```

## 依赖项

- python-telegram-bot >= 21.0
- aiosqlite >= 0.17.0
- configparser >= 6.0.0
- python-dotenv >= 1.0.0
- psutil >= 5.9.0

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT 许可证 - 详见 LICENSE 文件

## 支持

如遇问题：
1. 查看本文档的故障排查部分
2. 查看 [GitHub Issues](https://github.com/zoidberg-xgd/TeleSubmit/issues)
3. 提交新的 Issue

---

**开发者**: [@zoidberg-xgd](https://github.com/zoidberg-xgd)

**项目地址**: https://github.com/zoidberg-xgd/TeleSubmit
