from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

class ViewManager:
    @staticmethod
    async def show_sd_status(query, sd_controller, config):
        api_status = await sd_controller.check_api_status()
        if api_status:
            models = await sd_controller.get_models()
            samplers = await sd_controller.get_samplers()
            progress, eta = await sd_controller.get_progress()
            current_model = await sd_controller.get_current_model()
            status_text = (
                f"🟢 Stable Diffusion WebUI 状态\n\n"
                f"📡 API: 在线\n"
                f"🎯 当前模型: {current_model}\n"
                f"📦 可用模型: {len(models)}\n"
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
                f"API地址: {config.SD_API_URL}"
            )
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]]
        await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard))

    @staticmethod
    async def show_sd_settings(query, user_settings):
        settings_text = (
            f"🛠️ 当前设置:\n\n"
            f"📐 分辨率: {user_settings['width']}x{user_settings['height']}\n"
            f"🔢 步数: {user_settings['steps']}\n"
            f"🎚️ CFG Scale: {user_settings['cfg_scale']}\n"
            f"🎨 采样器: {user_settings['sampler_name']}\n\n"
            f"📝 默认负面提示词:\n{user_settings['negative_prompt'][:100]}..."
        )
        keyboard = [[InlineKeyboardButton("🔙 返回", callback_data="main_menu")]]
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))

    @staticmethod
    async def show_generation_history(query, history):
        history = history[-5:]
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
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))