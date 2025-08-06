# main.py
from datetime import datetime
from bot import TelegramBot

if __name__ == "__main__":
    print("🎨 Stable Diffusion Telegram 控制器")
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    bot = TelegramBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 机器人已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
