import json
import os
from typing import Dict
from config import UserSettings, Config

class UserManager:
    user_settings: Dict[str, UserSettings]
    settings_file: str

    def __init__(self, default_params: UserSettings) -> None:
        self.user_settings = {}
        self.default_params = default_params
        # 将用户设置集中保存在 data 目录中
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        self.settings_file = os.path.join(Config.DATA_DIR, "user_settings.json")
        self.load_settings()

    def load_settings(self) -> None:
        """从本地文件加载用户设置"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    # 合并默认参数和保存的设置
                    for user_id, settings in saved_settings.items():
                        user_settings = self.default_params.copy()
                        user_settings.update(settings)
                        self.user_settings[user_id] = user_settings
                print(f"✅ 已加载 {len(self.user_settings)} 个用户的设置")
        except Exception as e:
            print(f"⚠️ 加载用户设置失败: {e}")

    def save_settings(self) -> None:
        """保存用户设置到本地文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.settings_file)), exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_settings, f, indent=2, ensure_ascii=False)
            print(f"✅ 用户设置已保存到 {self.settings_file}")
        except Exception as e:
            print(f"❌ 保存用户设置失败: {e}")

    def get_settings(self, user_id: str) -> UserSettings:
        if user_id not in self.user_settings:
            self.user_settings[user_id] = self.default_params.copy()
            self.save_settings()  # 立即保存新用户设置
        return self.user_settings[user_id]

    def set_resolution(self, user_id: str, width: int, height: int) -> None:
        settings = self.get_settings(user_id)
        settings['width'] = width
        settings['height'] = height
        self.save_settings()  # 保存更改

    def set_negative_prompt(self, user_id: str, negative_prompt: str) -> None:
        """设置用户自定义负面词"""
        settings = self.get_settings(user_id)
        settings['negative_prompt'] = negative_prompt.strip()
        self.save_settings()  # 保存更改
        print(f"✅ 用户 {user_id} 的负面词已更新")

    def reset_negative_prompt(self, user_id: str) -> None:
        """重置用户负面词为默认值"""
        settings = self.get_settings(user_id)
        settings['negative_prompt'] = self.default_params['negative_prompt']
        self.save_settings()  # 保存更改
        print(f"✅ 用户 {user_id} 的负面词已重置为默认")