import subprocess
import psutil
import platform
import asyncio
from datetime import datetime

class CommandExecutor:
    def __init__(self):
        self.system = platform.system()
    
    async def execute_command(self, command, timeout=30):
        """安全执行系统命令"""
        try:
            if self.system == "Windows":
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            
            result = stdout.decode('utf-8', errors='ignore')
            if stderr:
                result += f"\nError: {stderr.decode('utf-8', errors='ignore')}"
            
            return True, result
            
        except asyncio.TimeoutError:
            return False, "命令执行超时"
        except Exception as e:
            return False, f"执行错误: {str(e)}"
    
    def get_system_info(self):
        """获取系统信息"""
        try:
            info = {
                'system': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'cpu_count': psutil.cpu_count(),
                'memory': f"{psutil.virtual_memory().total // (1024**3)}GB",
                'cpu_percent': f"{psutil.cpu_percent(interval=1)}%",
                'memory_percent': f"{psutil.virtual_memory().percent}%",
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            }
            return info
        except Exception as e:
            return {'error': str(e)}
    
    def get_running_processes(self, limit=10):
        """获取运行中的进程"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                processes.append(proc.info)
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
            return processes[:limit]
        except Exception as e:
            return [{'error': str(e)}]