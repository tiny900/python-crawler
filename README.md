# Twitter Crawler

自动化 Twitter 数据爬虫，支持定时运行和 S3 上传。

## 功能特性

- 🤖 自动爬取多个 Twitter 账号
- ⏰ 每小时自动运行
- ☁️ 自动上传到 AWS S3
- 🔐 Cookie 加密存储
- 📊 运行统计和监控

## 快速开始

### 本地运行

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 首次登录获取 Cookie
```bash
python twitter_crawler_manual_login.py
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 添加你的配置
```

4. 运行爬虫
```bash
# 单次运行
python twitter_crawler.py

# 定时调度
python twitter_scheduler.py
```

### EC2 部署

1. 克隆代码
```bash
git clone https://github.com/tiny900/python-crawler.git
cd python-crawler
```

2. 运行部署脚本
```bash
bash deploy_to_ec2.sh
```

3. 配置环境变量
```bash
nano .env
```

4. 启动服务
```bash
sudo systemctl start twitter-crawler
```

## 配置说明

### 爬取账号
在 `twitter_crawler.py` 中修改 `TWITTER_ACCOUNTS`

### 时间范围
默认爬取最近 7 天，可在代码中调整

### S3 配置
需要在 `.env` 中配置 AWS 凭证

## 注意事项

- Cookie 会过期，需要定期更新
- 遵守 Twitter 使用条款
- 建议使用加密存储 Cookie
