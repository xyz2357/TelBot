import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from security import SecurityManager, require_auth
from sd_controller import StableDiffusionController
from config import Config, UserSettings
from keyboards import Keyboards, CallbackData
from user_manager import UserManager
from view_manager import ViewManager
from utils import safe_call
from text_content import TextContent


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class TelegramBot:
    application: Optional[Application]
    last_prompt: Optional[str]
    user_last_photo_msg: Dict[str, int] 
    security: SecurityManager
    sd_controller: StableDiffusionController
    user_manager: UserManager

    def __init__(self) -> None:
        self.security = SecurityManager()
        self.sd_controller = StableDiffusionController()
        self.user_manager = UserManager(Config.SD_DEFAULT_PARAMS)
        self.application = None
        self.last_prompt = None
        self.user_last_photo_msg = {}

    # 下面的代码只做流程分发，具体逻辑交给 manager/controller
    def create_main_menu(self) -> InlineKeyboardMarkup:
        return Keyboards.main_menu()

    def create_generation_menu(self) -> InlineKeyboardMarkup:
        return Keyboards.generation_menu()

    def create_resolution_menu(self, user_id: str) -> InlineKeyboardMarkup:
        current_settings = self.user_manager.get_settings(user_id)
        current_res = f"{current_settings['width']}x{current_settings['height']}"
        return Keyboards.resolution_menu(current_res)

    def get_user_settings(self, user_id: str) -> UserSettings:
        return self.user_manager.get_settings(user_id)

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """开始命令处理"""
        user = update.effective_user
        user_id: str = str(user.id)
        if not self.security.is_authorized_user(user_id):
            await update.message.reply_text(
                TextContent.USER_UNAUTHORIZED.format(username=user.username, userid=user.id)
            )
            return
        sd_status = await self.sd_controller.check_api_status()
        status_text = TextContent.STATUS_ONLINE if sd_status else TextContent.STATUS_OFFLINE
        welcome_text = TextContent.WELCOME.format(username=user.first_name, status=status_text)
        await update.message.reply_text(
            welcome_text,
            reply_markup=Keyboards.main_menu()
        )

    @require_auth
    async def handle_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """处理回调按钮"""
        query: CallbackQuery = update.callback_query
        user_id: str = str(query.from_user.id)
        await query.answer()
        
        data: CallbackData = query.data

        if data.startswith(CallbackData.LIKE.value.split("{")[0]):
            # like_{task_id}
            task_id = data.split("_", 1)[1]
            await self.sd_controller.save_last_result_locally()
            self.security.complete_task(task_id, "liked")
            old_caption = query.message.caption or ""
            new_caption = old_caption + TextContent.LIKED_CAPTION_APPEND
            await query.edit_message_caption(new_caption, reply_markup=None)
        elif data == CallbackData.MAIN_MENU.value:
            # main_menu
            sd_status = await self.sd_controller.check_api_status()
            status_text = TextContent.STATUS_ONLINE if sd_status else TextContent.STATUS_OFFLINE
            await query.edit_message_text(
                TextContent.WELCOME.format(username=query.from_user.first_name, status=status_text),
                reply_markup=Keyboards.main_menu()
            )
        elif data == CallbackData.TXT2IMG.value:
            # txt2img
            await query.edit_message_text(
                TextContent.GENERATION_MENU,
                reply_markup=Keyboards.generation_menu()
            )
        elif data == CallbackData.INPUT_PROMPT.value:
            # input_prompt
            user_settings = self.get_user_settings(user_id)
            await query.edit_message_text(
                TextContent.INPUT_PROMPT.format(
                    resolution=f"{user_settings['width']}x{user_settings['height']}"
                )
            )
        elif data == CallbackData.RANDOM_GENERATE.value:
            # random_generate
            await self.random_generate(query)
        elif data == CallbackData.SD_STATUS.value:
            # sd_status
            await self.show_sd_status(query)
        elif data == CallbackData.SD_SETTINGS.value:
            # sd_settings
            await self.show_sd_settings(query)
        elif data == CallbackData.GENERATION_HISTORY.value:
            # generation_history
            await self.show_generation_history(query)
        elif data == CallbackData.RESOLUTION_SETTINGS.value:
            # resolution_settings
            await self.show_resolution_settings(query, user_id)
        elif data.startswith(CallbackData.SET_RESOLUTION.value.split("{")[0]):  # "set_resolution_"
            # set_resolution_{res}
            await self.set_resolution(query, data, user_id)
        elif data.startswith(CallbackData.INTERRUPT.value.split("{")[0]):  # "interrupt_"
            # interrupt_{task_id}
            task_id = data.split("_", 1)[1]
            await self.interrupt_generation(query, task_id)

    async def show_resolution_settings(self, query: CallbackQuery, user_id: str) -> None:
        """显示分辨率设置菜单"""
        user_settings = self.get_user_settings(user_id)
        current_res = f"{user_settings['width']}x{user_settings['height']}"
        text = TextContent.RESOLUTION_SETTINGS.format(resolution=current_res)
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.resolution_menu(current_res)
        )

    async def set_resolution(self, query: CallbackQuery, callback_data: str, user_id: str) -> None:
        """设置用户分辨率"""
        parts = callback_data.split("_")
        width = int(parts[2])
        height = int(parts[3])
        user_settings = self.get_user_settings(user_id)
        user_settings['width'] = width
        user_settings['height'] = height
        await query.edit_message_text(
            TextContent.RESOLUTION_SET.format(width=width, height=height),
            reply_markup=Keyboards.resolution_menu(f"{width}x{height}")
        )

    async def random_generate(self, query: CallbackQuery) -> None:
        """随机生成图片"""
        import random
        prompt: str = random.choice(TextContent.RANDOM_PROMPTS)
        await query.edit_message_text(TextContent.RANDOM_GENERATE.format(prompt=prompt))
        user_id: str = str(query.from_user.id)
        username: str = query.from_user.username or query.from_user.first_name
        await self.generate_image_task(user_id, username, prompt, query.message)

    async def show_sd_status(self, query: CallbackQuery) -> None:
        """显示SD WebUI状态"""
        api_status: bool = await self.sd_controller.check_api_status()
        
        if api_status:
            models = await self.sd_controller.get_models()
            samplers = await self.sd_controller.get_samplers()
            progress, eta = await self.sd_controller.get_progress()
            current_model = await self.sd_controller.get_current_model()
            eta_text = TextContent.ETA_TEXT.format(eta=eta) if eta > 0 else ""
            status_text = TextContent.SD_STATUS_ONLINE.format(
                current_model=current_model,
                model_count=len(models),
                sampler_count=len(samplers),
                progress=progress*100,
                eta_text=eta_text
            )
        else:
            status_text = TextContent.SD_STATUS_OFFLINE.format(api_url=Config.SD_API_URL)
        
        keyboard = Keyboards.main_menu()
        await query.edit_message_text(
            status_text,
            reply_markup=keyboard
        )
    
    async def show_sd_settings(self, query: CallbackQuery) -> None:
        """显示SD设置信息"""
        user_id: str = str(query.from_user.id)
        user_settings = self.get_user_settings(user_id)
        
        settings_text = TextContent.SD_SETTINGS.format(
            width=user_settings['width'],
            height=user_settings['height'],
            steps=user_settings['steps'],
            cfg_scale=user_settings['cfg_scale'],
            sampler_name=user_settings['sampler_name'],
            negative_prompt=user_settings['negative_prompt'][:100] + "..."
        )
        
        keyboard = Keyboards.main_menu()
        await query.edit_message_text(
            settings_text,
            reply_markup=keyboard
        )
    
    async def show_generation_history(self, query: CallbackQuery) -> None:
        """显示生成历史"""
        history = self.security.generation_history[-5:]  # 最近5条
        if history:
            text = TextContent.GENERATION_HISTORY_HEADER
            for entry in reversed(history):
                timestamp = datetime.fromtimestamp(entry['timestamp']).strftime("%H:%M:%S")
                status = "✅" if entry['success'] else "❌"
                text += f"{status} {timestamp} - {entry['username']}\n"
                text += f"💭 {entry['prompt']}\n"
                if not entry['success'] and entry.get('error'):
                    text += f"⚠️ {entry['error']}\n"
                text += "\n"
        else:
            text = TextContent.GENERATION_HISTORY_EMPTY
        
        keyboard = Keyboards.main_menu()
        await query.edit_message_text(
            text,
            reply_markup=keyboard
        )
    
    @safe_call
    @require_auth
    async def handle_text_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理文本提示词"""
    
        prompt: str = update.message.text.strip()
        user_id: str = str(update.effective_user.id)
        username: str = update.effective_user.username or update.effective_user.first_name
        
        # 清理上次生成消息的按钮
        last_msg_id = self.user_last_photo_msg.get(user_id)
        if last_msg_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=update.message.chat_id,
                    message_id=last_msg_id,
                    reply_markup=None
                )
            except Exception:
                pass  # 忽略可能的错误

        if prompt.startswith('/'):
            return  # 忽略命令
        
        # 安全检查
        safe, safety_msg = self.security.is_safe_prompt(prompt)
        if not safe:
            await update.message.reply_text(TextContent.PROMPT_UNSAFE.format(msg=safety_msg))
            return
        
        limit, limit_msg = self.security.check_generation_limit(user_id)
        if not limit:
            await update.message.reply_text(limit_msg + "\n\n")
            return
        
        # 队列限制检查
        if self.security.get_queue_size() >= Config.MAX_QUEUE_SIZE:
            await update.message.reply_text(TextContent.QUEUE_FULL)
            return

        # 开始生成
        await self.generate_image_task(user_id, username, prompt, update.message)
    
    @safe_call
    async def generate_image_task(self, user_id: str, username: str, prompt: str, message: Message) -> None:
        """生成图片任务"""
        task_id = str(uuid.uuid4())[:8]
        self.last_prompt = prompt  # 保存最后的提示词
        
        # 获取用户自定义设置
        user_settings = self.get_user_settings(user_id)
        
        # 添加到安全管理器
        self.security.add_task(task_id, user_id, prompt)
        self.security.add_generation_record(user_id)
        
        # 创建中断按钮
        keyboard = Keyboards.interrupt_keyboard(task_id)
        reply_markup = keyboard
        
        # 显示生成进度
        progress_msg = await message.reply_text(
            TextContent.GENERATE_PROGRESS.format(
                task_id=task_id,
                prompt=prompt[:50] + ('...' if len(prompt) > 50 else ''),
                resolution=f"{user_settings['width']}x{user_settings['height']}"
            ),
            reply_markup=reply_markup
        )
        
        # 调用SD API生成图片，使用用户设置
        success, result = await self.sd_controller.generate_image(
            prompt, 
            **user_settings  # 使用用户自定义设置
        )
        
        if success:
            reply_markup = Keyboards.like_keyboard(task_id)
            await progress_msg.edit_text(TextContent.GENERATE_SUCCESS)
            caption = TextContent.GENERATE_CAPTION.format(
                prompt=prompt,
                resolution=f"{user_settings['width']}x{user_settings['height']}"
            )
            sent_msg = await message.reply_photo(
                photo=result,
                caption=caption,
                reply_markup=reply_markup
            )
            
            self.user_last_photo_msg[user_id] = sent_msg.message_id

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
            await progress_msg.edit_text(TextContent.GENERATE_FAIL.format(error=result, prompt=prompt[:50]))
            
            # 记录失败日志
            self.security.log_generation(user_id, username, prompt, False, result)
            self.security.complete_task(task_id, f"failed: {result}")
    
    @require_auth
    async def regenerate_image_with_last_prompt_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """重新生成上一个提示词的图片"""
        prompt = self.last_prompt
        user_id: str = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name
        if self.last_prompt is not None:
            await self.generate_image_task(user_id, username, self.last_prompt, update.message)
        else:
            await update.message.reply_text(TextContent.NO_LAST_PROMPT)
    
    async def interrupt_generation(self, query: CallbackQuery, task_id: str) -> None:
        """中断生成任务"""
        success = await self.sd_controller.interrupt_generation()
        
        if success:
            self.security.complete_task(task_id, "interrupted")
            await query.edit_message_text(TextContent.INTERRUPT_SUCCESS.format(task_id=task_id))
        else:
            await query.edit_message_text(TextContent.INTERRUPT_FAIL.format(task_id=task_id))
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """帮助命令"""
        await update.message.reply_text(TextContent.HELP)
    
    def run(self) -> None:
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
        self.application.add_handler(CommandHandler("re", self.regenerate_image_with_last_prompt_task))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_prompt))
        
        logger.info("Stable Diffusion 控制机器人启动中...")
        logger.info(f"SD WebUI API: {Config.SD_API_URL}")
        self.application.run_polling()