"""应用配置"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

# 数据库路径
DATABASE_URL = f"sqlite:///{BASE_DIR / 'data' / 'homepage.db'}"

# 网站信息
SITE_TITLE = "我的个人主页"
SITE_AUTHOR = "你的名字"
SITE_DESCRIPTION = "欢迎来到我的个人空间"

# 日记分页
DIARY_PAGE_SIZE = 10

# Unsplash API（通过环境变量设置）
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
# Pexels API（替代 Unsplash，图片质量更高）
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# 调试模式（通过环境变量开启，如 DEBUG=true python run.py）
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
