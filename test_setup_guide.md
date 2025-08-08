# Stable Diffusion Bot 测试指南

这是一个为 Stable Diffusion Telegram Bot 项目编写的全面测试套件。

## 📁 测试文件结构

```
tests/
├── test_unit.py           # 单元测试
├── test_integration.py    # 集成测试  
├── test_e2e.py           # 端到端测试
├── factories.py          # 测试数据工厂和Mock工具
├── conftest.py           # pytest配置和fixtures
└── __init__.py

reports/                  # 测试报告输出目录
├── test_summary.html     # 测试总览报告
├── unit_tests.html       # 单元测试报告
├── integration_tests.html # 集成测试报告
├── e2e_tests.html        # 端到端测试报告
└── coverage.xml          # 覆盖率XML报告

htmlcov/                  # HTML覆盖率报告
├── index.html            # 主覆盖率报告
├── unit/                 # 单元测试覆盖率
└── integration/          # 集成测试覆盖率

pytest.ini               # pytest配置文件
test_requirements.txt    # 测试依赖
run_tests.py            # 测试运行脚本
```

## 🚀 快速开始

### 1. 安装测试依赖

```bash
# 安装测试相关依赖
pip install -r test_requirements.txt

# 或者逐个安装主要依赖
pip install pytest pytest-asyncio pytest-cov pytest-mock aioresponses
```

### 2. 运行测试

```bash
# 运行所有测试
python run_tests.py --all

# 运行特定类型的测试
python run_tests.py --unit          # 单元测试
python run_tests.py --integration   # 集成测试
python run_tests.py --e2e           # 端到端测试

# 运行代码质量检查
python run_tests.py --quality

# 清理测试报告
python run_tests.py --clean
```

### 3. 使用原生pytest

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_unit.py -v

# 运行特定测试类
pytest tests/test_unit.py::TestSecurityManager -v

# 运行特定测试方法
pytest tests/test_unit.py::TestSecurityManager::test_authorization -v

# 运行带标记的测试
pytest -m unit          # 仅单元测试
pytest -m integration   # 仅集成测试
pytest -m slow          # 仅性能测试

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 📊 测试类型说明

### 单元测试 (Unit Tests)
- **文件**: `tests/test_unit.py`
- **目的**: 测试各个模块的独立功能
- **覆盖范围**: 
  - 配置管理 (Config)
  - 安全管理 (SecurityManager)
  - 用户管理 (UserManager)  
  - 表单管理 (FormManager)
  - SD控制器 (StableDiffusionController)
  - 文本内容 (TextContent)
  - 认证装饰器 (require_auth)

### 集成测试 (Integration Tests)
- **文件**: `tests/test_integration.py`
- **目的**: 测试模块间的交互和数据流
- **覆盖范围**:
  - Bot核心功能集成
  - 用户数据持久化
  - 安全管理集成
  - SD API交互
  - 性能测试

### 端到端测试 (E2E Tests)
- **文件**: `tests/test_e2e.py`  
- **目的**: 模拟真实用户操作，测试完整workflow
- **覆盖场景**:
  - 完整图片生成流程
  - 高级表单使用流程
  - 用户设置管理流程
  - 错误处理流程
  - 任务中断流程

## 🔧 测试工具和工厂

### 测试数据工厂 (factories.py)
提供标准化的测试数据生成：

```python
from factories import UserFactory, MessageFactory, ImageFactory

# 创建测试用户
user = UserFactory.create_authorized_user()
unauthorized_user = UserFactory.create_unauthorized_user()

# 创建测试消息  
message = MessageFactory.create_text_message("test prompt", user)
callback = MessageFactory.create_callback_query("main_menu", user)

# 创建测试图片
img_data = ImageFactory.create_test_image(512, 512, 'blue')
sd_response = ImageFactory.create_sd_response("anime girl")
```

### Mock工具
```python
from factories import MockHelper, AssertHelper

# 创建异步上下文管理器
async_cm = MockHelper.create_async_context_manager(mock_response)

# 断言Telegram消息
AssertHelper.assert_telegram_message_sent(mock_message, "期望文本")
AssertHelper.assert_callback_answered(mock_query)
```

## 📈 覆盖率报告

测试完成后会生成详细的覆盖率报告：

- **HTML报告**: `htmlcov/index.html` - 可视化覆盖率报告
- **XML报告**: `reports/coverage.xml` - CI/CD集成用
- **终端报告**: 直接在终端显示覆盖率摘要

目标覆盖率：
- 单元测试: > 90%
- 集成测试: > 80%  
- 整体覆盖率: > 85%

## 🔍 代码质量检查

### Black - 代码格式化
```bash
# 检查格式
black --check --diff .

# 自动格式化
black .
```

### Flake8 - 代码风格
```bash
# 检查代码风格
flake8 . --output-file=reports/flake8_report.txt
```

### MyPy - 类型检查
```bash  
# 类型注解检查
mypy . --html-report reports/mypy_report
```

### Bandit - 安全检查
```bash
# 安全漏洞扫描
bandit -r . -f json -o reports/security_report.json
```

## 🎯 最佳实践

### 1. 测试命名规范
```python
class TestSecurityManager:
    def test_authorization_with_valid_user(self):
        """测试有效用户的授权"""
        pass
        
    def test_authorization_with_invalid_user(self):
        """测试无效用户的授权"""  
        pass
```

### 2. 使用Fixtures
```python
@pytest.fixture
def security_manager():
    """SecurityManager实例fixture"""
    return SecurityManager()

def test_something(security_manager):
    # 使用fixture
    result = security_manager.is_authorized_user("123")
```

### 3. 异步测试
```python
@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await some_async_function()
    assert result is not None
```

### 4. Mock外部依赖
```python
@patch('aiohttp.ClientSession.get')
async def test_api_call(mock_get):
    """测试API调用"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_get.return_value.__aenter__.return_value = mock_response
    
    result = await api_function()
    assert result is True
```

### 5. 参数化测试
```python
@pytest.mark.parametrize("input_value,expected", [
    ("safe prompt", True),
    ("unsafe violence", False),
    ("" * 600, False),  # 过长
])
def test_prompt_safety(input_value, expected):
    """参数化测试提示词安全性"""
    result, _ = security.is_safe_prompt(input_value) 
    assert result == expected
```

## 🚨 常见问题

### Q1: 测试运行缓慢
A: 使用并行测试：`python run_tests.py --all --parallel`

### Q2: 异步测试失败
A: 确保安装了 `pytest-asyncio` 并使用 `@pytest.mark.asyncio` 装饰器

### Q3: 覆盖率不准确  
A: 确保测试运行时包含所有相关文件路径

### Q4: Mock不生效
A: 检查导入路径是否正确，确保patch的是实际使用的模块

## 🔄 CI/CD集成

### GitHub Actions示例
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r test_requirements.txt
        
    - name: Run tests
      run: python run_tests.py --all --quiet
      
    - name: Upload coverage
      uses: codecov/codecov-action@v1
      with:
        file: ./reports/coverage.xml
```

## 📚 进阶用法

### 自定义测试标记
```python
# 在pytest.ini中定义
markers = 
    api: API相关测试
    database: 数据库测试  
    slow: 慢速测试

# 在测试中使用
@pytest.mark.api
def test_api_endpoint():
    pass

# 运行特定标记的测试
pytest -m api
```

### 测试数据参数化
```python
@pytest.fixture(params=['test1', 'test2', 'test3'])
def test_data(request):
    return request.param

def test_with_multiple_data(test_data):
    # 会用每个参数运行一次
    assert process_data(test_data) is not None
```

### 跳过测试
```python
@pytest.mark.skip(reason="功能暂未实现")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.version_info < (3, 8), reason="需要Python 3.8+")
def test_new_feature():
    pass
```

## 📞 支持

如果你在运行测试时遇到问题：

1. 检查依赖是否正确安装
2. 确保Python版本兼容 (>=3.8)  
3. 查看测试报告中的详细错误信息
4. 参考本文档的最佳实践部分

更多pytest使用方法，请参考 [pytest官方文档](https://docs.pytest.org/)。