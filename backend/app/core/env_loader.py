"""统一加载项目环境变量（需在其它 app 模块导入前执行）"""
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_DIR.parent

load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv()
