# Stable Diffusion Telegram Bot 🎨

一个功能强大的 Telegram 机器人，用于远程控制 Stable Diffusion WebUI 进行 AI 图像生成。

## ✨ 功能特性

- 🎨 **文生图 (txt2img)** - 通过文本提示词生成高质量图像
- 📐 **自定义分辨率** - 支持多种预设分辨率和自定义设置
- 🎲 **随机生成** - 内置精选提示词库，一键随机生成
- 📊 **实时状态监控** - 监控 SD WebUI 状态、模型、采样器等信息
- 🛠️ **参数设置** - 查看和管理生成参数
- ⏹️ **任务管理** - 支持中断正在进行的生成任务
- 👍 **图片保存** - 点赞功能自动保存喜欢的图片到本地
- 📈 **生成历史** - 查看最近的生成记录
- 🔐 **用户授权** - 支持多用户授权访问控制
- ⚡ **队列管理** - 防止过载的任务队列系统

## 📋 系统要求

- Python 3.8+
- Stable Diffusion WebUI (启用 API 模式)
- Telegram Bot Token

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd stable-diffusion-telegram-bot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例配置文件并编辑：

```bash
cp .env.sample .env
```

编辑 `.env` 文件：

```env
# Telegram Bot Token (从 @BotFather 获取)
BOT_TOKEN="your_bot_token_here"

# 授权用户ID列表 (逗号分隔，从 @userinfobot 获取)
AUTHORIZED_USERS="123456789,987654321"

# Stable Diffusion WebUI API 地址
SD_API_URL=http://127.0.0.1:7860

# API 超时时间 (秒)
SD_API_TIMEOUT=300

# 本地图片保存路径
LOCAL_SAVE_PATH=generated_images
```

### 4. 启动 Stable Diffusion WebUI

确保 SD WebUI 以 API 模式启动：

```bash
# Linux/Mac
./webui.sh --api --listen

# Windows
webui-user.bat --api --listen
```

### 5. 运行机器人

```bash
python main.py
```

## 🔧 配置说明

### Telegram 配置

1. **创建 Telegram Bot**
   - 联系 [@BotFather](https://t.me/BotFather)
   - 发送 `/newbot` 命令
   - 按提示设置机器人名称和用户名
   - 获取 Bot Token

2. **获取用户ID**
   - 联系 [@userinfobot](https://t.me/userinfobot)
   - 发送任意消息获取你的用户ID
   - 将用户ID添加到 `AUTHORIZED_USERS` 中

### Stable Diffusion WebUI 配置

确保 WebUI 启动时包含以下参数：
- `--api` - 启用 API 接口
- `--listen` - 允许外部访问 (如果需要)
- `--port 7860` - 指定端口 (可选)

## 📱 使用方法

### 基本操作

1. **启动机器人**
   ```
   /start
   ```

2. **生成图片**
   - 点击 "🎨 生成图片"
   - 选择 "✏️ 输入提示词" 或 "🎲 随机生成"
   - 直接发送英文提示词

3. **设置分辨率**
   - 点击 "📐 分辨率设置"
   - 选择预设分辨率或自定义

### 支持的分辨率

- 1024x1024 (正方形)
- 1216x832 (横屏)
- 832x1216 (竖屏)
- 1280x720 (宽屏 16:9)
- 720x1280 (竖屏 9:16)

### 提示词建议

- 使用英文描述
- 尽量详细和具体
- 示例：
  ```
  a beautiful landscape with mountains at sunset, oil painting style
  cute cat sitting on a chair, digital art, high quality
  anime girl with blue hair, detailed, masterpiece
  ```

## 🛠️ 高级配置

### 默认生成参数

在 `config.py` 中可以修改默认参数：

```python
SD_DEFAULT_PARAMS = {
    'width': 1024,
    'height': 1024,
    'steps': 20,
    'cfg_scale': 7.0,
    'sampler_name': 'Euler a',
    'negative_prompt': 'lowres, bad anatomy, bad hands, text, error...'
}
```

### 安全设置

- `MAX_PROMPT_LENGTH`: 最大提示词长度 (默认: 500)
- `MAX_QUEUE_SIZE`: 最大并发任务数 (默认: 5)
- 内置不当内容过滤

## 📁 项目结构

```
├── main.py                 # 主程序入口
├── bot.py                  # Telegram Bot 主逻辑
├── config.py               # 配置管理
├── sd_controller.py        # SD WebUI API 控制器
├── security.py             # 安全和权限管理
├── keyboards.py            # Telegram 键盘定义
├── text_content.py         # 文本内容定义
├── user_manager.py         # 用户设置管理
├── view_manager.py         # 视图管理 (备用)
├── utils.py                # 工具函数
├── requirements.txt        # 依赖列表
├── .env.sample            # 环境变量示例
├── .gitignore             # Git 忽略文件
└── generated_images/       # 生成的图片保存目录
```

## 🔍 故障排除

### 常见问题

1. **机器人无响应**
   - 检查 Bot Token 是否正确
   - 确认用户ID已添加到授权列表
   - 查看终端错误日志

2. **SD WebUI 连接失败**
   - 确认 WebUI 已启动且启用 API
   - 检查 API 地址和端口配置
   - 确认防火墙设置

3. **图片生成失败**
   - 检查提示词是否包含不支持的内容
   - 确认 WebUI 有可用的模型
   - 查看 WebUI 终端的错误信息

### 日志查看

机器人会在终端输出详细的运行日志，包括：
- API 连接状态
- 用户操作记录
- 错误信息和调试信息

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

### 开发指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## ⚠️ 免责声明

- 本工具仅供学习和个人使用
- 请遵守当地法律法规和平台使用条款
- 生成的图片内容由用户负责
- 作者不对使用本工具产生的任何后果负责

## 📞 支持

如果你遇到问题或有建议，请：

1. 查看本 README 的故障排除部分
2. 在 GitHub Issues 中搜索类似问题
3. 创建新的 Issue 并提供详细信息

## 🙏 致谢

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API 封装
- [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) - AI 图像生成界面
- [Pillow](https://pillow.readthedocs.io/) - Python 图像处理库