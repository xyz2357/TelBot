# security.py
import time
from functools import wraps
from config import Config

class SecurityManager:
    def __init__(self):
        self.generation_history = []
        self.rate_limits = {}
        self.active_tasks = {}  # 跟踪活跃任务
    
    def is_authorized_user(self, user_id):
        """检查用户是否被授权"""
        return user_id in Config.AUTHORIZED_USERS
    
    def is_safe_prompt(self, prompt):
        """检查提示词是否安全"""
        prompt_lower = prompt.lower()
        
        # 检查提示词长度
        if len(prompt) > Config.MAX_PROMPT_LENGTH:
            return False, "提示词过长"
        
        # 检查是否包含不当内容
        unsafe_keywords = [
            'nude', 'naked', 'nsfw', 'sexual', 'porn', 'explicit',
            'violence', 'gore', 'blood', 'kill', 'death'
        ]
        
        for keyword in unsafe_keywords:
            if keyword in prompt_lower:
                return False, f"包含不当内容: {keyword}"
        
        return True, "安全"
    
    def check_generation_limit(self, user_id, limit=3, window=300):
        """检查用户生图频率限制 (5分钟内最多3张)"""
        now = time.time()
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        
        # 清理过期记录
        self.rate_limits[user_id] = [
            timestamp for timestamp in self.rate_limits[user_id]
            if now - timestamp < window
        ]
        
        if len(self.rate_limits[user_id]) >= limit:
            return False, f"生图频率过高，请等待{window//60}分钟"
        
        return True, "通过"
    
    def add_generation_record(self, user_id):
        """添加生图记录"""
        now = time.time()
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = []
        self.rate_limits[user_id].append(now)
    
    def get_queue_size(self):
        """获取当前队列大小"""
        return len([task for task in self.active_tasks.values() if not task.get('completed', False)])
    
    def add_task(self, task_id, user_id, prompt):
        """添加任务到队列"""
        self.active_tasks[task_id] = {
            'user_id': user_id,
            'prompt': prompt,
            'start_time': time.time(),
            'completed': False
        }
    
    def complete_task(self, task_id, result=None):
        """标记任务完成"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['completed'] = True
            self.active_tasks[task_id]['end_time'] = time.time()
            self.active_tasks[task_id]['result'] = result
    
    def log_generation(self, user_id, username, prompt, success, error=None):
        """记录生图日志"""
        log_entry = {
            'timestamp': time.time(),
            'user_id': user_id,
            'username': username,
            'prompt': prompt[:100] + '...' if len(prompt) > 100 else prompt,
            'success': success,
            'error': error
        }
        self.generation_history.append(log_entry)
        
        # 保持最近50条记录
        if len(self.generation_history) > 50:
            self.generation_history = self.generation_history[-50:]

def require_auth(func):
    """认证装饰器"""
    @wraps(func)
    async def wrapper(self, update, context):
        user_id = update.effective_user.id
        if not self.security.is_authorized_user(user_id):
            await update.message.reply_text("❌ 未授权访问")
            return
        return await func(self, update, context)
    return wrapper