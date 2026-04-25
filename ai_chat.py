"""
AI 问答模块
支持后端：
  1. Ollama       本地 (http://localhost:11434)  — 完全免费，需本地安装
  2. Groq Cloud   云端免费层  (https://api.groq.com/openai/v1)
                 免费额度：每天 14400 请求 / llama3-8b-8192
  3. OpenAI 兼容  任意 OpenAI 格式 API（openai / deepseek / moonshot / 自建 …）
  4. 内置离线     无网络/无配置时的硬编码提示，不调用任何接口

依赖：Python 内置 urllib（无需额外安装）
可选：urllib3 / requests（不强制，内部兼容判断）
"""
import json
import os
import threading
import urllib.request
import urllib.error
from typing import Callable, Iterator

# ─── 默认免费 Groq 配置 ───────────────────────────────────────
#  注册地址: https://console.groq.com  → API Keys → Create API Key
#  免费层每天约 14400 次，足够个人日常使用
GROQ_FREE_BASE   = "https://api.groq.com/openai/v1"
GROQ_FREE_MODEL  = "llama3-8b-8192"
GROQ_DEMO_KEY    = ""          # 留空表示未配置，需用户自行填入

# ─── 腾讯混元大模型配置（OpenAI 兼容）─────────────────────────
#  官网: https://cloud.tencent.com/document/product/1729
#  控制台: https://console.cloud.tencent.com/hunyuan/api-key
HUNYUAN_BASE      = "https://api.hunyuan.cloud.tencent.com/v1"
HUNYUAN_MODEL     = "hunyuan-turbos-latest"
# 演示 Key：默认为空；如需"零配置即用"可设置环境变量 HUNYUAN_DEMO_KEY
# 推荐方式 → 在 AI 设置面板填入自己的 Key，避免把 Key 硬编码到源码里
HUNYUAN_DEMO_KEY  = os.environ.get("HUNYUAN_DEMO_KEY", "")

OLLAMA_BASE      = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "qwen2:7b"   # 若用户本地有 qwen2 则优先

# ─── 系统提示词 ───────────────────────────────────────────────
SYSTEM_PROMPT = (
    "你是一个专注于任务管理和效率提升的 AI 助手，运行在「桌面任务管家」软件中。"
    "请用中文回答，回答要简洁、实用，重点突出。"
    "如果用户询问任务管理、时间规划、优先级等话题，请给出具体可操作的建议。"
)


# ─────────────────────────────────────────────────────────────
class AIBackend:
    """AI 后端抽象，子类实现 chat() / stream_chat()"""

    def chat(self, messages: list[dict]) -> str:
        raise NotImplementedError

    def stream_chat(self, messages: list[dict],
                    on_token: Callable[[str], None],
                    on_done: Callable[[str], None],
                    on_error: Callable[[str], None]):
        """在独立线程中流式输出，通过回调传出 token"""
        def _run():
            try:
                full = ""
                for tok in self._stream_iter(messages):
                    full += tok
                    on_token(tok)
                on_done(full)
            except Exception as e:
                on_error(str(e))
        threading.Thread(target=_run, daemon=True).start()

    def _stream_iter(self, messages: list[dict]) -> Iterator[str]:
        # 默认退化为非流式
        yield self.chat(messages)


# ─────────────────────────────────────────────────────────────
class OllamaBackend(AIBackend):
    """本地 Ollama 后端"""

    def __init__(self, base_url: str = OLLAMA_BASE,
                 model: str = OLLAMA_DEFAULT_MODEL):
        self.base = base_url.rstrip("/")
        self.model = model

    def _post(self, endpoint: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def chat(self, messages: list[dict]) -> str:
        resp = self._post("/api/chat", {
            "model": self.model,
            "messages": messages,
            "stream": False,
        })
        return resp.get("message", {}).get("content", "（无回复）")

    def _stream_iter(self, messages: list[dict]) -> Iterator[str]:
        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": True,
        }).encode()
        req = urllib.request.Request(
            f"{self.base}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            for raw_line in r:
                line = raw_line.decode().strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    tok = obj.get("message", {}).get("content", "")
                    if tok:
                        yield tok
                    if obj.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    @staticmethod
    def available(base_url: str = OLLAMA_BASE) -> bool:
        """探测 Ollama 是否在线"""
        try:
            urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=2)
            return True
        except Exception:
            return False

    @staticmethod
    def list_models(base_url: str = OLLAMA_BASE) -> list[str]:
        try:
            with urllib.request.urlopen(
                    f"{base_url.rstrip('/')}/api/tags", timeout=3) as r:
                data = json.loads(r.read().decode())
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────
class OpenAICompatBackend(AIBackend):
    """OpenAI 兼容接口（支持 openai / groq / deepseek / moonshot / hunyuan 等）

    extra_body：用于透传非标准参数（如腾讯混元的 enable_enhancement）
    label     ：显示名（如 "腾讯混元"），无则按域名推断
    """

    def __init__(self, api_key: str, base_url: str, model: str,
                 timeout: int = 60,
                 extra_body: dict | None = None,
                 label: str | None = None):
        self.api_key    = api_key
        self.base       = base_url.rstrip("/")
        self.model      = model
        self.timeout    = timeout
        self.extra_body = extra_body or {}
        self.label      = label

    def _merge(self, payload: dict) -> dict:
        """把 extra_body 合并进 payload 顶层（OpenAI SDK 的 extra_body 行为一致）"""
        if self.extra_body:
            for k, v in self.extra_body.items():
                payload.setdefault(k, v)
        return payload

    def _post(self, payload: dict) -> dict:
        data = json.dumps(self._merge(payload)).encode()
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=data,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode())

    def chat(self, messages: list[dict]) -> str:
        resp = self._post({
            "model":       self.model,
            "messages":    messages,
            "temperature": 0.7,
            "max_tokens":  2048,
        })
        return (resp.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "（无回复）"))

    def _stream_iter(self, messages: list[dict]) -> Iterator[str]:
        payload = self._merge({
            "model":       self.model,
            "messages":    messages,
            "temperature": 0.7,
            "max_tokens":  2048,
            "stream":      True,
        })
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=data,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            for raw_line in r:
                line = raw_line.decode().strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    tok = (obj.get("choices", [{}])[0]
                               .get("delta", {})
                               .get("content", ""))
                    if tok:
                        yield tok
                except json.JSONDecodeError:
                    continue


# ─────────────────────────────────────────────────────────────
class OfflineBackend(AIBackend):
    """离线后备：给出配置提示，无需网络"""

    _TIPS = [
        "💡 请在「设置 → AI 配置」中填写 API Key 或启动本地 Ollama 后使用 AI 功能。",
        "📌 推荐方案：\n"
        "  • 腾讯混元（内置演示 Key，开箱即用）\n"
        "  • Groq Cloud（llama3-8b）— 注册 console.groq.com 获取免费 Key\n"
        "  • Ollama 本地 — 安装 ollama.ai 后运行 `ollama run qwen2:7b`",
        "🔑 获取 Groq 免费 Key：\n"
        "  1. 访问 https://console.groq.com\n"
        "  2. 注册 / 登录\n"
        "  3. 左侧菜单 → API Keys → Create API Key\n"
        "  4. 复制 Key 填入设置面板",
    ]
    _idx = 0

    def chat(self, messages: list[dict]) -> str:
        msg = self._TIPS[self._idx % len(self._TIPS)]
        OfflineBackend._idx += 1
        return msg


# ─────────────────────────────────────────────────────────────
def build_backend(cfg: dict) -> AIBackend:
    """
    根据 config 构造合适的后端，优先级：
      1. prefer_ollama=True 且本地 Ollama 在线  → OllamaBackend
      2. active_provider 对应 provider 配置了 api_key → OpenAICompatBackend
      3. active_provider 为 hunyuan 且未配置 key → 用内置混元 DEMO Key 兜底
      4. 离线提示
    """
    ai_cfg = cfg.get("ai", {})

    # ── 优先 Ollama（需显式打开开关） ─────────────────────────
    ollama_url = ai_cfg.get("ollama_base", OLLAMA_BASE)
    if ai_cfg.get("prefer_ollama", False) and OllamaBackend.available(ollama_url):
        model = ai_cfg.get("ollama_model", OLLAMA_DEFAULT_MODEL)
        models = OllamaBackend.list_models(ollama_url)
        if models and model not in models:
            model = models[0]
        return OllamaBackend(ollama_url, model)

    # ── 按 active_provider 查找对应配置 ──────────────────────
    providers   = ai_cfg.get("providers", {}) or {}
    active_id   = ai_cfg.get("active_provider", "hunyuan")

    # 老配置兜底：没有 providers 时回退到旧字段
    if not providers:
        api_key  = (ai_cfg.get("api_key") or "").strip()
        base_url = ai_cfg.get("base_url", HUNYUAN_BASE).strip()
        model    = ai_cfg.get("model",   HUNYUAN_MODEL).strip()
        if api_key:
            return _make_openai_compat(api_key, base_url, model)
        if HUNYUAN_DEMO_KEY:
            return _make_openai_compat(HUNYUAN_DEMO_KEY, HUNYUAN_BASE, HUNYUAN_MODEL)
        return OfflineBackend()

    p = providers.get(active_id) or {}
    api_key  = (p.get("api_key")  or "").strip()
    base_url = (p.get("base_url") or "").strip()
    model    = (p.get("model")    or "").strip()

    if api_key and base_url and model:
        return _make_openai_compat(api_key, base_url, model,
                                   label=p.get("label"))

    # ── 混元无 Key 时使用内置 DEMO Key 兜底（零配置即用）────
    if active_id == "hunyuan" and HUNYUAN_DEMO_KEY:
        return _make_openai_compat(HUNYUAN_DEMO_KEY, HUNYUAN_BASE, HUNYUAN_MODEL,
                                   label="腾讯混元(内置)")

    # ── 离线后备 ─────────────────────────────────────────────
    return OfflineBackend()


def _make_openai_compat(api_key: str, base_url: str, model: str,
                        label: str | None = None) -> OpenAICompatBackend:
    """按 base_url 识别服务商，自动注入服务商特需参数（如混元的 enable_enhancement）"""
    base_low = base_url.lower()
    extra: dict = {}

    if "hunyuan" in base_low:
        # 腾讯混元：启用内容增强（联网/工具增强）
        extra = {"enable_enhancement": True}
        label = label or "腾讯混元"
    elif "groq" in base_low:
        label = label or "Groq Cloud"
    elif "deepseek" in base_low:
        label = label or "DeepSeek"
    elif "moonshot" in base_low:
        label = label or "Moonshot"
    elif "openai.com" in base_low:
        label = label or "OpenAI"

    return OpenAICompatBackend(api_key, base_url, model,
                               extra_body=extra, label=label)


def build_backend_for_provider(cfg: dict, provider_id: str) -> AIBackend:
    """即时指定某个 provider 构造后端（用于 AI 窗口下拉切换）"""
    # 复制一份 cfg，避免污染主 cfg
    local = json.loads(json.dumps(cfg))
    local.setdefault("ai", {})
    # 切换 provider 时强制关闭 Ollama 优先（除非用户选的就是 ollama）
    if provider_id == "ollama":
        local["ai"]["prefer_ollama"] = True
    else:
        local["ai"]["prefer_ollama"] = False
        local["ai"]["active_provider"] = provider_id
    return build_backend(local)


# ─────────────────────────────────────────────────────────────
class ChatSession:
    """维护一次会话的消息历史"""

    def __init__(self, backend: AIBackend,
                 system_prompt: str = SYSTEM_PROMPT,
                 max_history: int = 20):
        self.backend   = backend
        self.max_his   = max_history
        self.history: list[dict] = [{"role": "system", "content": system_prompt}]

    def _trimmed(self) -> list[dict]:
        """保留 system + 最近 max_history 条对话"""
        sys = self.history[:1]
        rest = self.history[1:][-self.max_his * 2:]
        return sys + rest

    def send_stream(self, user_msg: str,
                    on_token: Callable[[str], None],
                    on_done: Callable[[str], None],
                    on_error: Callable[[str], None]):
        self.history.append({"role": "user", "content": user_msg})
        msgs = self._trimmed()

        def _done(full: str):
            self.history.append({"role": "assistant", "content": full})
            on_done(full)

        self.backend.stream_chat(msgs, on_token, _done, on_error)

    def clear(self):
        self.history = self.history[:1]   # 只保留 system prompt
