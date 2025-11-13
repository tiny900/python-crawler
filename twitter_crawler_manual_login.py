from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import pickle
import os

def setup_driver():
    """设置Chrome浏览器驱动 - 可视化模式"""
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    # 创建本地用户数据目录
    user_data_dir = os.path.join(os.getcwd(), "chrome_user_data")
    chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"浏览器驱动启动失败: {e}")
        return None

def save_cookies(driver, filename="twitter_cookies.pkl"):
    """保存cookies到文件"""
    try:
        cookies = driver.get_cookies()
        with open(filename, 'wb') as f:
            pickle.dump(cookies, f)
        print(f"✅ Cookies已保存到 {filename}")
        return True
    except Exception as e:
        print(f"❌ 保存cookies失败: {e}")
        return False

def main():
    print("🔐 Twitter/X 登录工具 - 用于保存Cookies")
    print("="*60)
    print("📌 这个工具只需要运行一次")
    print("📌 登录后会保存cookies供自动化爬虫使用")
    
    driver = setup_driver()
    if not driver:
        return
    
    try:
        print("\n🌐 正在打开Twitter登录页面...")
        driver.get("https://x.com/login")
        
        print("\n⚠️  请在浏览器中手动完成登录")
        print("📝 登录步骤：")
        print("   1. 输入用户名/邮箱")
        print("   2. 输入密码")
        print("   3. 完成任何额外的验证（如果需要）")
        
        input("\n✅ 登录完成后，请按回车键继续...")
        
        # 等待页面加载
        time.sleep(3)
        
        # 检查是否登录成功
        if "home" in driver.current_url or "compose" in driver.current_url:
            print("\n🎉 登录成功！")
            
            # 保存cookies
            if save_cookies(driver):
                print("\n✅ Cookies保存成功！")
                print("📌 现在可以运行自动化爬虫了")
                print("   运行命令: python twitter_crawler.py")
            else:
                print("\n❌ Cookies保存失败，请重试")
        else:
            print("\n❌ 似乎登录未成功，请重新运行此脚本")
            
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    
    finally:
        input("\n按回车键关闭浏览器...")
        driver.quit()

if __name__ == "__main__":
    main()
