# bot.py
import logging
import uuid
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from security import SecurityManager, require_auth
from sd_controller import StableDiffusionController
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.security = SecurityManager()
        self.sd_controller = StableDiffusionController()
        self.application = None
    
    def create_main_menu(self):
        """创建主菜单键盘"""
        keyboard = [
            [InlineKeyboardButton("🎨 生成图片", callback_data="txt2img")],
            [InlineKeyboardButton("📊 SD状态", callback_data="sd_status")],
            [InlineKeyboardButton("🛠️ SD设置", callback_data="sd_settings")],
            [InlineKeyboardButton("📈 生成历史", callback_data="generation_history")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_generation_menu(self):
        """创建生成选项菜单"""
        keyboard = [
            [InlineKeyboardButton("✏️ 输入提示词", callback_data="input_prompt")],
            [InlineKeyboardButton("🎲 随机生成", callback_data="random_generate")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """开始命令处理"""
        user = update.effective_user
        
        if not self.security.is_authorized_user(user.id):
            await update.message.reply_text(
                f"❌ 用户 {user.username} (ID: {user.id}) 未被授权\n"
                "请联系管理员添加你的用户ID到授权列表"
            )
            return
        
        # 检查SD WebUI状态
        sd_status = await self.sd_controller.check_api_status()
        status_text = "🟢 在线" if sd_status else "🔴 离线"
        
        welcome_text = (
            f"🎯 Stable Diffusion 远程控制\n"
            f"👤 用户: {user.first_name}\n"
            f"🆔 ID: {user.id}\n"
            f"🖥️ SD WebUI: {status_text}\n\n"
            f"请选择要执行的操作:"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.create_main_menu()
        )
    
    @require_auth
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理回调按钮"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "main_menu":
            sd_status = await self.sd_controller.check_api_status()
            status_text = "🟢 在线" if sd_status else "🔴 离线"
            
            await query.edit_message_text(
                f"🎯 Stable Diffusion 远程控制\n🖥️ SD WebUI: {status_text}\n\n请选择操作:",
                reply_markup=self.create_main_menu()
            )
        
        elif data == "txt2img":
            await query.edit_message_text(
                "🎨 图片生成选项:",
                reply_markup=self.create_generation_menu()
            )
        
        elif data == "input_prompt":
            await query.edit_message_text(
                "✏️ 请输入你的提示词 (英文):\n\n"
                "💡 示例:\n"
                "• a beautiful landscape with mountains\n"
                "• cute cat sitting on a chair\n"
                "• anime girl with blue hair\n\n"
                "⚠️ 直接发送文字消息即可，无需命令前缀"
            )
        
        elif data == "random_generate":
            await self.random_generate(query)
        
        elif data == "sd_status":
            await self.show_sd_status(query)
        
        elif data == "sd_settings":
            await self.show_sd_settings(query)
        
        elif data == "generation_history":
            await self.show_generation_history(query)
        
        elif data.startswith("interrupt_"):
            task_id = data.split("_", 1)[1]
            await self.interrupt_generation(query, task_id)
    
    async def random_generate(self, query):
        """随机生成图片"""
        random_prompts = [
            "a serene mountain landscape at sunset",
            "a cute robot in a colorful garden",
            "a magical forest with glowing mushrooms",
            "a cozy coffee shop in the rain",
            "a majestic dragon flying over clouds",
            "a peaceful beach with crystal clear water",
            "a steampunk city with flying machines",
            "a lovely cottage surrounded by flowers"
        ]
        
        import random
        prompt = random.choice(random_prompts)
        
        await query.edit_message_text(f"🎲 随机生成中...\n提示词: {prompt}")
        await self.generate_image_task(query.from_user.id, query.from_user.username, prompt, query.message)
    
    async def show_sd_status(self, query):
        """显示SD WebUI状态"""
        api_status = await self.sd_controller.check_api_status()
        
        if api_status:
            models = await self.sd_controller.get_models()
            samplers = await self.sd_controller.get_samplers()
            progress, eta = await self.sd_controller.get_progress()
            
            status_text = (
                f"🟢 Stable Diffusion WebUI 状态\n\n"
                f"📡 API: 在线\n"
                f"🎯 可用模型: {len(models)}\n"
                f"⚙️ 可用采样器: {len(samplers)}\n"
                f"📊 当前进度: {progress*100:.1f}%\n"
            )
            
            if eta > 0:
                status_text += f"⏱️ 预计剩余: {eta:.1f}秒\n"
        else:
            status_text = (
                f"🔴 Stable Diffusion WebUI 离线\n\n"
                f"请确保WebUI已启动并开启API\n"
                f"启动命令: --api --listen\n"
                f"API地址: {Config.SD_API_URL}"
            )
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]]
        await query.edit_message_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_sd_settings(self, query):
        """显示SD设置信息"""
        settings_text = (
            f"🛠️ 当前设置:\n\n"
            f"📐 分辨率: {Config.SD_DEFAULT_PARAMS['width']}x{Config.SD_DEFAULT_PARAMS['height']}\n"
            f"🔢 步数: {Config.SD_DEFAULT_PARAMS['steps']}\n"
            f"🎚️ CFG Scale: {Config.SD_DEFAULT_PARAMS['cfg_scale']}\n"
            f"🎨 采样器: {Config.SD_DEFAULT_PARAMS['sampler_name']}\n\n"
            f"📝 默认负面提示词:\n{Config.SD_DEFAULT_PARAMS['negative_prompt'][:100]}..."
        )
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]]
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_generation_history(self, query):
        """显示生成历史"""
        history = self.security.generation_history[-5:]  # 最近5条
        if history:
            text = "📈 最近生成历史:\n\n"
            for entry in reversed(history):
                timestamp = datetime.fromtimestamp(entry['timestamp']).strftime("%H:%M:%S")
                status = "✅" if entry['success'] else "❌"
                text += f"{status} {timestamp} - {entry['username']}\n"
                text += f"💭 {entry['prompt']}\n"
                if not entry['success'] and entry.get('error'):
                    text += f"⚠️ {entry['error']}\n"
                text += "\n"
        else:
            text = "📈 暂无生成历史"
        
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @require_auth
    async def handle_text_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本提示词"""
        prompt = update.message.text.strip()
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        if prompt.startswith('/'):
            return  # 忽略命令
        
        # 安全检查
        safe, safety_msg = self.security.is_safe_prompt(prompt)
        if not safe:
            await update.message.reply_text(f"❌ 提示词不安全: {safety_msg}")
            return
        
        # 频率限制检查
        rate_ok, rate_msg = self.security.check_generation_limit(user_id)
        if not rate_ok:
            await update.message.reply_text(f"⚠️ {rate_msg}")
            return
        
        # 队列限制检查
        if self.security.get_queue_size() >= Config.MAX_QUEUE_SIZE:
            await update.message.reply_text(f"⚠️ 队列已满，请稍后再试")
            return
        
        # 开始生成
        await update.message.reply_text(f"🎨 开始生成图片...\n💭 提示词: {prompt}")
        await self.generate_image_task(user_id, username, prompt, update.message)
    
    async def generate_image_task(self, user_id, username, prompt, message):
        """生成图片任务"""
        task_id = str(uuid.uuid4())[:8]
        
        # 添加到安全管理器
        self.security.add_task(task_id, user_id, prompt)
        self.security.add_generation_record(user_id)
        
        # 创建中断按钮
        keyboard = [[InlineKeyboardButton("⏹️ 中断生成", callback_data=f"interrupt_{task_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # 显示生成进度
            progress_msg = await message.reply_text(
                f"⏳ 生成中... (任务ID: {task_id})\n"
                f"💭 {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
                reply_markup=reply_markup
            )
            
            # 调用SD API生成图片
            success, result, info, local_path = await self.sd_controller.generate_image(prompt)
            
            if success:
                # 生成成功，发送图片
                path_info = f"\n💾 本地保存: {local_path}" if local_path else ""
                await progress_msg.edit_text(f"✅ 生成完成！正在上传图片...{path_info}")
                
                # 发送图片
                caption = f"🎨 生成完成\n💭 {prompt}\n🆔 任务ID: {task_id}"
                if local_path:
                    caption += f"\n💾 保存位置: {local_path}"
                
                await message.reply_photo(
                    photo=result,
                    caption=caption
                )
                
                # 清理进度消息
                try:
                    await progress_msg.delete()
                except:
                    pass
                
                # 记录成功日志
                self.security.log_generation(user_id, username, prompt, True)
                self.security.complete_task(task_id, "success")
                
            else:
                # 生成失败
                await progress_msg.edit_text(
                    f"❌ 生成失败\n"
                    f"错误: {result}\n"
                    f"💭 {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                )
                
                # 记录失败日志
                self.security.log_generation(user_id, username, prompt, False, result)
                self.security.complete_task(task_id, f"failed: {result}")
                
        except Exception as e:
            error_msg = f"系统错误: {str(e)}"
            try:
                await progress_msg.edit_text(
                    f"❌ 系统错误\n"
                    f"错误: {error_msg}\n"
                    f"💭 {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
                )
            except:
                await message.reply_text(f"❌ 生成过程中出现错误: {error_msg}")
            
            # 记录错误日志
            self.security.log_generation(user_id, username, prompt, False, error_msg)
            self.security.complete_task(task_id, f"error: {error_msg}")
    
    async def interrupt_generation(self, query, task_id):
        """中断生成任务"""
        success = await self.sd_controller.interrupt_generation()
        
        if success:
            self.security.complete_task(task_id, "interrupted")
            await query.edit_message_text(f"⏹️ 任务 {task_id} 已中断")
        else:
            await query.edit_message_text(f"❌ 无法中断任务 {task_id}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助命令"""
        help_text = (
            "🤖 Stable Diffusion 远程控制帮助\n\n"
            "📋 可用命令:\n"
            "/start - 显示主菜单\n"
            "/help - 显示此帮助\n\n"
            "🎨 功能说明:\n"
            "• 文生图 (txt2img)\n"
            "• SD WebUI状态监控\n"
            "• 生成队列管理\n"
            "• 生成历史记录\n\n"
            "✏️ 使用方法:\n"
            "1. 发送 /start 打开菜单\n"
            "2. 点击 '生成图片' 选择模式\n"
            "3. 直接发送英文提示词进行生成\n\n"
            "💡 提示词建议:\n"
            "• 使用英文描述\n"
            "• 示例: 'a beautiful sunset over mountains, oil painting style'"
        )
        await update.message.reply_text(help_text)
    
    def run(self):
        """运行机器人"""
        if not Config.BOT_TOKEN:
            logger.error("请在 .env 文件中设置 BOT_TOKEN")
            return
        
        if not Config.AUTHORIZED_USERS:
            logger.error("请在 .env 文件中设置 AUTHORIZED_USERS")
            return
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # 添加处理器
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_prompt))
        
        logger.info("Stable Diffusion 控制机器人启动中...")
        logger.info(f"SD WebUI API: {Config.SD_API_URL}")
        self.application.run_polling()