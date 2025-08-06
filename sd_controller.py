import aiohttp
import asyncio
import base64
import io
import os
from datetime import datetime
from PIL import Image
from config import Config

class StableDiffusionController:
    def __init__(self):
        self.api_url = Config.SD_API_URL
        self.timeout = Config.SD_API_TIMEOUT
    
    async def check_api_status(self):
        """检查SD WebUI API是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sdapi/v1/options", timeout=10) as response:
                    print(f"SD API状态检查: {response.status}")  # 调试信息
                    return response.status == 200
        except aiohttp.ClientConnectorError as e:
            print(f"SD API连接错误: {e}")  # 调试信息
            return False
        except asyncio.TimeoutError:
            print("SD API连接超时")  # 调试信息
            return False
        except Exception as e:
            print(f"SD API未知错误: {e}")  # 调试信息
            return False
    
    async def get_models(self):
        """获取可用模型列表"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=10) as response:
                    if response.status == 200:
                        models = await response.json()
                        return [model['title'] for model in models]
                    return []
        except Exception as e:
            return []
    
    async def get_samplers(self):
        """获取可用采样器列表"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sdapi/v1/samplers", timeout=10) as response:
                    if response.status == 200:
                        samplers = await response.json()
                        return [sampler['name'] for sampler in samplers]
                    return []
        except Exception as e:
            return []
    
    async def generate_image(self, prompt, negative_prompt=None, **params):
        """生成图片"""
        # 合并默认参数
        generation_params = Config.SD_DEFAULT_PARAMS.copy()
        generation_params.update(params)
        
        # 设置提示词
        generation_params['prompt'] = prompt
        if negative_prompt:
            generation_params['negative_prompt'] = negative_prompt
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/sdapi/v1/txt2img",
                    json=generation_params,
                    timeout=self.timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        if result.get('images'):
                            # 解码base64图片
                            image_data = base64.b64decode(result['images'][0])
                            image = Image.open(io.BytesIO(image_data))
                            
                            # 保存为bytes用于发送
                            img_bytes = io.BytesIO()
                            image.save(img_bytes, format='PNG')
                            img_bytes.seek(0)
                            
                            # 可选：保存到本地
                            local_path = None
                            if Config.SAVE_IMAGES_LOCALLY:
                                local_path = await self.save_image_locally(image, prompt)
                            
                            return True, img_bytes, result.get('info', {}), local_path
                        else:
                            return False, "未生成图片", None, None
                    else:
                        error_text = await response.text()
                        return False, f"API错误 ({response.status}): {error_text}", None, None
                        
        except asyncio.TimeoutError:
            return False, "生成超时，请检查提示词复杂度", None, None
        except Exception as e:
            return False, f"生成失败: {str(e)}", None, None
    
    async def save_image_locally(self, image, prompt):
        """保存图片到本地"""
        try:
            # 创建保存目录
            save_dir = Config.LOCAL_SAVE_PATH
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 清理提示词作为文件名的一部分
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_prompt = safe_prompt.replace(' ', '_')
            filename = f"{timestamp}_{safe_prompt}.png"
            
            # 保存图片
            filepath = os.path.join(save_dir, filename)
            image.save(filepath, 'PNG')
            
            return filepath
            
        except Exception as e:
            print(f"保存图片到本地失败: {e}")
            return None
    
    async def interrupt_generation(self):
        """中断当前生成"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/sdapi/v1/interrupt", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def get_progress(self):
        """获取生成进度"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sdapi/v1/progress", timeout=5) as response:
                    if response.status == 200:
                        progress = await response.json()
                        return progress.get('progress', 0), progress.get('eta_relative', 0)
                    return 0, 0
        except Exception:
            return 0, 0