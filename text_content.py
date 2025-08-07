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
    
    # 负面词相关文本
    NEGATIVE_PROMPT_SETTINGS = (
        "🚫 负面词设置\n\n"
        "当前负面词:\n"
        "📝 {negative_prompt}\n\n"
        "负面词用于告诉AI避免生成的内容，可以提高图片质量。"
    )
    INPUT_NEGATIVE_PROMPT = (
        "🚫 请输入自定义负面词 (英文):\n\n"
        "💡 常用负面词示例:\n"
        "• lowres, bad anatomy, bad hands\n"
        "• text, watermark, signature\n"
        "• worst quality, low quality\n"
        "• blurry, cropped, jpeg artifacts\n\n"
        "⚠️ 多个负面词请用逗号分隔\n"
        "📝 直接发送文字消息即可\n"
        "❌ 或点击下方按钮取消输入"
    )
    NEGATIVE_PROMPT_INPUT_CANCELLED = (
        "❌ 已取消负面词输入\n\n"
        "返回负面词设置页面："
    )
    NEGATIVE_PROMPT_SET = (
        "✅ 负面词已更新！\n\n"
        "📝 新的负面词:\n{negative_prompt}\n\n"
        "🎯 此设置将在你的下次生成中生效"
    )
    NEGATIVE_PROMPT_RESET = (
        "🔄 负面词已重置为默认设置！\n\n"
        "📝 默认负面词:\n{negative_prompt}"
    )
    NEGATIVE_PROMPT_TOO_LONG = "❌ 负面词过长，请控制在1000字符以内"
    
    # 新增表单相关文本
    ADVANCED_FORM_TITLE = (
        "📝 高级生成表单\n\n"
        "您可以设置详细的生成参数，未设置的项目将使用默认值："
    )
    
    FORM_INPUT_PROMPT = (
        "✏️ 请输入正面词 (提示词):\n\n"
        "💡 描述您想要生成的图像内容\n"
        "📝 使用英文，可以留空使用随机提示词\n\n"
        "示例:\n"
        "• a beautiful anime girl with long hair\n"
        "• mountain landscape at sunset\n"
        "• cute robot in a garden\n\n"
        "⚠️ 直接发送文字消息，或发送 'skip' 跳过此项"
    )
    
    FORM_INPUT_SEED = (
        "🎲 请输入图像种子 (Seed):\n\n"
        "💡 种子用于控制随机性，相同种子会生成相似图像\n"
        "📝 输入数字 (如: 123456789) 或发送 'random' 使用随机种子\n"
        "🔢 种子范围: 0 到 4294967295\n\n"
        "⚠️ 直接发送数字或 'random'，或发送 'skip' 跳过此项"
    )
    
    FORM_RESOLUTION_MENU = (
        "📐 请选择分辨率:\n\n"
        "当前选择: {current_resolution}\n"
        "不同分辨率适用于不同场景，请根据需要选择："
    )
    
    FORM_PROMPT_SET = "✅ 正面词已设置: {prompt}"
    FORM_PROMPT_SKIPPED = "⏭️ 正面词已跳过，将使用随机提示词"
    FORM_SEED_SET = "✅ 种子已设置: {seed}"
    FORM_SEED_RANDOM = "🎲 种子已设置为随机"
    FORM_SEED_SKIPPED = "⏭️ 种子已跳过，将使用随机种子"
    FORM_SEED_INVALID = "❌ 种子格式错误，请输入数字、'random' 或 'skip'"
    FORM_RESOLUTION_SET = "✅ 分辨率已设置: {resolution}"
    FORM_HIRES_ENABLED = "✅ 高清分辨修复已开启"
    FORM_HIRES_DISABLED = "❌ 高清分辨修复已关闭"
    FORM_RESET_SUCCESS = "🔄 表单已重置"
    FORM_INPUT_CANCELLED = "❌ 输入已取消"
    
    FORM_GENERATE_MISSING_PROMPT = (
        "⚠️ 未设置正面词，将使用随机提示词生成\n\n"
        "点击 '🚀 生成图片' 确认，或先设置正面词"
    )
    
    FORM_SUMMARY = (
        "📋 当前表单设置:\n\n"
        "✏️ 正面词: {prompt}\n"
        "📐 分辨率: {resolution}\n"
        "🎲 种子: {seed}\n"
        "🔍 高清修复: {hires_fix}\n\n"
        "请选择操作："
    )
    
    # 原有文本保持不变
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
        "📝 当前负面词:\n{negative_prompt}"
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
        "• 负面词自定义设置\n"
        "• 高级表单生成 (新增)\n"
        "• 生成队列管理\n"
        "• 生成历史记录\n\n"
        "✏️ 使用方法:\n"
        "1. 发送 /start 打开菜单\n"
        "2. 点击 '分辨率设置' 选择合适的分辨率\n"
        "3. 点击 '负面词设置' 自定义负面词\n"
        "4. 点击 '生成图片' 选择模式\n"
        "5. 选择 '高级表单' 进行详细设置\n"
        "6. 直接发送英文提示词进行快速生成\n\n"
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