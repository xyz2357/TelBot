import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Deque, Tuple, Set, TypedDict, cast
import io
from collections import deque
from telegram import Update, InlineKeyboardMarkup, Message, CallbackQuery
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from security import SecurityManager, require_auth
from sd_controller import StableDiffusionController
from config import Config, UserSettings
from keyboards import Keyboards, CallbackData
from user_manager import UserManager
from form_manager import FormManager
from utils import safe_call
from text_content import TextContent
import asyncio
import json
import os


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def _str_or_empty(v: Any) -> str:
    return v if isinstance(v, str) else ""

class SnapshotParams(TypedDict, total=False):
    negative_prompt: str
    seed: int
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler_name: str

class TaskSnapshot(TypedDict):
    prompt: str
    params: SnapshotParams

class TelegramBot:
    application: Optional[Application]  # type: ignore[type-arg]
    last_prompt: Optional[str]
    user_last_photo_msg: Dict[str, int]
    security: SecurityManager
    sd_controller: StableDiffusionController
    user_manager: UserManager
    form_manager: FormManager

    def __init__(self) -> None:
        self.security = SecurityManager()
        self.sd_controller = StableDiffusionController()
        self.user_manager = UserManager(Config.SD_DEFAULT_PARAMS)
        self.form_manager = FormManager()
        self.application = None
        self.last_prompt = None
        self.user_last_photo_msg = {}
        # 记录任务ID与对应结果，供点赞保存使用，避免并发串任务
        self.task_results: Dict[str, Dict[str, Any]] = {}
        # 记录任务ID与生成参数（用于高清化复用原图参数）
        self.task_params: Dict[str, Dict[str, Any]] = {}
        # 每个任务的完整快照，便于复用与溯源
        self.task_snapshots: Dict[str, TaskSnapshot] = {}
        # 每个用户最近包含点赞按钮的图片消息 (最多10条)
        self.user_recent_photo_msgs: Dict[str, Deque[Tuple[int, int]]] = {}

        # 在启动时加载快照缓存
        self._snapshot_cache_file = os.path.join(Config.DATA_DIR, 'snapshots.json')
        try:
            if os.path.exists(self._snapshot_cache_file):
                with open(self._snapshot_cache_file, 'r', encoding='utf-8') as f:
                    raw = cast(Dict[str, Any], json.load(f))
                    # 运行时校验结构
                    snapshots: Dict[str, TaskSnapshot] = {}
                    items: list[tuple[str, Any]] = list(raw.items())[-Config.SNAPSHOT_CACHE_LIMIT:]
                    for k, v in items:
                        if isinstance(v, dict) and 'prompt' in v and 'params' in v and isinstance(v['params'], dict):
                            snapshots[str(k)] = cast(TaskSnapshot, v)
                    self.task_snapshots = snapshots
        except Exception:
            pass
        self.waiting_for_negative_prompt: Set[str] = set()

    # 下面的代码只做流程分发，具体逻辑交给 manager/controller
    def create_main_menu(self) -> InlineKeyboardMarkup:
        return Keyboards.main_menu()

    def create_generation_menu(self) -> InlineKeyboardMarkup:
        return Keyboards.generation_menu()

    def create_resolution_menu(self, user_id: str) -> InlineKeyboardMarkup:
        current_settings: UserSettings = self.user_manager.get_settings(user_id)
        current_res = f"{current_settings['width']}x{current_settings['height']}"
        return Keyboards.resolution_menu(current_res)

    def get_user_settings(self, user_id: str) -> UserSettings:
        return self.user_manager.get_settings(user_id)

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """开始命令处理"""
        if update.effective_user is None or update.message is None:
            return
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
        query = update.callback_query
        if query is None:
            return
        user_id: str = str(query.from_user.id)
        await query.answer()
        
        data_opt = query.data
        if data_opt is None:
            return
        data: str = data_opt

        if data.startswith(CallbackData.LIKE.value.split("{")[0]):
            # like_{task_id}
            task_id = data.split("_", 1)[1]
            result = self.task_results.get(task_id)
            if result:
                await self.sd_controller.save_result_locally(result)
            self.security.complete_task(task_id, "liked")
            if query.message is not None:
                base = _str_or_empty(query.message.caption) or _str_or_empty(query.message.text)
                new_text = f"{base}{TextContent.LIKED_CAPTION_APPEND}"
                has_media = bool(getattr(query.message, "photo", None) or
                                getattr(query.message, "video", None) or
                                getattr(query.message, "document", None))

                try:
                    if has_media or isinstance(query.message.caption, str):
                        await query.edit_message_caption(new_text, reply_markup=None)
                    else:
                        await query.edit_message_text(new_text, reply_markup=None)
                except Exception:
                    pass
        elif data.startswith(CallbackData.ENHANCE_HR.value.split("{")[0]):
            # enhance_hr_{task_id}
            task_id = data.split("_", 2)[2]
            await self.enhance_image_hr(query, user_id, task_id)
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
            user_settings: UserSettings = self.get_user_settings(user_id)
            await query.edit_message_text(
                TextContent.INPUT_PROMPT.format(
                    resolution=f"{user_settings['width']}x{user_settings['height']}"
                )
            )
        elif data == CallbackData.RANDOM_GENERATE.value:
            # random_generate
            await self.random_generate(query)
        elif data == CallbackData.ADVANCED_FORM.value:
            # advanced_form - 新增表单功能
            await self.show_advanced_form(query, user_id)
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
        elif data == CallbackData.NEGATIVE_PROMPT_SETTINGS.value:
            # negative_prompt_settings
            await self.show_negative_prompt_settings(query, user_id)
        elif data == CallbackData.SET_NEGATIVE_PROMPT.value:
            # set_negative_prompt
            await self.request_negative_prompt_input(query, user_id)
        elif data == CallbackData.RESET_NEGATIVE_PROMPT.value:
            # reset_negative_prompt
            await self.reset_negative_prompt(query, user_id)
        elif data == CallbackData.CANCEL_NEGATIVE_PROMPT.value:
            # cancel_negative_prompt
            await self.cancel_negative_prompt_input(query, user_id)
        # 新增表单相关回调处理
        elif data == CallbackData.FORM_SET_PROMPT.value:
            # form_set_prompt
            await self.request_form_prompt_input(query, user_id)
        elif data == CallbackData.FORM_SET_RESOLUTION_MENU.value:
            # form_set_resolution_menu
            await self.show_form_resolution_menu(query, user_id)
        elif data.startswith(CallbackData.FORM_SET_RESOLUTION.value.split("{")[0]):
            # form_set_resolution_{res}
            await self.set_form_resolution(query, data, user_id)
        elif data == CallbackData.FORM_SET_SEED.value:
            # form_set_seed
            await self.request_form_seed_input(query, user_id)
        elif data == CallbackData.FORM_TOGGLE_HIRES.value:
            # form_toggle_hires
            await self.toggle_form_hires(query, user_id)
        elif data == CallbackData.FORM_GENERATE.value:
            # form_generate
            await self.generate_from_form(query, user_id)
        elif data == CallbackData.FORM_RESET.value:
            # form_reset
            await self.reset_form(query, user_id)
        elif data == CallbackData.FORM_CANCEL_INPUT.value:
            # form_cancel_input
            await self.cancel_form_input(query, user_id)

    # 原有方法保持不变
    async def show_resolution_settings(self, query: CallbackQuery, user_id: str) -> None:
        """显示分辨率设置菜单"""
        user_settings: UserSettings = self.get_user_settings(user_id)
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
        user_settings: UserSettings = self.get_user_settings(user_id)
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
        user_settings: UserSettings = self.get_user_settings(user_id)
        
        settings_text = TextContent.SD_SETTINGS.format(
            width=user_settings['width'],
            height=user_settings['height'],
            steps=user_settings['steps'],
            cfg_scale=user_settings['cfg_scale'],
            sampler_name=user_settings['sampler_name'],
            negative_prompt=user_settings['negative_prompt'][:100] + "..."
        )
        
        keyboard = Keyboards.sd_setting_menu()
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
    
    async def show_negative_prompt_settings(self, query: CallbackQuery, user_id: str) -> None:
        """显示负面词设置菜单"""
        user_settings: UserSettings = self.get_user_settings(user_id)
        current_negative_prompt = user_settings['negative_prompt']
        
        # 截断显示长负面词
        display_negative_prompt = current_negative_prompt
        if len(display_negative_prompt) > 200:
            display_negative_prompt = display_negative_prompt[:200] + "..."
        
        text = TextContent.NEGATIVE_PROMPT_SETTINGS.format(
            negative_prompt=display_negative_prompt
        )
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.negative_prompt_menu()
        )

    async def request_negative_prompt_input(self, query: CallbackQuery, user_id: str) -> None:
        """请求用户输入自定义负面词"""
        self.waiting_for_negative_prompt.add(user_id)
        await query.edit_message_text(
            TextContent.INPUT_NEGATIVE_PROMPT,
            reply_markup=Keyboards.negative_prompt_input_menu()
        )

    async def reset_negative_prompt(self, query: CallbackQuery, user_id: str) -> None:
        """重置用户负面词为默认值"""
        self.user_manager.reset_negative_prompt(user_id)
        default_negative_prompt = Config.SD_DEFAULT_PARAMS['negative_prompt']
        
        # 截断显示
        display_negative_prompt = default_negative_prompt
        if len(display_negative_prompt) > 200:
            display_negative_prompt = display_negative_prompt[:200] + "..."
            
        await query.edit_message_text(
            TextContent.NEGATIVE_PROMPT_RESET.format(
                negative_prompt=display_negative_prompt
            ),
            reply_markup=Keyboards.negative_prompt_menu()
        )

    async def handle_negative_prompt_input(self, update: Update, user_id: str, negative_prompt: str) -> None:
        """处理用户输入的负面词"""
        self.waiting_for_negative_prompt.discard(user_id)  # 移除等待状态
        
        # 验证负面词长度
        if len(negative_prompt) > 1000:
            if update.message is not None:
                await update.message.reply_text(TextContent.NEGATIVE_PROMPT_TOO_LONG)
            return
        
        # 保存负面词
        self.user_manager.set_negative_prompt(user_id, negative_prompt)
        
        # 截断显示
        display_negative_prompt = negative_prompt
        if len(display_negative_prompt) > 200:
            display_negative_prompt = display_negative_prompt[:200] + "..."
        
        if update.message is not None:
            await update.message.reply_text(
                TextContent.NEGATIVE_PROMPT_SET.format(negative_prompt=display_negative_prompt),
                reply_markup=Keyboards.negative_prompt_menu()
            )

    async def cancel_negative_prompt_input(self, query: CallbackQuery, user_id: str) -> None:
        """取消负面词输入"""
        self.waiting_for_negative_prompt.discard(user_id)  # 移除等待状态
        
        # 获取当前负面词设置并显示设置页面
        user_settings: UserSettings = self.get_user_settings(user_id)
        current_negative_prompt = user_settings['negative_prompt']
        
        # 截断显示长负面词
        display_negative_prompt = current_negative_prompt
        if len(display_negative_prompt) > 200:
            display_negative_prompt = display_negative_prompt[:200] + "..."
        
        cancel_text = TextContent.NEGATIVE_PROMPT_INPUT_CANCELLED + "\n\n" + TextContent.NEGATIVE_PROMPT_SETTINGS.format(
            negative_prompt=display_negative_prompt
        )
        
        await query.edit_message_text(
            cancel_text,
            reply_markup=Keyboards.negative_prompt_menu()
        )

    # 新增表单相关方法
    async def show_advanced_form(self, query: CallbackQuery, user_id: str) -> None:
        """显示高级表单"""
        form_data = self.form_manager.get_user_form(user_id)
        summary = self.form_manager.format_form_summary(user_id)
        
        text = TextContent.ADVANCED_FORM_TITLE + "\n\n" + TextContent.FORM_SUMMARY.format(**summary)
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.advanced_form_menu(cast(Dict[str, object], form_data))
        )

    async def request_form_prompt_input(self, query: CallbackQuery, user_id: str) -> None:
        """请求表单正面词输入"""
        self.form_manager.set_input_state(user_id, "prompt")
        await query.edit_message_text(
            TextContent.FORM_INPUT_PROMPT,
            reply_markup=Keyboards.form_input_cancel_menu()
        )

    async def show_form_resolution_menu(self, query: CallbackQuery, user_id: str) -> None:
        """显示表单分辨率选择菜单"""
        form_data = self.form_manager.get_user_form(user_id)
        current_res_val: str = (form_data.get('resolution') or "")
        
        text = TextContent.FORM_RESOLUTION_MENU.format(current_resolution=current_res_val or "未设置")
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.form_resolution_menu(current_res_val)
        )

    async def set_form_resolution(self, query: CallbackQuery, callback_data: str, user_id: str) -> None:
        """设置表单分辨率"""
        # 解析 form_set_resolution_1024_1024 格式
        parts = callback_data.split("_")
        width = int(parts[3])
        height = int(parts[4])
        resolution = f"{width}x{height}"
        
        self.form_manager.update_form_field(user_id, 'resolution', resolution)
        
        await query.edit_message_text(
            TextContent.FORM_RESOLUTION_SET.format(resolution=resolution),
            reply_markup=Keyboards.form_resolution_menu(resolution)
        )

    async def request_form_seed_input(self, query: CallbackQuery, user_id: str) -> None:
        """请求表单种子输入"""
        self.form_manager.set_input_state(user_id, "seed")
        await query.edit_message_text(
            TextContent.FORM_INPUT_SEED,
            reply_markup=Keyboards.form_input_cancel_menu()
        )

    async def toggle_form_hires(self, query: CallbackQuery, user_id: str) -> None:
        """切换表单高清修复选项"""
        form_data = self.form_manager.get_user_form(user_id)
        current_hires = form_data.get('hires_fix', False)
        new_hires = not current_hires
        
        self.form_manager.update_form_field(user_id, 'hires_fix', new_hires)
        
        message = TextContent.FORM_HIRES_ENABLED if new_hires else TextContent.FORM_HIRES_DISABLED
        
        # 更新表单显示
        summary = self.form_manager.format_form_summary(user_id)
        text = message + "\n\n" + TextContent.FORM_SUMMARY.format(**summary)
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.advanced_form_menu(cast(Dict[str, object], form_data))
        )

    async def generate_from_form(self, query: CallbackQuery, user_id: str) -> None:
        """从表单生成图片"""
        username = query.from_user.username or query.from_user.first_name
        
        # 获取提示词
        prompt = self.form_manager.get_prompt_from_form(user_id, TextContent.RANDOM_PROMPTS)
        
        await query.edit_message_text(
            f"🚀 正在使用表单设置生成图片...\n💭 {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        )
        
        # 生成图片，传递表单数据标识
        await self.generate_image_task(user_id, username, prompt, query.message, from_form=True)

    async def reset_form(self, query: CallbackQuery, user_id: str) -> None:
        """重置表单"""
        self.form_manager.reset_user_form(user_id)
        
        form_data = self.form_manager.get_user_form(user_id)
        summary = self.form_manager.format_form_summary(user_id)
        
        text = TextContent.FORM_RESET_SUCCESS + "\n\n" + TextContent.FORM_SUMMARY.format(**summary)
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.advanced_form_menu(cast(Dict[str, object], form_data))
        )

    async def cancel_form_input(self, query: CallbackQuery, user_id: str) -> None:
        """取消表单输入"""
        self.form_manager.clear_input_state(user_id)
        
        # 返回表单页面
        form_data = self.form_manager.get_user_form(user_id)
        summary = self.form_manager.format_form_summary(user_id)
        
        text = TextContent.FORM_INPUT_CANCELLED + "\n\n" + TextContent.FORM_SUMMARY.format(**summary)
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.advanced_form_menu(cast(Dict[str, object], form_data))
        )

    async def handle_form_input(self, update: Update, user_id: str, input_text: str) -> None:
        """处理表单输入"""
        input_state = self.form_manager.get_input_state(user_id)
        
        if input_state == "prompt":
            await self.handle_form_prompt_input(update, user_id, input_text)
        elif input_state == "seed":
            await self.handle_form_seed_input(update, user_id, input_text)

    async def handle_form_prompt_input(self, update: Update, user_id: str, prompt: str) -> None:
        """处理表单正面词输入"""
        self.form_manager.clear_input_state(user_id)
        
        if prompt.lower().strip() == 'skip':
            self.form_manager.update_form_field(user_id, 'prompt', None)
            message = TextContent.FORM_PROMPT_SKIPPED
        else:
            self.form_manager.update_form_field(user_id, 'prompt', prompt)
            display_prompt = prompt[:50] + '...' if len(prompt) > 50 else prompt
            message = TextContent.FORM_PROMPT_SET.format(prompt=display_prompt)
        
        # 返回表单页面
        form_data = self.form_manager.get_user_form(user_id)
        summary = self.form_manager.format_form_summary(user_id)
        text = message + "\n\n" + TextContent.FORM_SUMMARY.format(**summary)
        
        if update.message is None:
            return
        assert update.message is not None
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.advanced_form_menu(cast(Dict[str, object], form_data))
        )

    async def handle_form_seed_input(self, update: Update, user_id: str, seed_text: str) -> None:
        """处理表单种子输入"""
        self.form_manager.clear_input_state(user_id)
        
        is_valid, seed_value, status = self.form_manager.validate_seed(seed_text)
        
        if not is_valid:
            if update.message is not None:
                await update.message.reply_text(TextContent.FORM_SEED_INVALID)
            return
        
        self.form_manager.update_form_field(user_id, 'seed', seed_value)
        
        if status == "已跳过":
            message = TextContent.FORM_SEED_SKIPPED
        elif status == "随机":
            message = TextContent.FORM_SEED_RANDOM
        else:
            message = TextContent.FORM_SEED_SET.format(seed=seed_value)
        
        # 返回表单页面
        form_data = self.form_manager.get_user_form(user_id)
        summary = self.form_manager.format_form_summary(user_id)
        text = message + "\n\n" + TextContent.FORM_SUMMARY.format(**summary)
        
        if update.message is None:
            return
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.advanced_form_menu(cast(Dict[str, object], form_data))
        )

    @safe_call
    @require_auth
    async def handle_text_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理文本提示词"""
        
        if update.message is None or update.effective_user is None:
            return
        text_val = update.message.text
        if text_val is None:
            return
        prompt: str = text_val.strip()
        user_id: str = str(update.effective_user.id)
        username: str = update.effective_user.username or update.effective_user.first_name
        
        # 检查是否在等待表单输入
        if self.form_manager.is_waiting_for_input(user_id):
            await self.handle_form_input(update, user_id, prompt)
            return
        
        if user_id in self.waiting_for_negative_prompt:
            await self.handle_negative_prompt_input(update, user_id, prompt)
            return

        # 不再清理上一条消息的按钮，改为保留最近10条的点赞按钮，超出时再移除旧的

        if prompt.startswith('/'):
            return  # 忽略命令

        # 仅输入数字：重复执行“重新生成上一个提示词”的功能，次数限制在配置上限
        if prompt.isdigit():
            n = int(prompt)
            n = max(1, min(n, Config.REGENERATE_MAX_RUNS))
            if self.last_prompt is None:
                await update.message.reply_text(TextContent.NO_LAST_PROMPT)
                return
            for _ in range(n):
                # 队列限制检查
                if self.security.get_queue_size() >= Config.MAX_QUEUE_SIZE:
                    await update.message.reply_text(TextContent.QUEUE_FULL)
                    break
                # 频控
                limit, limit_msg = self.security.check_generation_limit(user_id)
                if not limit:
                    await update.message.reply_text(limit_msg + "\n\n")
                    break
                await self.generate_image_task(user_id, username, self.last_prompt, update.message)
            return
        
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
    async def generate_image_task(self, user_id: str, username: str, prompt: str, message: Message, from_form: bool = False, override_params: Optional[Dict[str, Any]] = None) -> None:
        """生成图片任务"""
        task_id = str(uuid.uuid4())[:8]
        self.last_prompt = prompt  # 保存最后的提示词
        
        # 获取用户自定义设置
        user_settings: UserSettings = self.get_user_settings(user_id)
        
        # 生成参数来源优先级：override_params > 表单参数 > 用户设置
        generation_params: Dict[str, Any]
        if override_params is not None:
            generation_params = dict(user_settings)
            generation_params.update(override_params)
        elif from_form:
            generation_params = self.form_manager.generate_params_from_form(user_id, user_settings)
        else:
            generation_params = dict(user_settings)
        
        # 自动生成随机seed（除非用户已指定）
        if 'seed' not in generation_params or generation_params['seed'] is None:
            import random
            generation_params['seed'] = random.randint(1, 2147483647)  # 32位有符号整数范围
        
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
                resolution=f"{generation_params['width']}x{generation_params['height']}"
            ),
            reply_markup=reply_markup
        )
        
        # 调用SD API生成图片，使用生成参数
        # 将 negative_prompt 单独取出以满足类型检查
        neg_prompt_any = generation_params.get('negative_prompt')
        neg_prompt: Optional[str] = neg_prompt_any if isinstance(neg_prompt_any, str) else None
        rest_params = dict(generation_params)
        if 'negative_prompt' in rest_params:
            rest_params.pop('negative_prompt')
        success, result = await self.sd_controller.generate_image(
            prompt,
            neg_prompt,
            **rest_params
        )
        
        if success:
            reply_markup = Keyboards.like_keyboard(task_id)
            await progress_msg.edit_text(TextContent.GENERATE_SUCCESS)
            
            # 构建标题，如果是表单生成则显示更多信息
            if from_form:
                form_data = self.form_manager.get_user_form(user_id)
                seed_info = f"🎲 种子: {generation_params['seed']}"
                hires_info = f"🔍 高清修复: {'开启' if bool(form_data.get('hires_fix')) else '关闭'}"
                caption = TextContent.GENERATE_CAPTION.format(
                    prompt=prompt,
                    resolution=f"{generation_params['width']}x{generation_params['height']}"
                ) + f"\n{seed_info}\n{hires_info}"
            else:
                caption = TextContent.GENERATE_CAPTION.format(
                    prompt=prompt,
                    resolution=f"{generation_params['width']}x{generation_params['height']}"
                )
            
            image_bytes, api_result = cast(Tuple[io.BytesIO, Dict[str, Any]], result)
            # 记录任务结果
            self.task_results[task_id] = api_result
            self.task_params[task_id] = generation_params
            # 判断是否本次已启用高清修复
            is_hr_enabled = bool(generation_params.get('enable_hr'))
            reply_markup = Keyboards.like_keyboard(task_id, show_enhance=not is_hr_enabled)
            sent_msg = await message.reply_photo(
                photo=image_bytes,
            caption=caption,
                reply_markup=reply_markup
            )
            
            self.user_last_photo_msg[user_id] = sent_msg.message_id

            # 快照：仅保存对 SD 生成有用的参数（可复用）
            base_keys = ['negative_prompt', 'seed', 'width', 'height', 'steps', 'cfg_scale', 'sampler_name']
            params_snapshot = {k: generation_params[k] for k in base_keys if k in generation_params}
            params_snapshot_t: SnapshotParams = cast(SnapshotParams, params_snapshot)
            self.task_snapshots[task_id] = {
                'prompt': prompt,
                'params': params_snapshot_t,
            }

            # 写入磁盘缓存（仅保存最近 SNAPSHOT_CACHE_LIMIT 条）
            try:
                os.makedirs(Config.DATA_DIR, exist_ok=True)
                # 裁剪
                if len(self.task_snapshots) > Config.SNAPSHOT_CACHE_LIMIT:
                    # 保留最新的 N 条
                    latest_items = list(self.task_snapshots.items())[-Config.SNAPSHOT_CACHE_LIMIT:]
                    self.task_snapshots = {k: v for k, v in latest_items}
                with open(self._snapshot_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cast(Dict[str, Any], self.task_snapshots), f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            # 维护最近10条带点赞按钮的图片消息
            chat_id = message.chat_id
            dq = self.user_recent_photo_msgs.setdefault(user_id, deque())
            dq.append((chat_id, sent_msg.message_id))
            if len(dq) > Config.LIKABLE_MESSAGE_LIMIT and self.application is not None:  # type: ignore[reportUnknownMemberType]
                old_chat_id, old_msg_id = dq.popleft()
                try:
                    if self.application.bot is not None:  # type: ignore[attr-defined]
                        await self.application.bot.edit_message_reply_markup(  # type: ignore[attr-defined]
                            chat_id=old_chat_id,
                            message_id=old_msg_id,
                            reply_markup=None
                        )
                except Exception:
                    pass

            # 清理进度消息
            try:
                await progress_msg.delete()
            except:
                pass
            
            # 记录成功日志
            self.security.log_generation(user_id, username, prompt, True)
            self.security.complete_task(task_id, "success")
            
        else:
            await progress_msg.edit_text(TextContent.GENERATE_FAIL.format(error=result, prompt=prompt[:50]))
            
            # 记录失败日志
            self.security.log_generation(user_id, username, prompt, False, str(result) if not isinstance(result, str) else result)
            self.security.complete_task(task_id, f"failed: {result}")
    
    @require_auth
    async def regenerate_image_with_last_prompt_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """重新生成上一个提示词的图片"""
        if update.effective_user is None or update.message is None:
            return
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

    async def enhance_image_hr(self, query: CallbackQuery, user_id: str, task_id: str) -> None:
        """基于快照参数，启用高清修复重新生成。"""
        snapshot = self.task_snapshots.get(task_id)
        if not snapshot:
            await query.answer("找不到该任务的参数，无法高清化", show_alert=True)
            return

        # 从快照参数出发，避免被用户此后改动影响
        generation_params_dict: Dict[str, Any] = dict(snapshot['params'])
        # 强制高清修复（不依赖表单状态）
        h = Config.HIRES_DEFAULTS
        generation_params_dict['enable_hr'] = True
        generation_params_dict['hr_scale'] = h['hr_scale']
        generation_params_dict['hr_upscaler'] = h['hr_upscaler']
        generation_params_dict['denoising_strength'] = h['denoising_strength']
        total_steps = int(generation_params_dict.get('steps', 20) or 20)
        generation_params_dict['hr_second_pass_steps'] = max(1, int(total_steps * h['hr_second_pass_ratio']))
        generation_params_dict['hr_resize_x'] = h['hr_resize_x']
        generation_params_dict['hr_resize_y'] = h['hr_resize_y']

        # 复用快照中的原始提示词
        original_prompt = snapshot.get('prompt') or self.last_prompt or ""
        try:
            await query.edit_message_text("✨ 正在对图片进行高清化...")
        except Exception:
            # 可能因为原消息是图片没有文本，无法 edit_text，退化为发送一条新进度消息
            if query.message is not None:
                await query.message.reply_text("✨ 正在对图片进行高清化...")

        # 直接发起新任务（使用当前消息作为 message 容器），并覆盖参数为快照参数 + 强制高清修复
        await self.generate_image_task(
            user_id,
            query.from_user.username or query.from_user.first_name,
            original_prompt,
            query.message,
            from_form=False,
            override_params=generation_params_dict,
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """帮助命令"""
        if update.message is not None:
            await update.message.reply_text(TextContent.HELP)
    
    def run(self) -> None:
        """运行机器人"""
        if not Config.BOT_TOKEN:
            logger.error("请在 .env 文件中设置 BOT_TOKEN")
            return
        
        if not Config.AUTHORIZED_USERS:
            logger.error("请在 .env 文件中设置 AUTHORIZED_USERS")
            return
        
        self.application = Application.builder().token(Config.BOT_TOKEN).build()  # type: ignore[assignment]
        
        # 添加处理器
        self.application.add_handler(CommandHandler("start", self.start))  # type: ignore[arg-type]
        self.application.add_handler(CommandHandler("re", self.regenerate_image_with_last_prompt_task))  # type: ignore[arg-type]
        self.application.add_handler(CommandHandler("help", self.help_command))  # type: ignore[arg-type]
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))  # type: ignore[arg-type]
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_prompt))  # type: ignore[arg-type]
        
        logger.info("Stable Diffusion 控制机器人启动中...")
        logger.info(f"SD WebUI API: {Config.SD_API_URL}")
        self.application.run_polling()  # type: ignore[attr-defined]