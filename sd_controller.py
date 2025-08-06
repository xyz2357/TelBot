import aiohttp
import asyncio
import base64
import io
import os
from datetime import datetime
from typing import Optional, Any, Dict, List, Tuple, Union
from PIL import Image
from config import Config
from PIL.PngImagePlugin import PngInfo
import json

class StableDiffusionController:
    api_url: str
    timeout: int
    last_result: Optional[Dict[str, Any]]

    def __init__(self) -> None:
        self.api_url = Config.SD_API_URL
        self.timeout = Config.SD_API_TIMEOUT
        self.last_result = None

    async def check_api_status(self) -> bool:
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

    async def get_models(self) -> List[str]:
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

    async def get_current_model(self) -> str:
        """获取当前使用的模型"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/sdapi/v1/options", timeout=10) as response:
                    if response.status == 200:
                        options = await response.json()
                        current_model = options.get('sd_model_checkpoint', '未知')
                        if '\\' in current_model or '/' in current_model:
                            current_model = current_model.split('\\')[-1].split('/')[-1]
                        if current_model.endswith('.safetensors') or current_model.endswith('.ckpt'):
                            current_model = current_model.rsplit('.', 1)[0]
                        return current_model
                    return "获取失败"
        except Exception as e:
            print(f"获取当前模型失败: {e}")
            return "未知"

    async def get_samplers(self) -> List[str]:
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

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        **params: Any
    ) -> Tuple[bool, Union[io.BytesIO, str]]:
        """生成图片"""
        generation_params: Dict[str, Any] = Config.SD_DEFAULT_PARAMS.copy()
        generation_params.update(params)
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
                            image_data = base64.b64decode(result['images'][0])
                            image = Image.open(io.BytesIO(image_data))
                            img_bytes = io.BytesIO()
                            image.save(img_bytes, format='PNG')
                            img_bytes.seek(0)
                            self.last_result = result
                            return True, img_bytes
                        else:
                            return False, "未生成图片"
                    else:
                        error_text = await response.text()
                        return False, f"API错误 ({response.status}): {error_text}"
        except asyncio.TimeoutError:
            return False, "生成超时，请检查提示词复杂度"
        except Exception as e:
            return False, f"生成失败: {str(e)}"

    async def save_last_result_locally(self) -> Optional[str]:
        """保存图片到本地，使用 SD WebUI 标准格式"""
        try:
            api_info = self.last_result.get('info', None)
            image_data = base64.b64decode(self.last_result['images'][0])
            image = Image.open(io.BytesIO(image_data))
            save_dir: str = Config.LOCAL_SAVE_PATH
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename: str = f"{timestamp}.png"
            filepath: str = os.path.join(save_dir, filename)
            metadata: PngInfo = PngInfo()
            if api_info and isinstance(api_info, str) and api_info.strip():
                parameters_text = json.loads(api_info).get('infotexts', [''])[0]
                metadata.add_text("parameters", parameters_text)
            image.save(filepath, 'PNG', pnginfo=metadata)
            print(f"图片已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"保存图片到本地失败: {e}")
            return None

    async def interrupt_generation(self) -> bool:
        """中断当前生成"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.api_url}/sdapi/v1/interrupt", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False

    async def get_progress(self) -> Tuple[float, float]:
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