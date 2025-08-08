# tests/factories.py
"""
测试数据工厂和Mock工具
提供标准化的测试数据生成和Mock对象创建
"""

import factory
import io
import base64
from PIL import Image
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, Optional
import random
import string


class UserFactory:
    """用户数据工厂"""
    
    @staticmethod
    def create_telegram_user(user_id: int = None, username: str = None, first_name: str = None) -> Mock:
        """创建Telegram用户Mock对象"""
        user = Mock()
        user.id = user_id or random.randint(100000, 999999)
        user.username = username or f"user_{user.id}"
        user.first_name = first_name or f"User{user.id}"
        user.last_name = "Test"
        return user
    
    @staticmethod
    def create_authorized_user() -> Mock:
        """创建授权用户"""
        return UserFactory.create_telegram_user(user_id=123, username="authorized_user")
    
    @staticmethod
    def create_unauthorized_user() -> Mock:
        """创建未授权用户"""
        return UserFactory.create_telegram_user(user_id=999, username="unauthorized_user")


class MessageFactory:
    """消息数据工厂"""
    
    @staticmethod
    def create_text_message(text: str, user: Mock = None, chat_id: int = None) -> Mock:
        """创建文本消息Mock对象"""
        message = Mock()
        message.text = text
        message.message_id = random.randint(1000, 9999)
        message.chat_id = chat_id or random.randint(100000, 999999)
        message.from_user = user or UserFactory.create_authorized_user()
        message.reply_text = AsyncMock()
        message.reply_photo = AsyncMock()
        message.delete = AsyncMock()
        return message
    
    @staticmethod
    def create_callback_query(data: str, user: Mock = None, message: Mock = None) -> Mock:
        """创建回调查询Mock对象"""
        query = Mock()
        query.data = data
        query.from_user = user or UserFactory.create_authorized_user()
        query.message = message or MessageFactory.create_text_message("test")
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_caption = AsyncMock()
        return query


class UpdateFactory:
    """更新对象工厂"""
    
    @staticmethod
    def create_message_update(text: str, user: Mock = None) -> Mock:
        """创建消息更新Mock对象"""
        update = Mock()
        user = user or UserFactory.create_authorized_user()
        update.effective_user = user
        update.message = MessageFactory.create_text_message(text, user)
        update.callback_query = None
        return update
    
    @staticmethod
    def create_callback_update(callback_data: str, user: Mock = None) -> Mock:
        """创建回调更新Mock对象"""
        update = Mock()
        user = user or UserFactory.create_authorized_user()
        update.effective_user = user
        update.callback_query = MessageFactory.create_callback_query(callback_data, user)
        update.message = None
        return update


class ImageFactory:
    """图片数据工厂"""
    
    @staticmethod
    def create_test_image(width: int = 64, height: int = 64, color: str = 'red') -> bytes:
        """创建测试图片数据"""
        img = Image.new('RGB', (width, height), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    @staticmethod
    def create_base64_image(width: int = 64, height: int = 64, color: str = 'red') -> str:
        """创建base64编码的测试图片"""
        img_data = ImageFactory.create_test_image(width, height, color)
        return base64.b64encode(img_data).decode()
    
    @staticmethod
    def create_sd_response(prompt: str = "test prompt", width: int = 64, height: int = 64) -> Dict[str, Any]:
        """创建SD API响应Mock数据"""
        img_b64 = ImageFactory.create_base64_image(width, height)
        return {
            'images': [img_b64],
            'info': f'{{"infotexts": ["{prompt}, Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 123456"]}}'
        }


class PromptFactory:
    """提示词工厂"""
    
    SAFE_PROMPTS = [
        "a beautiful landscape with mountains",
        "cute cat sitting on a chair",
        "anime girl with blue hair",
        "peaceful forest scene",
        "colorful flower garden",
        "majestic castle in the clouds"
    ]
    
    UNSAFE_PROMPTS = [
        "violence and blood",
        "gore scene with death",
        "kill the enemy"
    ]
    
    @staticmethod
    def random_safe_prompt() -> str:
        """生成随机安全提示词"""
        return random.choice(PromptFactory.SAFE_PROMPTS)
    
    @staticmethod
    def random_unsafe_prompt() -> str:
        """生成随机不安全提示词"""
        return random.choice(PromptFactory.UNSAFE_PROMPTS)
    
    @staticmethod
    def long_prompt() -> str:
        """生成超长提示词"""
        return "a " * 200  # 超过MAX_PROMPT_LENGTH
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class ConfigFactory:
    """配置工厂"""
    
    @staticmethod
    def create_test_config() -> Dict[str, Any]:
        """创建测试配置"""
        return {
            'BOT_TOKEN': 'test_token_123456',
            'AUTHORIZED_USERS': ['123', '456', '789'],
            'SD_API_URL': 'http://localhost:7860',
            'SD_API_TIMEOUT': 60,
            'MAX_PROMPT_LENGTH': 500,
            'MAX_QUEUE_SIZE': 5
        }
    
    @staticmethod
    def create_user_settings(width: int = 1024, height: int = 1024) -> Dict[str, Any]:
        """创建用户设置"""
        return {
            'width': width,
            'height': height,
            'steps': 20,
            'cfg_scale': 7.0,
            'sampler_name': 'Euler a',
            'negative_prompt': 'lowres, bad anatomy'
        }


class SDAPIFactory:
    """SD API响应工厂"""
    
    @staticmethod
    def create_models_response() -> list:
        """创建模型列表响应"""
        return [
            {'title': 'model1.safetensors', 'model_name': 'model1'},
            {'title': 'model2.ckpt', 'model_name': 'model2'},
            {'title': 'anime_model.safetensors', 'model_name': 'anime_model'}
        ]
    
    @staticmethod
    def create_samplers_response() -> list:
        """创建采样器列表响应"""
        return [
            {'name': 'Euler a'},
            {'name': 'Euler'},
            {'name': 'DPM++ 2M Karras'},
            {'name': 'DDIM'}
        ]
    
    @staticmethod
    def create_options_response() -> Dict[str, Any]:
        """创建选项响应"""
        return {
            'sd_model_checkpoint': 'path/to/model.safetensors',
            'samples_save': True,
            'samples_format': 'png'
        }
    
    @staticmethod
    def create_progress_response(progress: float = 0.5, eta: float = 10.5) -> Dict[str, Any]:
        """创建进度响应"""
        return {
            'progress': progress,
            'eta_relative': eta,
            'state': {'job': 'txt2img', 'job_count': 1, 'job_no': 0}
        }
    
    @staticmethod
    def create_error_response(status_code: int = 500, error_message: str = "Internal Server Error") -> Mock:
        """创建错误响应Mock"""
        response = AsyncMock()
        response.status = status_code
        response.text.return_value = error_message
        response.json.side_effect = Exception("JSON decode error")
        return response


class FormDataFactory:
    """表单数据工厂"""
    
    @staticmethod
    def create_empty_form() -> Dict[str, Any]:
        """创建空表单数据"""
        return {
            'prompt': None,
            'resolution': None,
            'seed': None,
            'hires_fix': False
        }
    
    @staticmethod
    def create_filled_form() -> Dict[str, Any]:
        """创建填充的表单数据"""
        return {
            'prompt': 'beautiful landscape',
            'resolution': '512x768',
            'seed': 123456,
            'hires_fix': True
        }
    
    @staticmethod
    def create_partial_form() -> Dict[str, Any]:
        """创建部分填充的表单数据"""
        return {
            'prompt': 'test prompt',
            'resolution': '1024x1024',
            'seed': None,
            'hires_fix': False
        }


class TaskFactory:
    """任务工厂"""
    
    @staticmethod
    def create_task_data(user_id: str = "123", prompt: str = "test prompt") -> Dict[str, Any]:
        """创建任务数据"""
        import time
        return {
            'user_id': user_id,
            'prompt': prompt,
            'start_time': time.time(),
            'completed': False,
            'end_time': None,
            'result': None
        }
    
    @staticmethod
    def create_completed_task(result: str = "success") -> Dict[str, Any]:
        """创建已完成任务数据"""
        import time
        task = TaskFactory.create_task_data()
        task['completed'] = True
        task['end_time'] = time.time()
        task['result'] = result
        return task


# Mock助手类
class MockHelper:
    """Mock助手工具"""
    
    @staticmethod
    def create_async_context_manager(return_value: Any) -> Mock:
        """创建异步上下文管理器Mock"""
        mock = AsyncMock()
        mock.__aenter__.return_value = return_value
        mock.__aexit__.return_value = None
        return mock
    
    @staticmethod
    def setup_aiohttp_mock(mock_session, responses: list) -> None:
        """设置aiohttp Mock响应"""
        if len(responses) == 1:
            # 单个响应
            mock_session.return_value.__aenter__.return_value = responses[0]
        else:
            # 多个响应序列
            mock_session.return_value.__aenter__.side_effect = responses
    
    @staticmethod
    def create_file_mock(content: str) -> Mock:
        """创建文件Mock对象"""
        file_mock = Mock()
        file_mock.read.return_value = content
        file_mock.write = Mock()
        file_mock.__enter__.return_value = file_mock
        file_mock.__exit__.return_value = None
        return file_mock


# 测试断言助手
class AssertHelper:
    """断言助手"""
    
    @staticmethod
    def assert_telegram_message_sent(mock_message, expected_text_contains: str = None):
        """断言Telegram消息被发送"""
        mock_message.reply_text.assert_called_once()
        if expected_text_contains:
            call_args = mock_message.reply_text.call_args
            assert expected_text_contains in call_args[0][0]
    
    @staticmethod
    def assert_telegram_photo_sent(mock_message, expected_caption_contains: str = None):
        """断言Telegram图片被发送"""
        mock_message.reply_photo.assert_called_once()
        if expected_caption_contains:
            call_args = mock_message.reply_photo.call_args
            caption = call_args[1].get('caption', '')
            assert expected_text_contains in caption
    
    @staticmethod
    def assert_callback_answered(mock_query, expected_text: str = None, show_alert: bool = False):
        """断言回调查询被应答"""
        mock_query.answer.assert_called_once()
        if expected_text or show_alert is not False:
            call_args = mock_query.answer.call_args
            if expected_text:
                assert call_args[0][0] == expected_text
            if show_alert is not False:
                assert call_args[1].get('show_alert') == show_alert
    
    @staticmethod
    def assert_message_edited(mock_query, expected_text_contains: str = None):
        """断言消息被编辑"""
        mock_query.edit_message_text.assert_called_once()
        if expected_text_contains:
            call_args = mock_query.edit_message_text.call_args
            assert expected_text_contains in call_args[0][0]
    
    @staticmethod
    def assert_form_field_set(form_manager, user_id: str, field: str, expected_value: Any):
        """断言表单字段被正确设置"""
        form_data = form_manager.get_user_form(user_id)
        assert form_data[field] == expected_value
    
    @staticmethod
    def assert_user_settings_updated(user_manager, user_id: str, **expected_settings):
        """断言用户设置被更新"""
        settings = user_manager.get_settings(user_id)
        for key, expected_value in expected_settings.items():
            assert settings[key] == expected_value
    
    @staticmethod
    def assert_task_in_queue(security_manager, task_id: str, expected_status: str = None):
        """断言任务在队列中"""
        assert task_id in security_manager.active_tasks
        if expected_status:
            task = security_manager.active_tasks[task_id]
            if expected_status == "completed":
                assert task['completed'] == True
            elif expected_status == "active":
                assert task['completed'] == False