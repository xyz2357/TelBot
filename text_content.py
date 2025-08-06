class TextContent:
    WELCOME = (
        "🎯 Stable Diffusion 远程控制\n"
        "👤 用户: {username}\n"
        "🖥️ SD WebUI: {status}\n\n"
        "请选择要执行的操作:"
    )
    USER_UNAUTHORIZED = "❌ 用户 {username} (ID: {userid}) 未被授权\n请联系管理员添加你的用户ID到授权列表"
    GENERATION_MENU = "🎨 图片生成选项:"
    INPUT_PROMPT = (
        "✏️ 请输入你的提示词 (英文):\n\n"
        "💡 示例:\n"
        "• a beautiful landscape with mountains\n"
        "• cute cat sitting on a chair\n"
        "• anime girl with blue hair\n\n"
        "📐 当前分辨率: {resolution}\n"
        "⚠️ 直接发送文字消息即可，无需命令前缀"
    )
    RESOLUTION_SETTINGS = (
        "📐 分辨率设置\n\n"
        "当前分辨率: {resolution}\n"
        "请选择新的分辨率:"
    )
    RESOLUTION_SET = (
        "✅ 分辨率已设置为: {width}x{height}\n\n"
        "📝 此设置将在你的下次生成中生效"
    )
    RANDOM_PROMPTS = [
        "a serene mountain landscape at sunset",
        "a cute robot in a colorful garden",
        "a magical forest with glowing mushrooms",
        "a cozy coffee shop in the rain",
        "a majestic dragon flying over clouds",
        "a peaceful beach with crystal clear water",
        "a steampunk city with flying machines",
        "a lovely cottage surrounded by flowers"
    ]
    RANDOM_GENERATE = "🎲 随机生成中...\n提示词: {prompt}"
    SD_STATUS_ONLINE = (
        "🟢 Stable Diffusion WebUI 状态\n\n"
        "📡 API: 在线\n"
        "🎯 当前模型: {current_model}\n"
        "📦 可用模型: {model_count}\n"
        "⚙️ 可用采样器: {sampler_count}\n"
        "📊 当前进度: {progress:.1f}%\n"
        "{eta_text}"
    )
    SD_STATUS_OFFLINE = (
        "🔴 Stable Diffusion WebUI 离线\n\n"
        "请确保WebUI已启动并开启API\n"
        "启动命令: --api --listen\n"
        "API地址: {api_url}"
    )
    SD_SETTINGS = (
        "🛠️ 当前设置:\n\n"
        "📐 分辨率: {width}x{height}\n"
        "🔢 步数: {steps}\n"
        "🎚️ CFG Scale: {cfg_scale}\n"
        "🎨 采样器: {sampler_name}\n\n"
        "📝 默认负面提示词:\n{negative_prompt}"
    )
    GENERATION_HISTORY_HEADER = "📈 最近生成历史:\n\n"
    GENERATION_HISTORY_EMPTY = "📈 暂无生成历史"
    PROMPT_UNSAFE = "❌ 提示词不安全: {msg}"
    QUEUE_FULL = "⚠️ 队列已满，请稍后再试"
    GENERATE_SUCCESS = "✅ 生成完成！正在上传图片..."
    GENERATE_FAIL = "❌ 生成失败\n错误: {error}\n💭 {prompt}"
    INTERRUPT_SUCCESS = "⏹️ 任务 {task_id} 已中断"
    INTERRUPT_FAIL = "❌ 无法中断任务 {task_id}"
    NO_LAST_PROMPT = "❌ 没有可用的上一个提示词，请先生成图片。"
    HELP = (
        "🤖 Stable Diffusion 远程控制帮助\n\n"
        "📋 可用命令:\n"
        "/start - 显示主菜单\n"
        "/help - 显示此帮助\n\n"
        "🎨 功能说明:\n"
        "• 文生图 (txt2img)\n"
        "• SD WebUI状态监控\n"
        "• 分辨率自定义设置\n"
        "• 生成队列管理\n"
        "• 生成历史记录\n\n"
        "✏️ 使用方法:\n"
        "1. 发送 /start 打开菜单\n"
        "2. 点击 '分辨率设置' 选择合适的分辨率\n"
        "3. 点击 '生成图片' 选择模式\n"
        "4. 直接发送英文提示词进行生成\n\n"
        "💡 提示词建议:\n"
        "• 使用英文描述\n"
        "• 示例: 'a beautiful sunset over mountains, oil painting style'"
    )
    LIKED_CAPTION_APPEND = "\n\n✅ 已点赞并保存图片！"
    GENERATE_CAPTION = (
        "🎨 生成完成\n"
        "💭 {prompt}\n"
        "📐 {resolution}\n"
    )
    GENERATE_PROGRESS = (
        "⏳ 生成中... (任务ID: {task_id})\n"
        "💭 {prompt}\n"
        "📐 {resolution}"
    )
    STATUS_ONLINE = "🟢 在线"
    STATUS_OFFLINE = "🔴 离线"
    ETA_TEXT = "⏱️ 预计剩余: {eta:.1f}秒\n"