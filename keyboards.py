from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class CallbackData(Enum):
    TXT2IMG = "txt2img"
    SD_STATUS = "sd_status"
    SD_SETTINGS = "sd_settings"
    RESOLUTION_SETTINGS = "resolution_settings"
    NEGATIVE_PROMPT_SETTINGS = "negative_prompt_settings"
    GENERATION_HISTORY = "generation_history"
    INPUT_PROMPT = "input_prompt"
    RANDOM_GENERATE = "random_generate"
    MAIN_MENU = "main_menu"
    INTERRUPT = "interrupt_{task_id}"
    LIKE = "like_{task_id}"
    ENHANCE_HR = "enhance_hr_{task_id}"
    SET_RESOLUTION = "set_resolution_{res}"
    SET_NEGATIVE_PROMPT = "set_negative_prompt"
    RESET_NEGATIVE_PROMPT = "reset_negative_prompt"
    CANCEL_NEGATIVE_PROMPT = "cancel_negative_prompt"
    # 新增表单相关回调
    ADVANCED_FORM = "advanced_form"
    FORM_SET_PROMPT = "form_set_prompt"
    FORM_SET_RESOLUTION = "form_set_resolution_{res}"
    FORM_SET_SEED = "form_set_seed"
    FORM_TOGGLE_HIRES = "form_toggle_hires"
    FORM_GENERATE = "form_generate"
    FORM_RESET = "form_reset"
    FORM_CANCEL_INPUT = "form_cancel_input"
    FORM_SET_RESOLUTION_MENU = "form_set_resolution_menu"

    @staticmethod
    def interrupt(task_id: str) -> str:
        return CallbackData.INTERRUPT.value.format(task_id=task_id)

    @staticmethod
    def like(task_id: str) -> str:
        return CallbackData.LIKE.value.format(task_id=task_id)

    @staticmethod
    def enhance_hr(task_id: str) -> str:
        return CallbackData.ENHANCE_HR.value.format(task_id=task_id)

    @staticmethod
    def set_resolution(res: str) -> str:
        return CallbackData.SET_RESOLUTION.value.format(res=res.replace('x', '_'))

    @staticmethod
    def form_set_resolution(res: str) -> str:
        return CallbackData.FORM_SET_RESOLUTION.value.format(res=res.replace('x', '_'))

class Keyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 生成图片", callback_data=CallbackData.TXT2IMG.value)],
            [InlineKeyboardButton("📊 SD状态", callback_data=CallbackData.SD_STATUS.value)],
            [InlineKeyboardButton("🛠️ SD设置", callback_data=CallbackData.SD_SETTINGS.value)],
            [InlineKeyboardButton("📈 生成历史", callback_data=CallbackData.GENERATION_HISTORY.value)],
        ])

    @staticmethod
    def generation_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ 输入提示词", callback_data=CallbackData.INPUT_PROMPT.value)],
            [InlineKeyboardButton("🎲 随机生成", callback_data=CallbackData.RANDOM_GENERATE.value)],
            [InlineKeyboardButton("📝 高级表单", callback_data=CallbackData.ADVANCED_FORM.value)],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data=CallbackData.MAIN_MENU.value)],
        ])

    @staticmethod
    def resolution_menu(current_res: str) -> InlineKeyboardMarkup:
        resolutions = [
            ("1024x1024", "正方形"),
            ("1216x832", "横屏"),
            ("832x1216", "竖屏"),
            ("1280x720", "宽屏 16:9"),
            ("720x1280", "竖屏 9:16")
        ]
        keyboard = []
        for res_text, desc in resolutions:
            prefix = "✅ " if res_text == current_res else ""
            button_text = f"{prefix}{res_text} ({desc})"
            callback_data = CallbackData.set_resolution(res_text)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data=CallbackData.MAIN_MENU.value)])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def sd_setting_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📐 分辨率设置", callback_data=CallbackData.RESOLUTION_SETTINGS.value)],
            [InlineKeyboardButton("🚫 负面词设置", callback_data=CallbackData.NEGATIVE_PROMPT_SETTINGS.value)],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data=CallbackData.MAIN_MENU.value)],
        ])

    @staticmethod
    def negative_prompt_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ 自定义负面词", callback_data=CallbackData.SET_NEGATIVE_PROMPT.value)],
            [InlineKeyboardButton("🔄 恢复默认", callback_data=CallbackData.RESET_NEGATIVE_PROMPT.value)],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data=CallbackData.MAIN_MENU.value)],
        ])

    @staticmethod
    def negative_prompt_input_menu() -> InlineKeyboardMarkup:
        """输入负面词时显示的键盘，包含取消按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ 取消输入", callback_data=CallbackData.CANCEL_NEGATIVE_PROMPT.value)],
        ])

    @staticmethod
    def interrupt_keyboard(task_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏹️ 中断生成", callback_data=CallbackData.interrupt(task_id))]
        ])

    @staticmethod
    def like_keyboard(task_id: str, show_enhance: bool = True) -> InlineKeyboardMarkup:
        row = [InlineKeyboardButton("👍 点赞并保存", callback_data=CallbackData.like(task_id))]
        if show_enhance:
            row.append(InlineKeyboardButton("✨ 高清化", callback_data=CallbackData.enhance_hr(task_id)))
        return InlineKeyboardMarkup([row])

    # 新增表单相关键盘
    @staticmethod
    def advanced_form_menu(form_data: dict) -> InlineKeyboardMarkup:
        """高级表单菜单"""
        prompt_text = f"✏️ 正面词: {'已设置' if form_data.get('prompt') else '未设置'}"
        resolution_text = f"📐 分辨率: {form_data.get('resolution', '未设置')}"
        seed_text = f"🎲 种子: {form_data.get('seed', '随机')}"
        hires_text = f"🔍 高清修复: {'✅ 开启' if form_data.get('hires_fix') else '❌ 关闭'}"
        
        keyboard = [
            [InlineKeyboardButton(prompt_text, callback_data=CallbackData.FORM_SET_PROMPT.value)],
            [InlineKeyboardButton(resolution_text, callback_data=CallbackData.FORM_SET_RESOLUTION_MENU.value)],
            [InlineKeyboardButton(seed_text, callback_data=CallbackData.FORM_SET_SEED.value)],
            [InlineKeyboardButton(hires_text, callback_data=CallbackData.FORM_TOGGLE_HIRES.value)],
            [InlineKeyboardButton("🚀 生成图片", callback_data=CallbackData.FORM_GENERATE.value)],
            [
                InlineKeyboardButton("🔄 重置表单", callback_data=CallbackData.FORM_RESET.value),
                InlineKeyboardButton("🔙 返回", callback_data=CallbackData.TXT2IMG.value)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def form_resolution_menu(current_res: str) -> InlineKeyboardMarkup:
        """表单中的分辨率选择菜单"""
        resolutions = [
            ("1024x1024", "正方形"),
            ("1216x832", "横屏"),
            ("832x1216", "竖屏"),
            ("1280x720", "宽屏 16:9"),
            ("720x1280", "竖屏 9:16"),
            ("512x512", "小尺寸"),
            ("768x768", "中等尺寸")
        ]
        keyboard = []
        for res_text, desc in resolutions:
            prefix = "✅ " if res_text == current_res else ""
            button_text = f"{prefix}{res_text} ({desc})"
            callback_data = CallbackData.form_set_resolution(res_text)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        keyboard.append([InlineKeyboardButton("🔙 返回表单", callback_data=CallbackData.ADVANCED_FORM.value)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def form_input_cancel_menu() -> InlineKeyboardMarkup:
        """表单输入时的取消菜单"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ 取消输入", callback_data=CallbackData.FORM_CANCEL_INPUT.value)],
        ])