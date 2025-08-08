# tests/test_integration.py
import pytest
import asyncio
import tempfile
import shutil
import os
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

# 导入待测试的模块
from bot import TelegramBot
from config import Config
from security import SecurityManager
from user_manager import UserManager
from form_manager import FormManager
from sd_controller import StableDiffusionController


@pytest.mark.integration
class TestBotIntegration:
    """Bot集成测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录fixture"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Mock配置fixture"""
        with patch.object(Config, 'DATA_DIR', temp_dir), \
             patch.object(Config, 'BOT_TOKEN', 'test_token'), \
             patch.object(Config, 'AUTHORIZED_USERS', ['123', '456']):
            yield Config
    
    @pytest.fixture
    def bot_instance(self, mock_config):
        """Bot实例fixture"""
        with patch('bot.Application') as mock_app:
            bot = TelegramBot()
            yield bot
    
    @pytest.mark.asyncio
    async def test_start_command_authorized_user(self, bot_instance):
        """测试授权用户的start命令"""
        # Mock update和context
        mock_update = Mock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 123
        mock_update.effective_user.first_name = "TestUser"
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = Mock()
        
        # Mock SD API状态检查
        with patch.object(bot_instance.sd_controller, 'check_api_status', return_value=True):
            await bot_instance.start(mock_update, mock_context)
        
        # 验证回复消息被调用
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        self.assertIn("TestUser", call_args[0][0])
    
    @pytest.mark.asyncio
    async def test_start_command_unauthorized_user(self, bot_instance):
        """测试未授权用户的start命令"""
        mock_update = Mock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 999  # 未授权
        mock_update.effective_user.username = "UnauthorizedUser"
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = Mock()
        
        await bot_instance.start(mock_update, mock_context)
        
        # 验证发送了未授权消息
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        self.assertIn("未被授权", call_args[0][0])
    
    @pytest.mark.asyncio
    async def test_text_prompt_handling(self, bot_instance):
        """测试文本提示词处理"""
        mock_update = Mock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 123  # 授权用户
        mock_update.effective_user.username = "TestUser"
        mock_update.message = Mock()
        mock_update.message.text = "a beautiful landscape"
        mock_update.message.reply_text = AsyncMock()
        mock_update.message.reply_photo = AsyncMock()
        
        mock_context = Mock()
        
        # Mock SD生成成功
        import io
        from PIL import Image
        import base64
        
        # 创建测试图片
        test_img = Image.new('RGB', (64, 64), color='red')
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        mock_result = (img_bytes, {'info': 'test info'})
        
        with patch.object(bot_instance.sd_controller, 'generate_image', return_value=(True, mock_result)), \
             patch.object(bot_instance.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            await bot_instance.handle_text_prompt(mock_update, mock_context)
        
        # 验证图片被发送
        mock_update.message.reply_photo.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_callback_handling_main_menu(self, bot_instance):
        """测试回调处理 - 主菜单"""
        mock_query = Mock()
        mock_query.from_user = Mock()
        mock_query.from_user.id = 123
        mock_query.from_user.first_name = "TestUser"
        mock_query.data = "main_menu"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()
        
        mock_update = Mock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = mock_query.from_user
        
        mock_context = Mock()
        
        with patch.object(bot_instance.sd_controller, 'check_api_status', return_value=True):
            await bot_instance.handle_callback(mock_update, mock_context)
        
        # 验证回调被应答和消息被编辑
        mock_query.answer.assert_called_once()
        mock_query.edit_message_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_form_workflow(self, bot_instance):
        """测试表单工作流程"""
        user_id = "123"
        
        # 1. 显示高级表单
        mock_query = Mock()
        mock_query.from_user = Mock()
        mock_query.from_user.id = int(user_id)
        mock_query.data = "advanced_form"
        mock_query.answer = AsyncMock()
        mock_query.edit_message_text = AsyncMock()
        
        mock_update = Mock()
        mock_update.callback_query = mock_query
        mock_update.effective_user = mock_query.from_user
        
        await bot_instance.handle_callback(mock_update, Mock())
        
        # 验证表单被显示
        mock_query.edit_message_text.assert_called_once()
        
        # 2. 设置表单提示词
        mock_query.data = "form_set_prompt"
        mock_query.edit_message_text.reset_mock()
        
        await bot_instance.handle_callback(mock_update, Mock())
        
        # 验证进入提示词输入状态
        assert bot_instance.form_manager.is_waiting_for_input(user_id)
        
        # 3. 输入提示词
        mock_update.callback_query = None
        mock_update.message = Mock()
        mock_update.message.text = "test prompt"
        mock_update.message.reply_text = AsyncMock()
        
        await bot_instance.handle_text_prompt(mock_update, Mock())
        
        # 验证提示词被设置
        form_data = bot_instance.form_manager.get_user_form(user_id)
        assert form_data['prompt'] == "test prompt"
        assert not bot_instance.form_manager.is_waiting_for_input(user_id)


@pytest.mark.integration
class TestSecurityIntegration:
    """安全管理集成测试"""
    
    @pytest.fixture
    def security_manager(self):
        return SecurityManager()
    
    def test_complete_task_workflow(self, security_manager):
        """测试完整任务工作流程"""
        task_id = "test_task"
        user_id = "test_user"
        prompt = "test prompt"
        
        # 1. 添加任务
        security_manager.add_task(task_id, user_id, prompt)
        assert security_manager.get_queue_size() == 1
        
        # 2. 记录生成
        security_manager.add_generation_record(user_id)
        
        # 3. 记录日志
        log_entry = security_manager.log_generation(user_id, "username", prompt, True)
        assert log_entry['success']
        
        # 4. 完成任务
        security_manager.complete_task(task_id, "success")
        task = security_manager.active_tasks[task_id]
        assert task['completed']
        assert task['result'] == "success"
        
        # 5. 验证历史记录
        assert len(security_manager.generation_history) == 1
        assert security_manager.generation_history[0]['prompt'] == prompt


@pytest.mark.integration  
class TestUserDataPersistence:
    """用户数据持久化集成测试"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_user_settings_persistence(self, temp_dir):
        """测试用户设置持久化"""
        with patch.object(Config, 'DATA_DIR', temp_dir):
            # 创建用户管理器并设置一些数据
            user_manager1 = UserManager(Config.SD_DEFAULT_PARAMS)
            user_manager1.set_resolution("123", 512, 768)
            user_manager1.set_negative_prompt("123", "custom negative prompt")
            
            # 创建新的用户管理器实例（模拟重启）
            user_manager2 = UserManager(Config.SD_DEFAULT_PARAMS)
            
            # 验证数据被正确加载
            settings = user_manager2.get_settings("123")
            assert settings['width'] == 512
            assert settings['height'] == 768
            assert settings['negative_prompt'] == "custom negative prompt"
    
    def test_form_data_lifecycle(self, temp_dir):
        """测试表单数据生命周期"""
        form_manager = FormManager()
        user_id = "test_user"
        
        # 设置表单数据
        form_manager.update_form_field(user_id, 'prompt', 'test prompt')
        form_manager.update_form_field(user_id, 'resolution', '512x512')
        form_manager.update_form_field(user_id, 'seed', 123456)
        form_manager.update_form_field(user_id, 'hires_fix', True)
        
        # 生成参数
        user_settings = Config.SD_DEFAULT_PARAMS.copy()
        params = form_manager.generate_params_from_form(user_id, user_settings)
        
        # 验证参数正确生成
        assert params['width'] == 512
        assert params['height'] == 512
        assert params['seed'] == 123456
        assert params['enable_hr'] == True
        
        # 重置表单
        form_manager.reset_user_form(user_id)
        new_form_data = form_manager.get_user_form(user_id)
        
        # 验证重置成功
        assert new_form_data['prompt'] is None
        assert new_form_data['resolution'] is None
        assert new_form_data['seed'] is None
        assert new_form_data['hires_fix'] == False


@pytest.mark.integration
@pytest.mark.slow
class TestSDControllerIntegration:
    """SD控制器集成测试（需要mock外部API）"""
    
    @pytest.fixture
    def sd_controller(self):
        return StableDiffusionController()
    
    @pytest.mark.asyncio
    async def test_generation_workflow_success(self, sd_controller):
        """测试完整生成工作流程 - 成功案例"""
        import io
        from PIL import Image
        import base64
        
        # 创建测试图片
        test_img = Image.new('RGB', (64, 64), color='blue')
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        img_b64 = base64.b64encode(img_data).decode()
        
        mock_response_data = {
            'images': [img_b64],
            'info': '{"infotexts": ["test parameters"]}'
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 执行生成
            success, result = await sd_controller.generate_image(
                "test prompt",
                "test negative",
                width=512,
                height=512,
                steps=20
            )
            
            # 验证结果
            assert success == True
            assert isinstance(result, tuple)
            assert len(result) == 2
            
            img_bytes, api_result = result
            assert isinstance(img_bytes, io.BytesIO)
            assert isinstance(api_result, dict)
            assert 'images' in api_result
    
    @pytest.mark.asyncio
    async def test_generation_workflow_failure(self, sd_controller):
        """测试完整生成工作流程 - 失败案例"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 执行生成
            success, result = await sd_controller.generate_image("test prompt")
            
            # 验证失败结果
            assert success == False
            assert isinstance(result, str)
            assert "API错误" in result
    
    @pytest.mark.asyncio
    async def test_api_status_and_models_workflow(self, sd_controller):
        """测试API状态和模型获取工作流程"""
        # Mock API状态检查
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            status = await sd_controller.check_api_status()
            assert status == True
        
        # Mock模型获取
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = [
                {'title': 'model1.safetensors'},
                {'title': 'model2.ckpt'}
            ]
            mock_get.return_value.__aenter__.return_value = mock_response
            
            models = await sd_controller.get_models()
            assert len(models) == 2
            assert 'model1.safetensors' in models


# 性能测试
@pytest.mark.slow
class TestPerformance:
    """性能测试"""
    
    def test_user_manager_performance(self):
        """测试用户管理器性能"""
        assert False, "Skip test_user_manager_performance"
        #import time
        
        #with tempfile.TemporaryDirectory() as temp_dir:
        #    with patch.object(Config, 'DATA_DIR', temp_dir):
        #        user_manager = UserManager(Config.SD_DEFAULT_PARAMS)
        #        
        #        # 测试大量用户设置的性能
        #        start_time = time.time()
        #        
        #        for i in range(1000):
        #            user_id = f"user_{i}"
        #            user_manager.set_resolution(user_id, 512, 512)
        #            user_manager.set_negative_prompt(user_id, f"negative_{i}")
        #        
        #        end_time = time.time()
        #        
        #        # 验证性能在合理范围内（1000个用户操作应该在1秒内完成）
        #        assert end_time - start_time < 1.0
        #        
        #        # 验证数据正确性
        #        settings = user_manager.get_settings("user_500")
        #        assert settings['width'] == 512
        #        assert settings['negative_prompt'] == "negative_500"
    
    def test_security_manager_performance(self):
        """测试安全管理器性能"""
        import time
        
        security = SecurityManager()
        security.authorized_users = ['123', '456']
        
        start_time = time.time()
        
        # 测试大量安全检查
        for i in range(10000):
            prompt = f"test prompt {i}"
            is_safe, _ = security.is_safe_prompt(prompt)
            assert is_safe == True
            
            # 测试授权检查
            is_auth = security.is_authorized_user('123')
            assert is_auth == True
        
        end_time = time.time()
        
        # 10000次检查应该在0.5秒内完成
        assert end_time - start_time < 0.5


# 测试运行器
if __name__ == '__main__':
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing'
    ])