# config.py
import os
from dotenv import load_dotenv
from typing import TypedDict, Optional

load_dotenv()

class UserSettings(TypedDict):
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler_name: str
    negative_prompt: str

class FormData(TypedDict):
    prompt: Optional[str]
    resolution: Optional[str]  # 格式如 "1024x1024"
    seed: Optional[int]  # None 表示随机
    hires_fix: bool

class HiresDefaults(TypedDict):
    hr_scale: float
    hr_upscaler: str
    denoising_strength: float
    hr_second_pass_ratio: float  # 基于总 steps 的比例，最终会换算为 hr_second_pass_steps
    hr_resize_x: int
    hr_resize_y: int

class Config:
    # Telegram配置
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    # 逗号分隔的用户ID列表，去空格并过滤空项
    _AUTH_RAW = os.getenv("AUTHORIZED_USERS", "")
    AUTHORIZED_USERS = [u.strip() for u in _AUTH_RAW.split(",") if u.strip()]
    
    # Stable Diffusion WebUI配置
    SD_API_URL = os.getenv('SD_API_URL', 'http://127.0.0.1:7860')
    SD_API_TIMEOUT = int(os.getenv('SD_API_TIMEOUT', '300'))  # 5分钟超时
    
    # 安全配置
    MAX_PROMPT_LENGTH = 500
    MAX_QUEUE_SIZE = 5  # 最大并发任务数
    
    # SD默认参数
    SD_DEFAULT_PARAMS: UserSettings = {
        'width': 1024,
        'height': 1024,
        'steps': 20,
        'cfg_scale': 7.0,
        'sampler_name': 'Euler a',
        'negative_prompt': 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry'
    }
    
    # 表单默认数据
    DEFAULT_FORM_DATA: FormData = {
        'prompt': None,
        'resolution': None,
        'seed': None,
        'hires_fix': False
    }
    
    # 高清修复默认参数
    HIRES_DEFAULTS: HiresDefaults = {
        'hr_scale': 2.0,
        'hr_upscaler': 'R-ESRGAN 4x+ Anime6B',
        'denoising_strength': 0.1,
        'hr_second_pass_ratio': 0.5,  # 二次步数 = steps * ratio
        'hr_resize_x': 0,
        'hr_resize_y': 0,
    }
    
    # 数据与图片保存设置
    DATA_DIR = os.getenv('DATA_DIR', 'data')
    LOCAL_SAVE_PATH = os.getenv('LOCAL_SAVE_PATH', 'generated_images')

    # 点赞可操作的最近图片数量上限
    LIKABLE_MESSAGE_LIMIT = int(os.getenv('LIKABLE_MESSAGE_LIMIT', '10'))

    # 连续重新生成的上限（当用户仅输入数字时触发）
    REGENERATE_MAX_RUNS = int(os.getenv('REGENERATE_MAX_RUNS', '10'))

    # 快照缓存上限（重启后仍可使用的最近生成参数数）
    SNAPSHOT_CACHE_LIMIT = int(os.getenv('SNAPSHOT_CACHE_LIMIT', '10'))