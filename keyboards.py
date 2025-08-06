from enum import Enum
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class CallbackData(Enum):
    TXT2IMG = "txt2img"
    SD_STATUS = "sd_status"
    SD_SETTINGS = "sd_settings"
    RESOLUTION_SETTINGS = "resolution_settings"
    GENERATION_HISTORY = "generation_history"
    INPUT_PROMPT = "input_prompt"
    RANDOM_GENERATE = "random_generate"
    MAIN_MENU = "main_menu"
    INTERRUPT = "interrupt_{task_id}"
    LIKE = "like_{task_id}"
    SET_RESOLUTION = "set_resolution_{res}"

    @staticmethod
    def interrupt(task_id: str) -> str:
        return CallbackData.INTERRUPT.value.format(task_id=task_id)

    @staticmethod
    def like(task_id: str) -> str:
        return CallbackData.LIKE.value.format(task_id=task_id)

    @staticmethod
    def set_resolution(res: str) -> str:
        return CallbackData.SET_RESOLUTION.value.format(res=res.replace('x', '_'))

class Keyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 生成图片", callback_data=CallbackData.TXT2IMG.value)],
            [InlineKeyboardButton("📊 SD状态", callback_data=CallbackData.SD_STATUS.value)],
            [InlineKeyboardButton("🛠️ SD设置", callback_data=CallbackData.SD_SETTINGS.value)],
            [InlineKeyboardButton("📐 分辨率设置", callback_data=CallbackData.RESOLUTION_SETTINGS.value)],
            [InlineKeyboardButton("📈 生成历史", callback_data=CallbackData.GENERATION_HISTORY.value)],
        ])

    @staticmethod
    def generation_menu() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ 输入提示词", callback_data=CallbackData.INPUT_PROMPT.value)],
            [InlineKeyboardButton("🎲 随机生成", callback_data=CallbackData.RANDOM_GENERATE.value)],
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
    def interrupt_keyboard(task_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏹️ 中断生成", callback_data=CallbackData.interrupt(task_id))]
        ])

    @staticmethod
    def like_keyboard(task_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👍 点赞并保存", callback_data=CallbackData.like(task_id))]
        ])