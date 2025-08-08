from typing import Dict, Optional, Union, List, Any, Tuple
from config import FormData, Config, UserSettings
import random

class FormManager:
    """管理用户表单数据"""
    
    def __init__(self):
        self.user_forms: Dict[str, FormData] = {}
        self.form_input_states: Dict[str, str] = {}  # 跟踪用户当前的输入状态
    
    def get_user_form(self, user_id: str) -> FormData:
        """获取用户的表单数据"""
        if user_id not in self.user_forms:
            self.user_forms[user_id] = Config.DEFAULT_FORM_DATA.copy()
        return self.user_forms[user_id]
    
    def reset_user_form(self, user_id: str) -> None:
        """重置用户表单"""
        self.user_forms[user_id] = Config.DEFAULT_FORM_DATA.copy()
        self.clear_input_state(user_id)
    
    def update_form_field(self, user_id: str, field: str, value: Union[str, int, bool, None]) -> None:
        """更新表单字段"""
        form_data = self.get_user_form(user_id)
        form_data[field] = value
    
    def set_input_state(self, user_id: str, state: str) -> None:
        """设置用户的输入状态"""
        self.form_input_states[user_id] = state
    
    def get_input_state(self, user_id: str) -> Optional[str]:
        """获取用户的输入状态"""
        return self.form_input_states.get(user_id)
    
    def clear_input_state(self, user_id: str) -> None:
        """清除用户的输入状态"""
        if user_id in self.form_input_states:
            del self.form_input_states[user_id]
    
    def is_waiting_for_input(self, user_id: str) -> bool:
        """检查用户是否在等待输入"""
        return user_id in self.form_input_states
    
    def format_form_summary(self, user_id: str) -> Dict[str, str]:
        """格式化表单摘要显示"""
        form_data = self.get_user_form(user_id)
        
        prompt_display = form_data.get('prompt') or "未设置 (将使用随机)"
        if prompt_display != "未设置 (将使用随机)" and len(prompt_display) > 30:
            prompt_display = prompt_display[:30] + "..."
            
        resolution_display = form_data.get('resolution') or "未设置 (使用默认)"
        seed_display = str(form_data.get('seed')) if form_data.get('seed') is not None else "随机"
        hires_display = "开启" if form_data.get('hires_fix') else "关闭"
        
        return {
            'prompt': prompt_display,
            'resolution': resolution_display, 
            'seed': seed_display,
            'hires_fix': hires_display
        }
    
    def validate_seed(self, seed_text: str) -> Tuple[bool, Optional[int], str]:
        """验证种子输入"""
        seed_text = seed_text.strip().lower()
        
        if seed_text == 'skip':
            return True, None, "已跳过"
        elif seed_text == 'random':
            return True, None, "随机"
        else:
            try:
                seed = int(seed_text)
                if 0 <= seed <= 4294967295:
                    return True, seed, "有效"
                else:
                    return False, None, "种子超出范围 (0-4294967295)"
            except ValueError:
                return False, None, "无效格式"
    
    def generate_params_from_form(self, user_id: str, user_settings: UserSettings) -> Dict[str, Any]:
        """从表单生成API参数"""
        form_data = self.get_user_form(user_id)
        params: Dict[str, Any] = dict(user_settings)
        
        # 处理分辨率
        if form_data.get('resolution'):
            try:
                width, height = form_data['resolution'].split('x')
                params['width'] = int(width)
                params['height'] = int(height)
            except ValueError:
                pass  # 使用默认分辨率
        
        # 处理种子
        if form_data.get('seed') is not None:
            params['seed'] = form_data['seed']
        else:
            # 生成随机种子
            params['seed'] = random.randint(0, 4294967295)
        
        # 高清修复参数映射
        if form_data.get('hires_fix'):
            h = Config.HIRES_DEFAULTS
            params['enable_hr'] = True
            params['hr_scale'] = h['hr_scale']
            params['hr_upscaler'] = h['hr_upscaler']
            # 避免 None 值导致 WebUI 后端比较报错
            params['denoising_strength'] = h['denoising_strength']
            # 二次采样步数：基于比例计算，至少 1
            total_steps = int(params.get('steps', 20) or 20)
            params['hr_second_pass_steps'] = max(1, int(total_steps * h['hr_second_pass_ratio']))
            # 不使用像素尺寸重设时明确给 0
            params['hr_resize_x'] = h['hr_resize_x']
            params['hr_resize_y'] = h['hr_resize_y']
        
        return params
    
    def get_prompt_from_form(self, user_id: str, random_prompts: List[str]) -> str:
        """从表单获取提示词，如果未设置则使用随机提示词"""
        form_data = self.get_user_form(user_id)
        prompt = form_data.get('prompt')
        
        if not prompt or prompt.strip() == "":
            # 使用随机提示词
            return random.choice(random_prompts)
        
        return prompt.strip()