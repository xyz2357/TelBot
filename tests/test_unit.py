import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
import asyncio
import json
import tempfile
import shutil
import os
from datetime import datetime
from typing import Dict, Any
import io
import base64
from PIL import Image

# 导入待测试的模块
from config import Config, UserSettings, FormData
from security import SecurityManager, require_auth
from user_manager import UserManager
from form_manager import FormManager
from sd_controller import StableDiffusionController
from text_content import TextContent


class TestConfig(unittest.TestCase):
    """测试配置类"""
    
    def test_default_config_values(self):
        """测试默认配置值"""
        self.assertEqual(Config.MAX_PROMPT_LENGTH, 500)
        self.assertEqual(Config.MAX_QUEUE_SIZE, 5)
        self.assertIn('width', Config.SD_DEFAULT_PARAMS)
        self.assertIn('height', Config.SD_DEFAULT_PARAMS)
        
    def test_authorized_users_parsing(self):
        """测试授权用户解析"""
        with patch.dict(os.environ, {'AUTHORIZED_USERS': '123,456,789'}):
            # 重新导入config以获取新的环境变量
            import importlib
            import config
            importlib.reload(config)
            # 注意：实际测试中可能需要更复杂的mock策略
            
    def test_hires_defaults(self):
        """测试高分辨率默认参数"""
        hires = Config.HIRES_DEFAULTS
        self.assertIn('hr_scale', hires)
        self.assertIn('hr_upscaler', hires)
        self.assertIn('denoising_strength', hires)


class TestSecurityManager(unittest.TestCase):
    """测试安全管理器"""
    
    def setUp(self):
        self.security = SecurityManager()
        
    def test_authorization(self):
        """测试用户授权"""
        # Mock authorized users
        self.security.authorized_users = ['123', '456']
        
        self.assertTrue(self.security.is_authorized_user('123'))
        self.assertTrue(self.security.is_authorized_user('456'))
        self.assertFalse(self.security.is_authorized_user('789'))
        
    def test_safe_prompt_validation(self):
        """测试提示词安全验证"""
        # 安全的提示词
        safe_prompt = "a beautiful landscape"
        is_safe, msg = self.security.is_safe_prompt(safe_prompt)
        self.assertTrue(is_safe)
        self.assertEqual(msg, "安全")
        
        # 过长的提示词
        long_prompt = "a" * 501
        is_safe, msg = self.security.is_safe_prompt(long_prompt)
        self.assertFalse(is_safe)
        self.assertEqual(msg, "提示词过长")
        
        # 包含不当内容的提示词
        unsafe_prompt = "violence and gore"
        is_safe, msg = self.security.is_safe_prompt(unsafe_prompt)
        self.assertFalse(is_safe)
        self.assertIn("violence", msg)
        
    def test_generation_limit(self):
        """测试生成频率限制"""
        user_id = "test_user"
        
        # 测试通过情况
        passed, msg = self.security.check_generation_limit(user_id)
        self.assertTrue(passed)
        self.assertEqual(msg, "通过")
        
    def test_task_management(self):
        """测试任务管理"""
        task_id = "test_task_123"
        user_id = "test_user"
        prompt = "test prompt"
        
        # 添加任务
        self.security.add_task(task_id, user_id, prompt)
        self.assertEqual(self.security.get_queue_size(), 1)
        
        # 完成任务
        self.security.complete_task(task_id, "success")
        task = self.security.active_tasks.get(task_id)
        self.assertTrue(task['completed'])
        self.assertEqual(task['result'], "success")
        
    def test_generation_logging(self):
        """测试生成日志记录"""
        user_id = "test_user"
        username = "test_username"
        prompt = "test prompt"
        
        # 记录成功生成
        log_entry = self.security.log_generation(user_id, username, prompt, True)
        self.assertTrue(log_entry['success'])
        self.assertEqual(log_entry['user_id'], user_id)
        self.assertEqual(log_entry['username'], username)
        self.assertIsNone(log_entry['error'])
        
        # 记录失败生成
        error_msg = "API Error"
        log_entry = self.security.log_generation(user_id, username, prompt, False, error_msg)
        self.assertFalse(log_entry['success'])
        self.assertEqual(log_entry['error'], error_msg)
        
        # 验证历史记录
        self.assertEqual(len(self.security.generation_history), 2)


class TestUserManager(unittest.TestCase):
    """测试用户管理器"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = os.path.join(self.temp_dir, "user_settings.json")
        
        # Mock Config.DATA_DIR to use temp directory
        with patch.object(Config, 'DATA_DIR', self.temp_dir):
            self.user_manager = UserManager(Config.SD_DEFAULT_PARAMS)
            
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    def test_default_settings(self):
        """测试默认用户设置"""
        user_id = "test_user"
        settings = self.user_manager.get_settings(user_id)
        
        self.assertEqual(settings['width'], Config.SD_DEFAULT_PARAMS['width'])
        self.assertEqual(settings['height'], Config.SD_DEFAULT_PARAMS['height'])
        self.assertEqual(settings['steps'], Config.SD_DEFAULT_PARAMS['steps'])
        
    def test_set_resolution(self):
        """测试设置分辨率"""
        user_id = "test_user"
        new_width, new_height = 512, 768
        
        self.user_manager.set_resolution(user_id, new_width, new_height)
        settings = self.user_manager.get_settings(user_id)
        
        self.assertEqual(settings['width'], new_width)
        self.assertEqual(settings['height'], new_height)
        
    def test_negative_prompt_management(self):
        """测试负面词管理"""
        user_id = "test_user"
        custom_negative = "custom negative prompt"
        
        # 设置自定义负面词
        self.user_manager.set_negative_prompt(user_id, custom_negative)
        settings = self.user_manager.get_settings(user_id)
        self.assertEqual(settings['negative_prompt'], custom_negative)
        
        # 重置为默认
        self.user_manager.reset_negative_prompt(user_id)
        settings = self.user_manager.get_settings(user_id)
        self.assertEqual(settings['negative_prompt'], Config.SD_DEFAULT_PARAMS['negative_prompt'])
        
    @patch('builtins.open', new_callable=mock_open, read_data='{"test_user": {"width": 512, "height": 512}}')
    @patch('os.path.exists')
    def test_load_settings(self, mock_exists, mock_file):
        """测试加载用户设置"""
        mock_exists.return_value = True
        
        with patch.object(Config, 'DATA_DIR', self.temp_dir):
            user_manager = UserManager(Config.SD_DEFAULT_PARAMS)
            
        # 验证设置已加载
        self.assertIn("test_user", user_manager.user_settings)
        
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_save_settings(self, mock_makedirs, mock_file):
        """测试保存用户设置"""
        user_id = "test_user"
        self.user_manager.get_settings(user_id)  # 创建用户设置
        
        self.user_manager.save_settings()
        
        # 验证文件写入被调用
        mock_file.assert_called()
        mock_makedirs.assert_called()


class TestFormManager(unittest.TestCase):
    """测试表单管理器"""
    
    def setUp(self):
        self.form_manager = FormManager()
        
    def test_form_initialization(self):
        """测试表单初始化"""
        user_id = "test_user"
        form_data = self.form_manager.get_user_form(user_id)
        
        self.assertIsInstance(form_data, dict)
        self.assertIn('prompt', form_data)
        self.assertIn('resolution', form_data)
        self.assertIn('seed', form_data)
        self.assertIn('hires_fix', form_data)
        
    def test_form_field_updates(self):
        """测试表单字段更新"""
        user_id = "test_user"
        
        # 更新prompt
        self.form_manager.update_form_field(user_id, 'prompt', 'test prompt')
        form_data = self.form_manager.get_user_form(user_id)
        self.assertEqual(form_data['prompt'], 'test prompt')
        
        # 更新分辨率
        self.form_manager.update_form_field(user_id, 'resolution', '512x512')
        form_data = self.form_manager.get_user_form(user_id)
        self.assertEqual(form_data['resolution'], '512x512')
        
        # 更新高清修复
        self.form_manager.update_form_field(user_id, 'hires_fix', True)
        form_data = self.form_manager.get_user_form(user_id)
        self.assertTrue(form_data['hires_fix'])
        
    def test_input_state_management(self):
        """测试输入状态管理"""
        user_id = "test_user"
        
        # 设置输入状态
        self.form_manager.set_input_state(user_id, 'prompt')
        self.assertEqual(self.form_manager.get_input_state(user_id), 'prompt')
        self.assertTrue(self.form_manager.is_waiting_for_input(user_id))
        
        # 清除输入状态
        self.form_manager.clear_input_state(user_id)
        self.assertIsNone(self.form_manager.get_input_state(user_id))
        self.assertFalse(self.form_manager.is_waiting_for_input(user_id))
        
    def test_seed_validation(self):
        """测试种子验证"""
        # 有效种子
        is_valid, seed_value, status = self.form_manager.validate_seed('123456')
        self.assertTrue(is_valid)
        self.assertEqual(seed_value, 123456)
        self.assertEqual(status, '有效')
        
        # 跳过种子
        is_valid, seed_value, status = self.form_manager.validate_seed('skip')
        self.assertTrue(is_valid)
        self.assertIsNone(seed_value)
        self.assertEqual(status, '已跳过')
        
        # 随机种子
        is_valid, seed_value, status = self.form_manager.validate_seed('random')
        self.assertTrue(is_valid)
        self.assertIsNone(seed_value)
        self.assertEqual(status, '随机')
        
        # 无效种子
        is_valid, seed_value, status = self.form_manager.validate_seed('invalid')
        self.assertFalse(is_valid)
        self.assertIsNone(seed_value)
        
        # 超出范围的种子
        is_valid, seed_value, status = self.form_manager.validate_seed('9999999999')
        self.assertFalse(is_valid)
        
    def test_form_summary_formatting(self):
        """测试表单摘要格式化"""
        user_id = "test_user"
        
        # 设置一些表单数据
        self.form_manager.update_form_field(user_id, 'prompt', 'test prompt')
        self.form_manager.update_form_field(user_id, 'resolution', '512x512')
        self.form_manager.update_form_field(user_id, 'seed', 123456)
        self.form_manager.update_form_field(user_id, 'hires_fix', True)
        
        summary = self.form_manager.format_form_summary(user_id)
        
        self.assertEqual(summary['prompt'], 'test prompt')
        self.assertEqual(summary['resolution'], '512x512')
        self.assertEqual(summary['seed'], '123456')
        self.assertEqual(summary['hires_fix'], '开启')
        
    def test_params_generation_from_form(self):
        """测试从表单生成参数"""
        user_id = "test_user"
        user_settings = Config.SD_DEFAULT_PARAMS.copy()
        
        # 设置表单数据
        self.form_manager.update_form_field(user_id, 'resolution', '512x768')
        self.form_manager.update_form_field(user_id, 'seed', 123456)
        self.form_manager.update_form_field(user_id, 'hires_fix', True)
        
        params = self.form_manager.generate_params_from_form(user_id, user_settings)
        
        self.assertEqual(params['width'], 512)
        self.assertEqual(params['height'], 768)
        self.assertEqual(params['seed'], 123456)
        self.assertTrue(params['enable_hr'])
        self.assertIn('hr_scale', params)
        
    def test_prompt_from_form(self):
        """测试从表单获取提示词"""
        user_id = "test_user"
        random_prompts = ['random1', 'random2', 'random3']
        
        # 未设置提示词时使用随机
        prompt = self.form_manager.get_prompt_from_form(user_id, random_prompts)
        self.assertIn(prompt, random_prompts)
        
        # 设置了提示词时使用设置的
        custom_prompt = 'custom prompt'
        self.form_manager.update_form_field(user_id, 'prompt', custom_prompt)
        prompt = self.form_manager.get_prompt_from_form(user_id, random_prompts)
        self.assertEqual(prompt, custom_prompt)
        
    def test_form_reset(self):
        """测试表单重置"""
        user_id = "test_user"
        
        # 设置一些数据
        self.form_manager.update_form_field(user_id, 'prompt', 'test')
        self.form_manager.update_form_field(user_id, 'resolution', '512x512')
        self.form_manager.set_input_state(user_id, 'prompt')
        
        # 重置表单
        self.form_manager.reset_user_form(user_id)
        
        form_data = self.form_manager.get_user_form(user_id)
        self.assertIsNone(form_data['prompt'])
        self.assertIsNone(form_data['resolution'])
        self.assertFalse(self.form_manager.is_waiting_for_input(user_id))


class TestSDController(unittest.IsolatedAsyncioTestCase):
    """测试Stable Diffusion控制器"""
    
    def setUp(self):
        self.sd_controller = StableDiffusionController()
        
    @patch('aiohttp.ClientSession.get')
    async def test_api_status_check_online(self, mock_get):
        """测试API状态检查 - 在线"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response
        
        status = await self.sd_controller.check_api_status()
        self.assertTrue(status)
        
    @patch('aiohttp.ClientSession.get')
    async def test_api_status_check_offline(self, mock_get):
        """测试API状态检查 - 离线"""
        mock_get.side_effect = Exception("Connection failed")
        
        status = await self.sd_controller.check_api_status()
        self.assertFalse(status)
        
    @patch('aiohttp.ClientSession.get')
    async def test_get_models(self, mock_get):
        """测试获取模型列表"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [
            {'title': 'model1.safetensors'},
            {'title': 'model2.ckpt'}
        ]
        mock_get.return_value.__aenter__.return_value = mock_response
        
        models = await self.sd_controller.get_models()
        self.assertEqual(len(models), 2)
        self.assertIn('model1.safetensors', models)
        self.assertIn('model2.ckpt', models)
        
    @patch('aiohttp.ClientSession.get')
    async def test_get_current_model(self, mock_get):
        """测试获取当前模型"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'sd_model_checkpoint': 'path/to/model.safetensors'
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        model = await self.sd_controller.get_current_model()
        self.assertEqual(model, 'model')
        
    @patch('aiohttp.ClientSession.get')
    async def test_get_progress(self, mock_get):
        """测试获取生成进度"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'progress': 0.5,
            'eta_relative': 10.5
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        progress, eta = await self.sd_controller.get_progress()
        self.assertEqual(progress, 0.5)
        self.assertEqual(eta, 10.5)
        
    @patch('aiohttp.ClientSession.post')
    async def test_generate_image_success(self, mock_post):
        """测试图片生成成功"""
        # 创建一个简单的测试图片
        img = Image.new('RGB', (64, 64), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        img_b64 = base64.b64encode(img_data).decode()
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'images': [img_b64],
            'info': '{"infotexts": ["test info"]}'
        }
        mock_post.return_value.__aenter__.return_value = mock_response
        
        success, result = await self.sd_controller.generate_image("test prompt")
        self.assertTrue(success)
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], io.BytesIO)
        self.assertIsInstance(result[1], dict)
        
    @patch('aiohttp.ClientSession.post')
    async def test_generate_image_failure(self, mock_post):
        """测试图片生成失败"""
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text.return_value = "API Error"
        mock_post.return_value.__aenter__.return_value = mock_response
        
        success, result = await self.sd_controller.generate_image("test prompt")
        self.assertFalse(success)
        self.assertIsInstance(result, str)
        self.assertIn("API错误", result)
        
    @patch('aiohttp.ClientSession.post')
    async def test_interrupt_generation(self, mock_post):
        """测试中断生成"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        success = await self.sd_controller.interrupt_generation()
        self.assertTrue(success)
        
    def test_save_result_locally(self):
        """测试保存结果到本地"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(Config, 'DATA_DIR', temp_dir):
                with patch.object(Config, 'LOCAL_SAVE_PATH', 'test_images'):
                    # 创建测试图片数据
                    img = Image.new('RGB', (64, 64), color='blue')
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_data = img_bytes.getvalue()
                    img_b64 = base64.b64encode(img_data).decode()
                    
                    test_result = {
                        'images': [img_b64],
                        'info': '{"infotexts": ["test parameters"]}'
                    }
                    
                    # 运行异步方法
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        filepath = loop.run_until_complete(
                            self.sd_controller.save_result_locally(test_result)
                        )
                        self.assertIsNotNone(filepath)
                        self.assertTrue(os.path.exists(filepath))
                        self.assertTrue(filepath.endswith('.png'))
                    finally:
                        loop.close()


class TestRequireAuthDecorator(unittest.TestCase):
    """测试认证装饰器"""
    
    def setUp(self):
        self.security = SecurityManager()
        self.security.authorized_users = ['123', '456']
        
    def test_require_auth_authorized_user(self):
        """测试授权用户通过认证"""
        
        @require_auth
        async def test_method(self, update, context):
            return "success"
            
        # Mock对象
        mock_self = Mock()
        mock_self.security = self.security
        
        mock_update = Mock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 123
        
        mock_context = Mock()
        
        # 运行测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                test_method(mock_self, mock_update, mock_context)
            )
            # 应该成功执行
        finally:
            loop.close()
            
    def test_require_auth_unauthorized_user(self):
        """测试未授权用户被拒绝"""
        
        @require_auth
        async def test_method(self, update, context):
            return "success"
            
        # Mock对象
        mock_self = Mock()
        mock_self.security = self.security
        
        mock_update = Mock()
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 999  # 未授权ID
        mock_update.callback_query = None
        mock_update.message = Mock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = Mock()
        
        # 运行测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                test_method(mock_self, mock_update, mock_context)
            )
            # 应该调用reply_text发送未授权消息
            mock_update.message.reply_text.assert_awaited_once_with("❌ 未授权访问")
        finally:
            loop.close()


class TestTextContent(unittest.TestCase):
    """测试文本内容"""
    
    def test_text_content_exists(self):
        """测试文本内容存在性"""
        self.assertTrue(hasattr(TextContent, 'WELCOME'))
        self.assertTrue(hasattr(TextContent, 'GENERATION_MENU'))
        self.assertTrue(hasattr(TextContent, 'RANDOM_PROMPTS'))
        self.assertIsInstance(TextContent.RANDOM_PROMPTS, list)
        self.assertTrue(len(TextContent.RANDOM_PROMPTS) > 0)
        
    def test_text_formatting(self):
        """测试文本格式化"""
        welcome_text = TextContent.WELCOME.format(
            username="test_user",
            status="online"
        )
        self.assertIn("test_user", welcome_text)
        self.assertIn("online", welcome_text)


# 运行测试的辅助函数
def run_async_test(test_func):
    """运行异步测试的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(test_func)
    finally:
        loop.close()


if __name__ == '__main__':
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestConfig,
        TestSecurityManager, 
        TestUserManager,
        TestFormManager,
        TestSDController,
        TestRequireAuthDecorator,
        TestTextContent
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestClass(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果统计
    print(f"\n{'='*50}")
    print(f"测试完成!")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    print(f"{'='*50}")