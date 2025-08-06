from typing import Dict
from config import UserSettings

class UserManager:
    user_settings: Dict[str, UserSettings]

    def __init__(self, default_params: UserSettings) -> None:
        self.user_settings = {}
        self.default_params = default_params

    def get_settings(self, user_id: str) -> UserSettings:
        if user_id not in self.user_settings:
            self.user_settings[user_id] = self.default_params.copy()
        return self.user_settings[user_id]

    def set_resolution(self, user_id: str, width: int, height: int) -> None:
        settings = self.get_settings(user_id)
        settings['width'] = width
        settings['height'] = height