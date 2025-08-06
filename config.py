# config.py
import os
from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()

class UserSettings(TypedDict):
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler_name: str
    negative_prompt: str

class Config:
    # Telegram配置
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    AUTHORIZED_USERS = os.getenv("AUTHORIZED_USERS", "").split(",") # 逗号分隔的用户ID列表
    
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
    
    # 图片保存设置
    LOCAL_SAVE_PATH = os.getenv('LOCAL_SAVE_PATH', 'generated_images')