"""
配置管理模块 - 负责读写 config/config.json，管理数据目录路径

目录布局（仓库根）：
    {repo_root}/
    ├── src/              ← 源码（本文件在这里）
    ├── scripts/          ← 启动脚本
    ├── config/
    │   ├── config.json          ← 本地真实配置（含 Key），不入库
    │   └── config.example.json  ← 公共模板（入库）
    └── data/             ← 运行数据（不入库）

路径策略（重要）：
- _APP_DIR 指向 **仓库根**（src/ 的上一级），便于 data/ 和 config/ 目录定位。
- DEFAULT_DATA_DIR 为相对路径字符串 "data"，相对于仓库根。
- cfg["data_dir"] 可以是相对路径（相对 _APP_DIR）或绝对路径（用户显式指定外部盘/
  共享目录时）。
- 对外统一通过 ensure_data_dir(cfg) 拿到 **绝对 Path**，其它模块无需关心相对/绝对。
- 保存时 `save()` 会自动把仓库根下的绝对路径转回相对路径，保证 config.json
  跨机器可移植。
- 首次启动若 config/config.json 不存在，会自动从 config.example.json 拷贝一份。
"""
import json
import os
import shutil
from pathlib import Path

# 仓库根目录 = src/ 的上一级
_APP_DIR = Path(__file__).resolve().parent.parent

# 默认数据目录：仓库根下 ./data（相对路径，便于迁移）
DEFAULT_DATA_DIR = "data"

# 配置目录
_CFG_DIR = _APP_DIR / "config"


def _resolve_data_dir(raw: str | os.PathLike) -> Path:
    """把 cfg['data_dir']（相对或绝对）解析成绝对 Path"""
    if not raw:
        return (_APP_DIR / DEFAULT_DATA_DIR).resolve()
    p = Path(raw)
    if not p.is_absolute():
        p = _APP_DIR / p
    return p.resolve()


def _normalize_for_save(raw: str | os.PathLike) -> str:
    """存盘时把落在程序目录下的绝对路径转回相对路径，提升可移植性"""
    if not raw:
        return DEFAULT_DATA_DIR
    p = Path(raw)
    if not p.is_absolute():
        # 用户/代码写入的就是相对路径，原样保留（统一用正斜杠，跨平台友好）
        return str(p).replace("\\", "/")
    try:
        rel = p.resolve().relative_to(_APP_DIR)
        return rel.as_posix()
    except ValueError:
        # 不在程序目录下 → 说明用户故意指向外部位置，保留绝对路径
        return str(p)

DEFAULTS = {
    "data_dir": DEFAULT_DATA_DIR,
    # 界面语言：zh_CN（默认中文）/ en_US（English）
    "language": "zh_CN",
    "overlay_x": 20,
    "overlay_y": 100,
    "overlay_width": 280,
    "overlay_height": 600,
    "overlay_opacity": 0.90,
    "overlay_always_top": True,
    "overlay_visible": True,
    "overlay_bg_color": "#1a1a2e",
    "overlay_accent_color": "#4fc3f7",
    "overlay_text_color": "#e0e0e0",
    "font_size": 11,
    "show_completed": False,
    "max_display_tasks": 10,
    "autostart": False,
    # AI 配置节
    # active_provider：当前激活的服务商 id（hunyuan / groq / deepseek / moonshot / openai / custom / ollama）
    # providers：每个服务商独立保存 api_key / base_url / model
    # 旧字段 api_key/base_url/model 保留做向下兼容，加载时会迁移到 providers 中
    "ai": {
        "prefer_ollama":   False,                        # 优先使用本地 Ollama（true 时忽略 active_provider）
        "ollama_base":     "http://localhost:11434",
        "ollama_model":    "qwen2:7b",
        "active_provider": "hunyuan",                    # 默认使用腾讯混元（内置 DEMO Key）
        "providers": {
            "hunyuan": {
                "label":    "腾讯混元",
                "api_key":  "",
                "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
                "model":    "hunyuan-turbos-latest",
            },
            "groq": {
                "label":    "Groq 免费",
                "api_key":  "",
                "base_url": "https://api.groq.com/openai/v1",
                "model":    "llama3-8b-8192",
            },
            "deepseek": {
                "label":    "DeepSeek",
                "api_key":  "",
                "base_url": "https://api.deepseek.com/v1",
                "model":    "deepseek-chat",
            },
            "moonshot": {
                "label":    "Moonshot",
                "api_key":  "",
                "base_url": "https://api.moonshot.cn/v1",
                "model":    "moonshot-v1-8k",
            },
            "openai": {
                "label":    "OpenAI",
                "api_key":  "",
                "base_url": "https://api.openai.com/v1",
                "model":    "gpt-4o-mini",
            },
            "custom": {
                "label":    "自定义",
                "api_key":  "",
                "base_url": "",
                "model":    "",
            },
        },
        "system_prompt":   "",                           # 自定义系统提示（空则用内置）
        # ── 以下为旧字段，保留做向下兼容，不再直接使用 ─────────
        "api_key":         "",
        "base_url":        "https://api.hunyuan.cloud.tencent.com/v1",
        "model":           "hunyuan-turbos-latest",
    },
    # 备份 / 邮件发送配置
    "backup": {
        "smtp_host":       "smtp.qq.com",                # SMTP 服务器（默认 QQ 邮箱）
        "smtp_port":       465,                          # SSL 端口
        "sender":          "",                           # 发件邮箱（通常同收件）
        "auth_code":       "",                           # 授权码（不是登录密码！）
        "recipient":       "",                           # 收件邮箱，留空则发给自己
        "include_config":  True,                         # 备份是否包含 config.json（脱敏）
        "last_export_dir": "",                           # 上次导出目录
    },
}

# 配置文件：优先读 config/config.json；不存在则尝试从 config.example.json 拷贝
_CFG_FILE     = _CFG_DIR / "config.json"
_CFG_EXAMPLE  = _CFG_DIR / "config.example.json"


def _ensure_cfg_file() -> None:
    """首次启动若 config.json 不存在，尝试从 config.example.json 拷贝一份"""
    if _CFG_FILE.exists():
        return
    try:
        _CFG_DIR.mkdir(parents=True, exist_ok=True)
        if _CFG_EXAMPLE.exists():
            shutil.copy2(_CFG_EXAMPLE, _CFG_FILE)
    except Exception as e:
        print(f"[config] 初始化 config.json 失败: {e}")


def load() -> dict:
    _ensure_cfg_file()
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    if _CFG_FILE.exists():
        try:
            with open(_CFG_FILE, "r", encoding="utf-8") as f:
                user = json.load(f)
        except Exception:
            user = {}
        # 顶层合并
        for k, v in (user or {}).items():
            # 嵌套字典做字段级合并，避免老配置丢失新加的默认键
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                merged = dict(cfg[k])
                # providers 需要做字段级深合并（每个 provider 是嵌套 dict）
                if k == "ai" and isinstance(v.get("providers"), dict):
                    merged_providers = dict(merged.get("providers", {}))
                    for pid, pdata in v["providers"].items():
                        base = dict(merged_providers.get(pid, {}))
                        if isinstance(pdata, dict):
                            base.update(pdata)
                        merged_providers[pid] = base
                    merged.update(v)
                    merged["providers"] = merged_providers
                else:
                    merged.update(v)
                cfg[k] = merged
            else:
                cfg[k] = v

    # ── 兼容旧配置：如果 ai.api_key 存在但 providers 中对应服务商为空，迁移过去 ──
    _migrate_legacy_ai(cfg)
    return cfg


def _migrate_legacy_ai(cfg: dict) -> None:
    """把旧版扁平 ai.api_key/base_url/model 迁移到对应 provider 下"""
    ai = cfg.get("ai", {})
    legacy_key = (ai.get("api_key") or "").strip()
    if not legacy_key:
        return

    # 如果旧 key 就是内置 DEMO Key，视为"未配置"，不迁移（避免在 UI 里显示成已填）
    try:
        from ai_chat import HUNYUAN_DEMO_KEY
        if legacy_key == HUNYUAN_DEMO_KEY:
            ai["api_key"] = ""
            return
    except Exception:
        pass

    legacy_base = (ai.get("base_url") or "").lower()
    providers = ai.setdefault("providers", {})

    # 按 base_url 识别应归属的 provider
    provider_id = "custom"
    if "hunyuan" in legacy_base:
        provider_id = "hunyuan"
    elif "groq" in legacy_base:
        provider_id = "groq"
    elif "deepseek" in legacy_base:
        provider_id = "deepseek"
    elif "moonshot" in legacy_base:
        provider_id = "moonshot"
    elif "openai.com" in legacy_base:
        provider_id = "openai"

    p = providers.get(provider_id, {})
    # 只在该 provider 尚未配置 key 时才迁移（避免覆盖）
    if not (p.get("api_key") or "").strip():
        p["api_key"]  = legacy_key
        p["base_url"] = ai.get("base_url") or p.get("base_url", "")
        p["model"]    = ai.get("model")    or p.get("model", "")
        providers[provider_id] = p
        ai.setdefault("active_provider", provider_id)
    # 清空旧字段，防止下次再迁移
    ai["api_key"] = ""


def save(cfg: dict):
    try:
        # 保存时对 data_dir 做可移植性归一化：程序目录下的路径写相对值
        to_save = dict(cfg)
        if "data_dir" in to_save:
            to_save["data_dir"] = _normalize_for_save(to_save["data_dir"])
        _CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[config] 保存失败: {e}")


def ensure_data_dir(cfg: dict) -> Path:
    """返回 data 目录的绝对 Path；支持 cfg['data_dir'] 为相对路径"""
    p = _resolve_data_dir(cfg.get("data_dir", DEFAULT_DATA_DIR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_app_dir() -> Path:
    """程序目录（脚本所在目录），跨模块统一获取相对基准"""
    return _APP_DIR
