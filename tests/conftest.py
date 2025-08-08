# tests/conftest.py
"""
pytest配置文件
提供全局fixtures和测试配置
"""

import pytest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Generator, Any, Dict

# 导入测试工厂
from .factories import (
    UserFactory, MessageFactory, UpdateFactory, 
    ConfigFactory, ImageFactory, SDAPIFactory
)


# ==================== 异步测试配置 ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于整个测试会话"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 临时环境配置 ====================

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """临时目录fixture"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_config(temp_dir: str) -> Generator[Dict[str, Any], None, None]:
    """Mock配置fixture"""
    test_config = ConfigFactory.create_test_config()
    
    with patch.dict(os.environ, {
        'BOT_TOKEN': test_config['BOT_TOKEN'],
        'AUTHORIZED_USERS': ','.join(test_config['AUTHORIZED_USERS']),
        'SD_API_URL': test_config['SD_API_URL'],
        'DATA_DIR': temp_dir
    }):
        # 重新加载config模块以应用环境变量
        from config import Config
        original_data_dir = Config.DATA_DIR
        Config.DATA_DIR = temp_dir
        
        yield test_config
        
        # 恢复原始配置
        Config.DATA_DIR = original_data_dir


# ==================== 用户和消息fixtures ====================

@pytest.fixture
def authorized_user() -> Mock:
    """授权用户fixture"""
    return UserFactory.create_authorized_user()


@pytest.fixture
def unauthorized_user() -> Mock:
    """未授权用户fixture"""
    return UserFactory.create_unauthorized_user()


@pytest.fixture
def test_message(authorized_user: Mock) -> Mock:
    """测试消息fixture"""
    return MessageFactory.create_text_message("test message", authorized_user)


@pytest.fixture
def test_callback_query(authorized_user: Mock) -> Mock:
    """测试回调查询fixture"""
    return MessageFactory.create_callback_query("test_callback", authorized_user)


@pytest.fixture
def message_update(authorized_user: Mock) -> Mock:
    """消息更新fixture"""
    return UpdateFactory.create_message_update("test prompt", authorized_user)


@pytest.fixture
def callback_update(authorized_user: Mock) -> Mock:
    """回调更新fixture"""
    return UpdateFactory.create_callback_update("main_menu", authorized_user)


# ==================== 组件fixtures ====================

@pytest.fixture
def security_manager():
    """安全管理器fixture"""
    from security import SecurityManager
    manager = SecurityManager()
    manager.authorized_users = ['123', '456']  # 设置测试用户
    return manager


@pytest.fixture
def user_manager(mock_config: Dict[str, Any]):
    """用户管理器fixture"""
    from user_manager import UserManager
    from config import Config
    return UserManager(Config.SD_DEFAULT_PARAMS)


@pytest.fixture
def form_manager():
    """表单管理器fixture"""
    from form_manager import FormManager
    return FormManager()


@pytest.fixture
def sd_controller():
    """SD控制器fixture"""
    from sd_controller import StableDiffusionController
    return StableDiffusionController()


# ==================== Bot fixtures ====================

@pytest.fixture
def bot_instance(mock_config: Dict[str, Any]):
    """Bot实例fixture"""
    with patch('bot.Application') as mock_app:
        from bot import TelegramBot
        bot = TelegramBot()
        yield bot


# ==================== Mock API响应fixtures ====================

@pytest.fixture
def mock_sd_success_response():
    """成功的SD API响应fixture"""
    return ImageFactory.create_sd_response("test prompt")


@pytest.fixture
def mock_sd_models_response():
    """SD模型列表响应fixture"""
    return SDAPIFactory.create_models_response()


@pytest.fixture
def mock_sd_samplers_response():
    """SD采样器列表响应fixture"""
    return SDAPIFactory.create_samplers_response()


@pytest.fixture
def mock_sd_progress_response():
    """SD进度响应fixture"""
    return SDAPIFactory.create_progress_response(0.5, 10.0)


# ==================== HTTP Mock fixtures ====================

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session"""
    with patch('aiohttp.ClientSession') as mock_session:
        yield mock_session


@pytest.fixture
def mock_successful_api_call(mock_aiohttp_session):
    """成功的API调用Mock"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"status": "success"}
    mock_aiohttp_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
    mock_aiohttp_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
    return mock_response


@pytest.fixture
def mock_failed_api_call(mock_aiohttp_session):
    """失败的API调用Mock"""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_aiohttp_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
    mock_aiohttp_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
    return mock_response


# ==================== 数据库和文件Mock fixtures ====================

@pytest.fixture
def mock_file_operations():
    """Mock文件操作"""
    mock_data = {}
    
    def mock_open_func(filename, mode='r', *args, **kwargs):
        mock_file = Mock()
        if 'r' in mode:
            mock_file.read.return_value = mock_data.get(filename, '{}')
            mock_file.__enter__.return_value = mock_file
        elif 'w' in mode:
            def write_func(content):
                mock_data[filename] = content
            mock_file.write = write_func
            mock_file.__enter__.return_value = mock_file
        return mock_file
    
    with patch('builtins.open', side_effect=mock_open_func), \
         patch('os.path.exists', return_value=True), \
         patch('os.makedirs'), \
         patch('shutil.rmtree'):
        yield mock_data


# ==================== 测试标记配置 ====================

def pytest_configure(config):
    """pytest配置函数"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "unit: 单元测试标记"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记"
    )
    config.addinivalue_line(
        "markers", "e2e: 端到端测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记"
    )
    config.addinivalue_line(
        "markers", "api: API测试标记"
    )
    config.addinivalue_line(
        "markers", "security: 安全测试标记"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    # 为测试文件自动添加标记
    for item in items:
        # 根据文件名添加标记
        if "test_unit" in item.fspath.basename:
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        elif "test_e2e" in item.fspath.basename:
            item.add_marker(pytest.mark.e2e)
        
        # 根据测试名称添加标记
        if "performance" in item.name or "slow" in item.name:
            item.add_marker(pytest.mark.slow)
        
        if "api" in item.name:
            item.add_marker(pytest.mark.api)
            
        if "security" in item.name or "auth" in item.name:
            item.add_marker(pytest.mark.security)


# ==================== 测试会话钩子 ====================

@pytest.fixture(scope="session", autouse=True)
def setup_test_session():
    """测试会话设置"""
    print("\n🚀 开始测试会话...")
    
    # 设置测试环境变量
    os.environ.setdefault('PYTEST_RUNNING', '1')
    
    yield
    
    print("\n✅ 测试会话完成!")


@pytest.fixture(autouse=True)
def setup_test_isolation():
    """测试隔离设置 - 每个测试前后运行"""
    # 测试前设置
    original_env = os.environ.copy()
    
    yield
    
    # 测试后清理
    os.environ.clear()
    os.environ.update(original_env)


# ==================== 参数化数据fixtures ====================

@pytest.fixture(params=[
    "a beautiful landscape",
    "cute cat sitting on a chair", 
    "anime girl with blue hair",
    "peaceful forest scene"
])
def safe_prompts(request):
    """安全提示词参数化fixture"""
    return request.param


@pytest.fixture(params=[
    "violence and blood",
    "gore scene with death",
    "kill the enemy"
])
def unsafe_prompts(request):
    """不安全提示词参数化fixture"""
    return request.param


@pytest.fixture(params=[
    (512, 512),
    (768, 512), 
    (512, 768),
    (1024, 1024)
])
def test_resolutions(request):
    """测试分辨率参数化fixture"""
    return request.param


# ==================== 错误模拟fixtures ====================

@pytest.fixture
def network_error():
    """网络错误Mock"""
    return ConnectionError("Network connection failed")


@pytest.fixture  
def timeout_error():
    """超时错误Mock"""
    return asyncio.TimeoutError("Request timed out")


@pytest.fixture
def api_error():
    """API错误Mock"""
    error_response = Mock()
    error_response.status = 500
    error_response.text.return_value = "Internal Server Error"
    return error_response


# ==================== 性能测试fixtures ====================

@pytest.fixture
def performance_timer():
    """性能计时器fixture"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
            
        def assert_faster_than(self, seconds):
            assert self.elapsed is not None, "Timer not used properly"
            assert self.elapsed < seconds, f"Operation took {self.elapsed}s, expected < {seconds}s"
    
    return Timer()


# ==================== 日志配置 ====================

@pytest.fixture(autouse=True)
def configure_test_logging():
    """配置测试日志"""
    import logging
    
    # 设置测试期间的日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    # 可以在这里添加测试专用的日志处理器
    yield


# ==================== 资源清理fixtures ====================

@pytest.fixture
def cleanup_tasks():
    """清理异步任务fixture"""
    tasks = []
    
    def add_task(task):
        tasks.append(task)
        return task
    
    yield add_task
    
    # 清理所有任务
    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(task)
            except asyncio.CancelledError:
                pass


# ==================== 测试数据预设 ====================

@pytest.fixture
def sample_user_settings():
    """示例用户设置"""
    return ConfigFactory.create_user_settings(width=512, height=768)


@pytest.fixture
def sample_form_data():
    """示例表单数据"""
    from factories import FormDataFactory
    return FormDataFactory.create_filled_form()


@pytest.fixture
def sample_task_data():
    """示例任务数据"""
    from factories import TaskFactory
    return TaskFactory.create_task_data("123", "test prompt")


# ==================== 断言助手 ====================

@pytest.fixture
def assert_helper():
    """断言助手fixture"""
    from factories import AssertHelper
    return AssertHelper