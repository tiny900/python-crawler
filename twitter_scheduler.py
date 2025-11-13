#!/usr/bin/env python3
"""
Twitter 爬虫简化调度器
每小时运行一次，自动S3上传
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
import json
from pathlib import Path

# ========== 配置区域 ==========
CONFIG = {
    # 爬虫脚本文件名
    "auto_crawler": "twitter_crawler.py",  # 自动爬虫脚本
    "s3_uploader": "s3_uploader.py",  # S3上传脚本

    # 定时运行配置
    "schedule": {
        "hourly_run": True,  # 每小时运行一次
        "daily_limit": 24    # 每日最大运行次数（每小时一次）
    },

    # S3上传配置
    "s3": {
        "enabled": True,  # 是否启用S3上传
        "auto_upload": True,  # 爬虫成功后自动上传
        "timeout": 300  # S3上传超时时间（秒）
    }
}


class SimpleCrawlerScheduler:
    def __init__(self):
        self.config = CONFIG
        self.stats_file = Path("scheduler_stats.json")
        self.daily_run_count = 0
        self.last_run_date = None
        self.run_times = []  # 记录运行时间
        self.load_stats()

    def load_stats(self):
        """加载运行统计"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
                    self.daily_run_count = stats.get('daily_run_count', 0)

                    last_date = stats.get('last_run_date')
                    if last_date:
                        self.last_run_date = datetime.strptime(last_date, '%Y-%m-%d').date()
            except Exception as e:
                print(f"⚠️ 加载统计信息失败: {e}")

    def save_stats(self):
        """保存运行统计"""
        try:
            stats = {
                'daily_run_count': self.daily_run_count,
                'last_run_date': datetime.now().date().isoformat(),
                'last_update': datetime.now().isoformat(),
                'run_history': self.run_times[-10:]  # 保存最近10次运行记录
            }
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存统计信息失败: {e}")

    def check_daily_limit(self):
        """检查每日运行次数限制"""
        current_date = datetime.now().date()

        # 如果是新的一天，重置计数器
        if self.last_run_date != current_date:
            self.daily_run_count = 0
            self.last_run_date = current_date

        return self.daily_run_count < self.config['schedule']['daily_limit']

    def upload_to_s3(self):
        """执行S3上传"""
        if not self.config['s3']['enabled']:
            print("📤 S3上传已禁用")
            return True

        print("\n📤 开始上传到S3...")
        try:
            # 检查S3上传脚本是否存在
            if not os.path.exists(self.config['s3_uploader']):
                print(f"❌ S3上传脚本不存在: {self.config['s3_uploader']}")
                return False

            s3_process = subprocess.run(
                [sys.executable, self.config['s3_uploader']],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=self.config['s3']['timeout']
            )

            if s3_process.returncode == 0:
                print("✅ S3上传完成!")
                # 显示上传输出
                for line in s3_process.stdout.split('\n'):
                    if line.strip():
                        print(f"  > {line}")
                return True
            else:
                print("❌ S3上传失败")
                if s3_process.stderr:
                    print(f"错误信息: {s3_process.stderr}")
                if s3_process.stdout:
                    print(f"输出信息: {s3_process.stdout}")
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ S3上传超时（{self.config['s3']['timeout']}秒）")
            return False
        except Exception as e:
            print(f"❌ 运行S3上传时出错: {e}")
            return False

    def run_crawler(self):
        """运行爬虫"""
        if not self.check_daily_limit():
            print(f"⚠️ 已达到每日运行限制 ({self.config['schedule']['daily_limit']} 次)")
            return False

        start_time = time.time()  # 记录开始时间

        print(f"\n{'=' * 60}")
        print(f"🚀 开始运行爬虫 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 今日第 {self.daily_run_count + 1} 次运行")

        # 运行爬虫
        try:
            print(f"\n📝 执行命令: python {self.config['auto_crawler']}")

            # 使用 subprocess 运行爬虫
            process = subprocess.Popen(
                [sys.executable, self.config['auto_crawler']],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1
            )

            # 实时显示输出
            output_lines = []
            try:
                for line in process.stdout:
                    print(f"  > {line.rstrip()}")
                    output_lines.append(line.rstrip())
            except Exception as e:
                print(f"  > [读取输出时出错: {e}]")

            # 等待进程结束
            return_code = process.wait()

            # 记录运行时间
            end_time = time.time()
            duration = end_time - start_time
            self.run_times.append({
                'time': datetime.now().isoformat(),
                'duration': duration
            })

            # 只保留最近10次记录
            if len(self.run_times) > 10:
                self.run_times.pop(0)

            # 显示运行时间统计
            print(f"\n⏱️ 运行时间统计:")
            print(f"  - 本次运行: {duration:.1f} 秒 ({duration / 60:.1f} 分钟)")

            if len(self.run_times) > 1:
                avg_time = sum(r['duration'] for r in self.run_times) / len(self.run_times)
                print(f"  - 平均运行时间: {avg_time:.1f} 秒 ({avg_time / 60:.1f} 分钟)")
                print(f"  - 最慢运行: {max(r['duration'] for r in self.run_times):.1f} 秒")

            if return_code == 0:
                print("\n✅ 爬虫运行成功!")
                self.daily_run_count += 1
                self.save_stats()

                # 自动运行S3上传
                if self.config['s3']['auto_upload']:
                    s3_success = self.upload_to_s3()
                    if not s3_success:
                        print("⚠️  注意: 爬虫成功但S3上传失败")

                return True
            else:
                print(f"\n❌ 爬虫运行失败，返回码：{return_code}")
                return False

        except KeyboardInterrupt:
            print("\n⚠️  爬虫被手动中断")
            process.terminate()
            raise
        except Exception as e:
            print(f"\n❌ 运行出错: {e}")
            return False
        finally:
            print(f"{'=' * 60}\n")

    def job_wrapper(self):
        """作业包装器 - 用于schedule调用"""
        try:
            self.run_crawler()
        except Exception as e:
            print(f"调度任务执行失败: {e}")


def main():
    """主函数"""
    print("""
    🤖  Twitter 爬虫简化调度器
    ===========================
    每小时运行一次，自动上传S3
    """)

    # 创建调度器实例
    scheduler = SimpleCrawlerScheduler()

    # 检查S3上传脚本
    if scheduler.config['s3']['enabled']:
        if os.path.exists(scheduler.config['s3_uploader']):
            print(f"📤 S3上传: 已启用 ({scheduler.config['s3_uploader']})")
        else:
            print(f"⚠️  S3上传脚本不存在: {scheduler.config['s3_uploader']}")
            choice = input("是否继续运行但禁用S3上传？(y/n): ")
            if choice.lower() == 'y':
                scheduler.config['s3']['enabled'] = False
                print("📤 S3上传已禁用")
            else:
                return
    else:
        print("📤 S3上传: 已禁用")

    # 设置定时任务 - 每小时运行一次
    print("\n📅 设置定时任务...")
    schedule.every().hour.do(scheduler.job_wrapper)
    print("  ⏰ 每小时运行一次")

    print(f"\n📊 每日运行限制: {scheduler.config['schedule']['daily_limit']} 次")
    print("\n✅ 调度器已启动，按 Ctrl+C 停止")

    # 立即运行一次
    print("\n🚀 立即运行第一次爬虫...")
    scheduler.run_crawler()

    # 主循环
    try:
        while True:
            schedule.run_pending()

            # 显示状态
            next_run = schedule.next_run()
            if next_run:
                current_time = datetime.now()
                if current_time.second == 0:  # 每分钟更新一次显示
                    print(f"\r⏳ 等待中... 当前时间: {current_time.strftime('%H:%M:%S')} | "
                          f"下次运行: {next_run.strftime('%H:%M:%S')} | "
                          f"今日已运行: {scheduler.daily_run_count} 次", end='', flush=True)

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\n👋 调度器已停止")
        print(f"📊 今日共运行 {scheduler.daily_run_count} 次")
        scheduler.save_stats()


if __name__ == "__main__":
    # 确保在正确的目录运行
    try:
        # 获取脚本所在目录
        if hasattr(sys, 'frozen'):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))

        os.chdir(script_dir)
    except:
        pass

    main()