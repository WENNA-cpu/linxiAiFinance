"""模型版本管理与回滚"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import MODEL_METADATA_PATH

BACKEND_DIR = Path(__file__).resolve().parents[2]
METADATA_FILE = BACKEND_DIR / MODEL_METADATA_PATH
VERSIONS_DIR = BACKEND_DIR / "models" / "versions"


def _load_metadata() -> Dict[str, Any]:
    if not METADATA_FILE.exists():
        return {"active": {}, "history": []}
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_metadata(data: Dict[str, Any]) -> None:
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_model_version(
    model_type: str,
    model_path: Path,
    metrics: Dict[str, Any],
    extra_files: Optional[List[Path]] = None,
) -> str:
    """训练完成后注册新版本并归档"""
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    version = datetime.now().strftime("v%Y%m%d_%H%M%S")
    version_dir = VERSIONS_DIR / model_type / version
    version_dir.mkdir(parents=True, exist_ok=True)

    dest = version_dir / model_path.name
    shutil.copy2(model_path, dest)

    copied = [str(dest)]
    for f in extra_files or []:
        if f.exists():
            d = version_dir / f.name
            shutil.copy2(f, d)
            copied.append(str(d))

    meta = _load_metadata()
    entry = {
        "version": version,
        "model_type": model_type,
        "path": str(dest.relative_to(BACKEND_DIR)) if dest.is_relative_to(BACKEND_DIR) else str(dest),
        "files": copied,
        "metrics": metrics,
        "created_at": datetime.now().isoformat(),
    }
    meta["active"][model_type] = entry
    meta["history"].insert(0, entry)
    meta["history"] = meta["history"][:20]
    _save_metadata(meta)
    return version


def rollback_model(model_type: str, version: str) -> Dict[str, Any]:
    """回滚到指定版本"""
    meta = _load_metadata()
    target = None
    for item in meta["history"]:
        if item["model_type"] == model_type and item["version"] == version:
            target = item
            break
    if not target:
        raise ValueError(f"未找到 {model_type} 版本 {version}")

    # 复制归档文件回 models 根目录
    for file_path in target.get("files", []):
        src = Path(file_path)
        if not src.is_absolute():
            src = BACKEND_DIR / src
        if src.exists():
            dest = BACKEND_DIR / "models" / src.name
            shutil.copy2(src, dest)

    meta["active"][model_type] = target
    _save_metadata(meta)
    return target


def get_active_version(model_type: str) -> Optional[Dict[str, Any]]:
    return _load_metadata().get("active", {}).get(model_type)


def list_versions(model_type: Optional[str] = None) -> List[Dict[str, Any]]:
    history = _load_metadata().get("history", [])
    if model_type:
        return [h for h in history if h["model_type"] == model_type]
    return history


def should_use_new_model(seed: str, ratio: int) -> bool:
    """基于 seed 的稳定灰度分流"""
    if ratio <= 0:
        return False
    if ratio >= 100:
        return True
    bucket = abs(hash(f"lingxi:{seed}")) % 100
    return bucket < ratio


MODEL_TYPE_ALIASES = {
    "lstm": "lstm_cycle",
    "lstm_cycle": "lstm_cycle",
    "rf": "rf_risk",
    "rf_risk": "rf_risk",
}


def normalize_model_type(model_type: str) -> str:
    key = (model_type or "").strip().lower()
    if key not in MODEL_TYPE_ALIASES:
        raise ValueError(f"不支持的 model_type: {model_type}，可选 lstm / rf")
    return MODEL_TYPE_ALIASES[key]


def resolve_target_version(model_type: str, target_version: str) -> str:
    """精确或前缀匹配版本号（如 v20260608 或 v1.0 别名）"""
    version = (target_version or "").strip()
    if not version:
        raise ValueError("target_version 不能为空")

    history = list_versions(model_type)
    if not history:
        raise ValueError(f"无可用 {model_type} 版本记录")

    for item in history:
        if item["version"] == version:
            return item["version"]

    prefix_matches = [h for h in history if h["version"].startswith(version)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]["version"]
    if len(prefix_matches) > 1:
        raise ValueError(f"版本前缀 {version} 匹配到多个版本，请使用完整版本号")

    raise ValueError(f"未找到 {model_type} 版本 {version}")


RUNTIME_CONFIG_FILE = BACKEND_DIR / "models" / "model_runtime.json"


def _load_runtime_config() -> Dict[str, Any]:
    if not RUNTIME_CONFIG_FILE.exists():
        meta = _load_metadata()
        return {
            "lstm_version": meta.get("active", {}).get("lstm_cycle", {}).get("version"),
            "rf_version": meta.get("active", {}).get("rf_risk", {}).get("version"),
        }
    with open(RUNTIME_CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_runtime_config(data: Dict[str, Any]) -> None:
    RUNTIME_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RUNTIME_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_runtime_version(model_type: str, version: str) -> Dict[str, Any]:
    """更新运行时版本配置（等效于 LSTM_VERSION / RF_VERSION 持久化）"""
    runtime = _load_runtime_config()
    if model_type == "lstm_cycle":
        runtime["lstm_version"] = version
        runtime["LSTM_VERSION"] = version
    elif model_type == "rf_risk":
        runtime["rf_version"] = version
        runtime["RF_VERSION"] = version
    runtime["updated_at"] = datetime.now().isoformat()
    _save_runtime_config(runtime)
    return runtime


def get_runtime_config() -> Dict[str, Any]:
    return _load_runtime_config()
