from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class Keyboards:
    @staticmethod
    def main_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎨 生成图片", callback_data="txt2img")],
            [InlineKeyboardButton("📊 SD状态", callback_data="sd_status")],
            [InlineKeyboardButton("🛠️ SD设置", callback_data="sd_settings")],
            [InlineKeyboardButton("📐 分辨率设置", callback_data="resolution_settings")],
            [InlineKeyboardButton("📈 生成历史", callback_data="generation_history")],
        ])

    @staticmethod
    def generation_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ 输入提示词", callback_data="input_prompt")],
            [InlineKeyboardButton("🎲 随机生成", callback_data="random_generate")],
            [InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")],
        ])

    @staticmethod
    def resolution_menu(current_res, user_id, get_user_settings):
        resolutions = [
            ("1024x1024", "1024", "1024", "正方形"),
            ("1216x832", "1216", "832", "横屏"),
            ("832x1216", "832", "1216", "竖屏"),
            ("1280x720", "1280", "720", "宽屏 16:9"),
            ("720x1280", "720", "1280", "竖屏 9:16")
        ]
        keyboard = []
        for res_text, width, height, desc in resolutions:
            prefix = "✅ " if res_text == current_res else "   "
            button_text = f"{prefix}{res_text} ({desc})"
            callback_data = f"set_resolution_{width}_{height}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        keyboard.append([InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")])
        return InlineKeyboardMarkup(keyboard)