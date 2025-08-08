# tests/test_e2e.py
"""
端到端测试
模拟真实用户操作流程，测试整个系统的集成
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from .factories import (
    UserFactory, MessageFactory, UpdateFactory, ImageFactory,
    PromptFactory, ConfigFactory, SDAPIFactory, MockHelper, AssertHelper
)
from bot import TelegramBot
from config import Config


@pytest.mark.e2e
class TestCompleteGenerationWorkflow:
    """完整图片生成工作流程测试"""
    
    @pytest.fixture
    async def setup_bot(self):
        """设置Bot测试环境"""
        temp_dir = tempfile.mkdtemp()
        
        with patch.object(Config, 'DATA_DIR', temp_dir), \
             patch.object(Config, 'BOT_TOKEN', 'test_token'), \
             patch.object(Config, 'AUTHORIZED_USERS', ['123', '456']), \
             patch('bot.Application') as mock_app:
            
            bot = TelegramBot()
            yield bot, temp_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_complete_text_to_image_workflow(self, setup_bot):
        """测试完整的文生图工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        
        # 1. 用户发送 /start 命令
        start_update = UpdateFactory.create_message_update("/start", user)
        
        with patch.object(bot.sd_controller, 'check_api_status', return_value=True):
            await bot.start(start_update, Mock())
        
        AssertHelper.assert_telegram_message_sent(
            start_update.message, 
            expected_text_contains="User123"
        )
        
        # 2. 用户点击生成图片按钮
        txt2img_update = UpdateFactory.create_callback_update("txt2img", user)
        await bot.handle_callback(txt2img_update, Mock())
        
        AssertHelper.assert_callback_answered(txt2img_update.callback_query)
        AssertHelper.assert_message_edited(
            txt2img_update.callback_query,
            expected_text_contains="图片生成选项"
        )
        
        # 3. 用户选择输入提示词
        input_update = UpdateFactory.create_callback_update("input_prompt", user)
        await bot.handle_callback(input_update, Mock())
        
        AssertHelper.assert_message_edited(
            input_update.callback_query,
            expected_text_contains="请输入你的提示词"
        )
        
        # 4. 用户发送提示词
        prompt = PromptFactory.random_safe_prompt()
        prompt_update = UpdateFactory.create_message_update(prompt, user)
        
        # Mock SD API响应
        sd_response = ImageFactory.create_sd_response(prompt)
        img_bytes = ImageFactory.create_test_image()
        mock_result = (MockHelper.create_file_mock(img_bytes), sd_response)
        
        with patch.object(bot.sd_controller, 'generate_image', return_value=(True, mock_result)), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            
            await bot.handle_text_prompt(prompt_update, Mock())
        
        # 验证图片被发送
        AssertHelper.assert_telegram_photo_sent(prompt_update.message)
        
        # 5. 用户点赞图片
        # 这里需要从bot的task_results中获取task_id
        task_ids = list(bot.task_results.keys())
        assert len(task_ids) > 0
        
        task_id = task_ids[0]
        like_update = UpdateFactory.create_callback_update(f"like_{task_id}", user)
        
        with patch.object(bot.sd_controller, 'save_result_locally', return_value="/path/to/saved.png"):
            await bot.handle_callback(like_update, Mock())
        
        AssertHelper.assert_callback_answered(like_update.callback_query)
    
    @pytest.mark.asyncio
    async def test_form_generation_workflow(self, setup_bot):
        """测试高级表单生成工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        user_id = str(user.id)
        
        # 1. 打开高级表单
        form_update = UpdateFactory.create_callback_update("advanced_form", user)
        await bot.handle_callback(form_update, Mock())
        
        AssertHelper.assert_message_edited(
            form_update.callback_query,
            expected_text_contains="高级生成表单"
        )
        
        # 2. 设置提示词
        prompt_update = UpdateFactory.create_callback_update("form_set_prompt", user)
        await bot.handle_callback(prompt_update, Mock())
        
        # 验证进入输入状态
        assert bot.form_manager.is_waiting_for_input(user_id)
        
        # 3. 输入提示词
        prompt_text = "beautiful anime girl with long hair"
        text_update = UpdateFactory.create_message_update(prompt_text, user)
        await bot.handle_text_prompt(text_update, Mock())
        
        # 验证提示词被设置
        AssertHelper.assert_form_field_set(
            bot.form_manager, user_id, 'prompt', prompt_text
        )
        assert not bot.form_manager.is_waiting_for_input(user_id)
        
        # 4. 设置分辨率
        resolution_menu_update = UpdateFactory.create_callback_update("form_set_resolution_menu", user)
        await bot.handle_callback(resolution_menu_update, Mock())
        
        resolution_update = UpdateFactory.create_callback_update("form_set_resolution_512_768", user)
        await bot.handle_callback(resolution_update, Mock())
        
        # 验证分辨率被设置
        AssertHelper.assert_form_field_set(
            bot.form_manager, user_id, 'resolution', "512x768"
        )
        
        # 5. 启用高清修复
        hires_update = UpdateFactory.create_callback_update("form_toggle_hires", user)
        await bot.handle_callback(hires_update, Mock())
        
        # 验证高清修复被启用
        AssertHelper.assert_form_field_set(
            bot.form_manager, user_id, 'hires_fix', True
        )
        
        # 6. 生成图片
        generate_update = UpdateFactory.create_callback_update("form_generate", user)
        
        # Mock SD API响应（带高清修复）
        sd_response = ImageFactory.create_sd_response(prompt_text, 512, 768)
        img_bytes = ImageFactory.create_test_image(512, 768)
        mock_result = (MockHelper.create_file_mock(img_bytes), sd_response)
        
        with patch.object(bot.sd_controller, 'generate_image', return_value=(True, mock_result)), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            
            await bot.handle_callback(generate_update, Mock())
        
        # 验证生成参数包含高清修复设置
        # 这需要检查sd_controller.generate_image的调用参数
        bot.sd_controller.generate_image.assert_called_once()
        call_args = bot.sd_controller.generate_image.call_args
        assert call_args[1]['enable_hr'] == True
        assert call_args[1]['width'] == 512
        assert call_args[1]['height'] == 768
    
    @pytest.mark.asyncio
    async def test_regeneration_workflow(self, setup_bot):
        """测试重新生成工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        
        # 1. 首次生成
        prompt = PromptFactory.random_safe_prompt()
        first_update = UpdateFactory.create_message_update(prompt, user)
        
        sd_response = ImageFactory.create_sd_response(prompt)
        img_bytes = ImageFactory.create_test_image()
        mock_result = (MockHelper.create_file_mock(img_bytes), sd_response)
        
        with patch.object(bot.sd_controller, 'generate_image', return_value=(True, mock_result)), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            
            await bot.handle_text_prompt(first_update, Mock())
        
        # 验证last_prompt被设置
        assert bot.last_prompt == prompt
        
        # 2. 使用数字重新生成（生成3次）
        regen_update = UpdateFactory.create_message_update("3", user)
        
        with patch.object(bot.sd_controller, 'generate_image', return_value=(True, mock_result)), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            
            await bot.handle_text_prompt(regen_update, Mock())
        
        # 验证generate_image被调用了3次
        assert bot.sd_controller.generate_image.call_count == 4  # 1次原始 + 3次重新生成
        
        # 3. 使用/re命令重新生成
        re_update = UpdateFactory.create_message_update("/re", user)
        
        with patch.object(bot.sd_controller, 'generate_image', return_value=(True, mock_result)), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            
            await bot.regenerate_image_with_last_prompt_task(re_update, Mock())
        
        # 验证又生成了一次
        assert bot.sd_controller.generate_image.call_count == 5
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, setup_bot):
        """测试错误处理工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        
        # 1. SD API离线
        prompt_update = UpdateFactory.create_message_update("test prompt", user)
        
        with patch.object(bot.sd_controller, 'generate_image', return_value=(False, "Connection failed")), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.0, 0.0)):
            
            await bot.handle_text_prompt(prompt_update, Mock())
        
        # 验证错误消息被发送
        # 这里需要检查进度消息被编辑为错误信息
        
        # 2. 不安全的提示词
        unsafe_prompt = PromptFactory.random_unsafe_prompt()
        unsafe_update = UpdateFactory.create_message_update(unsafe_prompt, user)
        
        await bot.handle_text_prompt(unsafe_update, Mock())
        
        AssertHelper.assert_telegram_message_sent(
            unsafe_update.message,
            expected_text_contains="不安全"
        )
        
        # 3. 未授权用户
        unauth_user = UserFactory.create_unauthorized_user()
        unauth_update = UpdateFactory.create_message_update("test prompt", unauth_user)
        
        await bot.handle_text_prompt(unauth_update, Mock())
        
        AssertHelper.assert_telegram_message_sent(
            unauth_update.message,
            expected_text_contains="未授权"
        )


@pytest.mark.e2e
class TestUserSettingsWorkflow:
    """用户设置工作流程测试"""
    
    @pytest.fixture
    async def setup_bot(self):
        temp_dir = tempfile.mkdtemp()
        with patch.object(Config, 'DATA_DIR', temp_dir), \
             patch.object(Config, 'AUTHORIZED_USERS', ['123']), \
             patch('bot.Application'):
            bot = TelegramBot()
            yield bot, temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_resolution_settings_workflow(self, setup_bot):
        """测试分辨率设置工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        user_id = str(user.id)
        
        # 1. 打开分辨率设置
        settings_update = UpdateFactory.create_callback_update("resolution_settings", user)
        await bot.handle_callback(settings_update, Mock())
        
        AssertHelper.assert_message_edited(
            settings_update.callback_query,
            expected_text_contains="分辨率设置"
        )
        
        # 2. 选择新分辨率
        resolution_update = UpdateFactory.create_callback_update("set_resolution_512_768", user)
        await bot.handle_callback(resolution_update, Mock())
        
        # 验证分辨率被更新
        AssertHelper.assert_user_settings_updated(
            bot.user_manager, user_id, width=512, height=768
        )
        
        # 3. 验证设置被持久化
        # 创建新的user_manager实例来验证持久化
        with patch.object(Config, 'DATA_DIR', temp_dir):
            new_user_manager = bot.user_manager.__class__(Config.SD_DEFAULT_PARAMS)
            settings = new_user_manager.get_settings(user_id)
            assert settings['width'] == 512
            assert settings['height'] == 768
    
    @pytest.mark.asyncio
    async def test_negative_prompt_settings_workflow(self, setup_bot):
        """测试负面词设置工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        user_id = str(user.id)
        
        # 1. 打开负面词设置
        settings_update = UpdateFactory.create_callback_update("negative_prompt_settings", user)
        await bot.handle_callback(settings_update, Mock())
        
        AssertHelper.assert_message_edited(
            settings_update.callback_query,
            expected_text_contains="负面词设置"
        )
        
        # 2. 选择自定义负面词
        custom_update = UpdateFactory.create_callback_update("set_negative_prompt", user)
        await bot.handle_callback(custom_update, Mock())
        
        # 验证进入等待状态
        assert user_id in bot.waiting_for_negative_prompt
        
        # 3. 输入自定义负面词
        custom_negative = "custom negative prompt, bad quality"
        text_update = UpdateFactory.create_message_update(custom_negative, user)
        await bot.handle_text_prompt(text_update, Mock())
        
        # 验证负面词被设置
        AssertHelper.assert_user_settings_updated(
            bot.user_manager, user_id, negative_prompt=custom_negative
        )
        assert user_id not in bot.waiting_for_negative_prompt
        
        # 4. 重置负面词
        reset_update = UpdateFactory.create_callback_update("reset_negative_prompt", user)
        await bot.handle_callback(reset_update, Mock())
        
        # 验证重置为默认值
        settings = bot.user_manager.get_settings(user_id)
        assert settings['negative_prompt'] == Config.SD_DEFAULT_PARAMS['negative_prompt']


@pytest.mark.e2e
class TestStatusAndHistoryWorkflow:
    """状态和历史记录工作流程测试"""
    
    @pytest.fixture
    async def setup_bot(self):
        temp_dir = tempfile.mkdtemp()
        with patch.object(Config, 'DATA_DIR', temp_dir), \
             patch.object(Config, 'AUTHORIZED_USERS', ['123']), \
             patch('bot.Application'):
            bot = TelegramBot()
            yield bot, temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_sd_status_workflow(self, setup_bot):
        """测试SD状态查看工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        
        # Mock SD API响应
        models_response = SDAPIFactory.create_models_response()
        samplers_response = SDAPIFactory.create_samplers_response()
        progress_response = SDAPIFactory.create_progress_response()
        
        status_update = UpdateFactory.create_callback_update("sd_status", user)
        
        with patch.object(bot.sd_controller, 'check_api_status', return_value=True), \
             patch.object(bot.sd_controller, 'get_models', return_value=[m['title'] for m in models_response]), \
             patch.object(bot.sd_controller, 'get_samplers', return_value=[s['name'] for s in samplers_response]), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.5, 10.5)), \
             patch.object(bot.sd_controller, 'get_current_model', return_value='model1'):
            
            await bot.handle_callback(status_update, Mock())
        
        AssertHelper.assert_message_edited(
            status_update.callback_query,
            expected_text_contains="在线"
        )
    
    @pytest.mark.asyncio
    async def test_generation_history_workflow(self, setup_bot):
        """测试生成历史查看工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        user_id = str(user.id)
        username = user.username
        
        # 添加一些历史记录
        bot.security.log_generation(user_id, username, "prompt 1", True)
        bot.security.log_generation(user_id, username, "prompt 2", False, "API Error")
        bot.security.log_generation(user_id, username, "prompt 3", True)
        
        history_update = UpdateFactory.create_callback_update("generation_history", user)
        await bot.handle_callback(history_update, Mock())
        
        AssertHelper.assert_message_edited(
            history_update.callback_query,
            expected_text_contains="最近生成历史"
        )
        
        # 验证历史记录内容
        call_args = history_update.callback_query.edit_message_text.call_args
        history_text = call_args[0][0]
        assert "prompt 1" in history_text
        assert "prompt 2" in history_text  
        assert "prompt 3" in history_text
        assert "API Error" in history_text


@pytest.mark.e2e
class TestTaskInterruptionWorkflow:
    """任务中断工作流程测试"""
    
    @pytest.fixture
    async def setup_bot(self):
        temp_dir = tempfile.mkdtemp()
        with patch.object(Config, 'DATA_DIR', temp_dir), \
             patch.object(Config, 'AUTHORIZED_USERS', ['123']), \
             patch('bot.Application'):
            bot = TelegramBot()
            yield bot, temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_task_interruption_workflow(self, setup_bot):
        """测试任务中断工作流程"""
        bot, temp_dir = setup_bot
        user = UserFactory.create_authorized_user()
        
        # 1. 开始生成任务
        prompt_update = UpdateFactory.create_message_update("test prompt", user)
        
        # Mock一个长时间运行的任务
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟慢速生成
            return True, (MockHelper.create_file_mock(b"test"), {"info": "test"})
        
        # 2. 获取任务ID（从进度消息的回调中）
        with patch.object(bot.sd_controller, 'generate_image', side_effect=slow_generate), \
             patch.object(bot.sd_controller, 'get_progress', return_value=(0.3, 5.0)):
            
            # 启动生成任务
            task = asyncio.create_task(bot.handle_text_prompt(prompt_update, Mock()))
            
            # 等待一小段时间让任务开始
            await asyncio.sleep(0.05)
            
            # 获取活动任务ID
            task_ids = list(bot.security.active_tasks.keys())
            assert len(task_ids) > 0
            task_id = task_ids[0]
            
            # 3. 中断任务
            interrupt_update = UpdateFactory.create_callback_update(f"interrupt_{task_id}", user)
            
            with patch.object(bot.sd_controller, 'interrupt_generation', return_value=True):
                await bot.handle_callback(interrupt_update, Mock())
            
            AssertHelper.assert_message_edited(
                interrupt_update.callback_query,
                expected_text_contains="已中断"
            )
            
            # 等待原始任务完成
            await task


if __name__ == '__main__':
    # 运行端到端测试
    pytest.main([
        __file__,
        '-v',
        '-m', 'e2e',
        '--tb=short',
        '--asyncio-mode=auto'
    ])