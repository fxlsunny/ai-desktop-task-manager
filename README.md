# 🖥️ AI Desktop Task Manager (桌面任务管家)

> 一个极简、低资源占用的 Windows 桌面任务管理工具。集成多模型 AI 助手、Markdown 编辑器、桌面截图标注、闹钟提醒等实用功能，全部由 Python 标准库 + Tkinter 构建，**零强依赖、毫秒级启动、内存占用 ~20MB**。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Dependencies](https://img.shields.io/badge/Core%20Deps-Zero-success)

---

## 📸 界面预览

```
┌─────────────────────┐
│ 📌 桌面任务管家      │  ← 半透明悬浮窗（可拖拽/折叠/调透明度）
│ ─────────────────── │
│ 🔴 [紧急] 修复 bug   │
│ 🟡 [中]   写周报    │
│ 🟢 [低]   整理资料   │
│ ─────────────────── │
│ ➕ 📋 🤖 📷 ⚙️ ×   │  ← 快捷按钮：新建/管理/AI/截图/设置/关闭
└─────────────────────┘
```

---

## ✨ 核心功能

### 🖥️ 桌面悬浮窗
- 始终置顶显示，可拖拽到屏幕任意位置
- **透明度可调**（20% ~ 100%），不干扰工作
- **一键折叠**，只保留顶栏标题条
- 多任务按优先级颜色分级显示（紧急🔴/高🟠/中🟡/低🟢）
- 支持快速勾选完成状态、实时更新进度百分比

### 📋 任务管理
| 字段 | 说明 |
|------|------|
| 任务标题 | 必填，显示在悬浮窗上 |
| 任务内容 | 支持 **Markdown 语法** + 内嵌图片 |
| 目标 | 本次任务期望达成的结果 |
| 问题/障碍 | 遇到的阻塞点备注 |
| 优先级 | 低 / 中 / 高 / 紧急（颜色区分） |
| 状态 | 待办 / 进行中 / 已完成 / 已取消 |
| 进度 | 0~100% 进度条 |
| 标签 | 逗号分隔的自由标签 |
| 提醒时间 | HH:MM 格式，到点弹窗 + 提示音 |
| 创建/更新时间 | 自动记录，显示耗时天数 |

### 🤖 AI 智能助手（独立窗口）
- **三栏布局**：左侧会话历史 / 中间消息区 / 底部输入框
- **6 大主流模型开箱即用**：
  | 提供商 | 默认模型 | 说明 |
  |--------|---------|------|
  | 🐉 腾讯混元 | `hunyuan-turbos-latest` | 国内首选，中文强 |
  | ⚡ Groq | `llama3-8b-8192` | **免费**，每天 14400 次 |
  | 🔵 DeepSeek | `deepseek-chat` | 代码任务友好 |
  | 🌙 Moonshot | `moonshot-v1-8k` | 长上下文 |
  | 🤖 OpenAI | `gpt-4o-mini` | 需自备 Key |
  | 🔧 自定义 | 任意 OpenAI 兼容接口 | 支持自建 / Ollama 转发等 |
- **Ollama 本地模型**：自动检测 `http://localhost:11434`，支持优先本地
- **流式输出**：边生成边显示，体验跟 ChatGPT 一致
- **顶栏一键切换模型**，每个提供商独立保存 API Key
- **会话历史持久化**：每个会话一个 JSON，`data/chat_history/` 目录
- **系统 Prompt 自定义**：可根据场景调整 AI 人设

### 📝 Markdown 放大编辑器
- 双击任务内容 或 点击 `🔍 放大编辑` 打开 **1200×720 编辑窗口**
- **三种视图模式**：仅编辑 / 分屏 / 仅预览
- **内置搜索替换**（`Ctrl+F`），支持正则
- **字号快捷缩放**（`Ctrl+= / Ctrl+-`）
- 纯 Tk tag 实现的 Markdown 渲染，**零第三方依赖**
  - 支持 H1-H6 / 粗体 / 斜体 / 代码块 / 有序列表 / 任务列表 / 链接 / 图片
- **本地图片预览**：`![alt](path)` 语法，相对路径 / 绝对路径均可

### 📷 桌面截图 + 标注
- **两种启动方式**：
  - 🔥 全局快捷键 `Ctrl+Alt+A`（需安装可选依赖 `keyboard`）
  - 🖱️ 悬浮窗 / 编辑器内的 `📷` 按钮
- **区域选择**：全屏半透明遮罩 + 拖拽框选（支持多屏 / 高 DPI）
- **标注工具**：矩形 / 椭圆 / 箭头 / 画笔 / 文字 / **马赛克**
  - 颜色盘 + 粗细滑块，`Ctrl+Z/Y` 撤销重做
- **保存规则**：
  - 自动按日期归档：`data/img/YYYYMMDD/HHMMSS_<自定义名>.jpg`
  - JPEG 质量 90，体积友好
  - 文件名可自定义，实时预览完整路径
  - 同名自动追加序号
- **一键插入任务内容**：截图保存后自动以 Markdown 格式插入，预览区直接可见

### ⏰ 闹钟 & 提醒
- 精确到分钟的 Toplevel 弹窗
- Windows 原生 Beep 提示音（无额外音频文件）
- 支持 "单次" / "每日循环" 两种模式

### 💾 数据管理 & 备份
- 所有数据本地 JSON 存储，**人类可读、可手改**
- **设置面板** 可指定 `data_dir` 路径（支持相对/绝对路径）
- **一键导出**：任务 + 历史对话 + 配置 打包 zip
- **邮件备份**：配置 SMTP（QQ / 163 / Gmail 均可），跨机器同步

### 🚀 开机自启 & 系统托盘
- 注册表 `Run` 键一键开启/关闭（无需管理员）
- 可选 `pystray` 支持系统托盘右下角图标
- 最小化后自动隐藏到托盘，不占任务栏

---

## 🚀 快速开始

### 环境要求
- **Windows 10/11**（Linux/macOS 大部分功能可用，但快捷键和注册表模块需适配）
- **Python 3.8+**
- **核心零依赖**，仅用标准库 + Tkinter

### 安装运行
```bash
# 1. 克隆项目
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager

# 2. 直接启动
python main.py

# 或双击启动（后台运行）
桌面任务管理.bat
```

### 安装可选增强（推荐）
```bash
双击 安装可选依赖.bat
# 等价于：pip install pillow pystray keyboard
```

| 可选包 | 启用功能 |
|--------|---------|
| `pillow` | 截图标注、Markdown 图片预览 |
| `pystray` | 系统托盘图标 |
| `keyboard` | 全局快捷键 `Ctrl+Alt+A` 截图 |

---

## 🔧 AI 配置

### 方式 1：界面配置（推荐）
1. 启动应用 → 悬浮窗点 `📋` 打开任务管理
2. 切到 **「AI 设置」** Tab
3. 下拉选择服务商 → 填入 API Key → 保存
4. 在 AI 助手窗口顶栏即可切换使用

### 方式 2：直接编辑 `config.json`
```json
{
  "ai": {
    "active_provider": "hunyuan",
    "providers": {
      "hunyuan": {
        "label": "腾讯混元",
        "api_key": "你的 Key",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-turbos-latest"
      }
    }
  }
}
```

### 方式 3：环境变量（避免 Key 落盘）
```powershell
$env:HUNYUAN_DEMO_KEY = "你的 Key"
python main.py
```

### 🆓 免费 AI 推荐
| 方案 | 获取方式 |
|------|---------|
| **Groq**（推荐）| https://console.groq.com → 注册即送每天 14400 次 |
| **Ollama 本地** | https://ollama.com 下载 → `ollama run qwen2:7b` |
| **腾讯混元** | https://console.cloud.tencent.com/hunyuan/api-key |
| **DeepSeek** | https://platform.deepseek.com/api_keys |

---

## ⌨️ 快捷键一览

### 全局
| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Alt + A` | 桌面截图（需装 keyboard 库） |

### Markdown 编辑器
| 快捷键 | 功能 |
|--------|------|
| `Ctrl + F` | 搜索 |
| `Ctrl + H` | 替换 |
| `Ctrl + =` | 字号放大 |
| `Ctrl + -` | 字号缩小 |
| `Ctrl + S` | 保存并关闭 |
| `Esc` | 取消退出 |

### 截图标注
| 快捷键 | 功能 |
|--------|------|
| `Ctrl + Z` | 撤销 |
| `Ctrl + Y` | 重做 |
| `Ctrl + S` | 保存 |
| `Esc` | 取消截图 |

---

## 📁 项目结构

```
ai-desktop-task-manager/
├── main.py               # 主入口（悬浮球 + 系统托盘 + 快捷键注册）
├── config.py             # 配置读写（多 Provider + 相对路径解析）
├── config.json           # 用户配置（首次运行自动生成）
├── config.json.example   # 配置示例
├── models.py             # 任务数据模型 + JSON 持久化
│
├── overlay.py            # 半透明悬浮窗（含截图按钮）
├── manager.py            # 任务管理主窗口（增删改查 / 设置 / AI 配置 / 备份）
├── markdown_editor.py    # Markdown 放大编辑器（~700 行，实时预览 + 搜索替换）
├── screenshot.py         # 桌面截图 + 标注编辑器（~700 行）
│
├── ai_window.py          # AI 对话窗口（三栏布局 + 模型切换）
├── ai_chat.py            # AI 后端抽象（Ollama / OpenAI 兼容）
├── chat_history.py       # 会话历史持久化
│
├── alarm.py              # 闹钟弹窗提醒
├── autostart.py          # 开机自启（注册表 Run 键）
├── backup.py             # 数据备份（本地 zip / 邮件 SMTP）
│
├── 桌面任务管理.bat       # Windows 后台启动脚本
├── 安装可选依赖.bat       # 安装 pillow/pystray/keyboard
│
├── data/                 # 用户数据目录（.gitignore）
│   ├── tasks.json        # 任务列表
│   ├── chat_history/     # AI 对话记录（每会话一个 JSON）
│   └── img/YYYYMMDD/     # 截图归档（按日期）
│
└── README.md
```

---

## 💡 技术亮点

### 🪶 极致轻量
- **内存 ~20MB**（对比 Electron 类应用动辄 200MB+）
- **闲置 0% CPU**（纯事件驱动，无轮询）
- **冷启动 < 0.5s**
- **核心零依赖**：仅 Python 标准库 + Tkinter（Python 自带）

### 🔌 多 AI 提供商统一抽象
- `ai_chat.py` 抽象 `AIBackend` 基类
- `OllamaBackend`（本地）+ `OpenAICompatBackend`（云端通用）
- 支持 `extra_body` 透传（如混元的 `enable_enhancement: true`）
- 流式/非流式双模式，自动降级

### 🎨 纯 Tk Markdown 渲染
- 不引入 `tkhtmlview` / `tkinterweb` 等重型依赖
- 利用 Text widget 的 tag 配置实现样式
- 正则分词 + 行级解析，性能足够千行内容实时预览
- 图片支持 `image_create` + PhotoImage 引用缓存防 GC

### 🖼️ Windows DPI 适配
- 调用 `ctypes.windll.shcore.SetProcessDpiAwareness(1)`
- 物理像素 vs 逻辑像素换算，多屏混用不跳位
- 虚拟屏边界识别，副屏截图正常

### 📦 相对路径 + 可移植
- `config.json` 中 `data_dir` 支持相对路径
- `config.py` 中 `_resolve_data_dir()` 统一解析
- 整个项目目录可随意移动，数据不会丢失

---

## 🐛 常见问题

<details>
<summary><b>Q: 启动后没有悬浮窗？</b></summary>

- 检查是否被防火墙/杀软拦截
- 看 `config.json` 中 `overlay_visible` 是否为 `true`
- `overlay_x` / `overlay_y` 是否在屏幕范围内（多屏用户重插拔显示器易出现）
- 删除 `config.json`，重启会生成默认值
</details>

<details>
<summary><b>Q: 截图按钮点击后崩溃？</b></summary>

确保安装了 `pillow`：
```bash
pip install pillow
```
如果仍崩溃，查看终端报错，常见是多屏 DPI 冲突，可尝试把副屏分辨率缩放调成 100%。
</details>

<details>
<summary><b>Q: AI 回复很慢 / 超时？</b></summary>

- 国内访问 OpenAI / Moonshot 建议走代理
- Groq 国内可直连，速度最快
- Ollama 本地模型取决于显卡，`qwen2:7b` 需 ~6GB 显存
</details>

<details>
<summary><b>Q: 如何把数据从 A 机器迁移到 B 机器？</b></summary>

1. A 机器：管理窗口 → 备份 → 导出为 zip
2. 通过邮件/U盘传到 B 机器
3. B 机器：备份 → 导入 zip  
或者直接复制整个 `data/` 目录到 B 机器即可。
</details>

<details>
<summary><b>Q: 开机自启不生效？</b></summary>

- 设置中勾选 "开机自启"
- 本质是写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- 如被安全软件拦截，请手动放行
</details>

---

## 🛠️ 开发 & 贡献

```bash
# 克隆
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager

# 运行
python main.py

# 无需编译 / 打包，直接修改即可生效
```

欢迎提交 [Issue](https://github.com/fxlsunny/ai-desktop-task-manager/issues) 和 Pull Request！

### 路线图
- [ ] macOS / Linux 适配（替换注册表模块）
- [ ] 任务看板视图（类 Kanban）
- [ ] 番茄钟集成
- [ ] 每日/每周 AI 总结报告
- [ ] 导出为 PDF 报告
- [ ] 多设备云端同步（WebDAV / OneDrive）

---

## 📄 许可证

[MIT License](LICENSE) © 2026 fxlsunny

---

## 🙏 致谢

- Python 标准库 & Tkinter 的设计者们
- [Pillow](https://python-pillow.org/) 提供图像能力
- [Groq](https://groq.com) / [DeepSeek](https://deepseek.com) / [腾讯混元](https://hunyuan.tencent.com) 提供的免费/低价 API
- 所有提过 Issue 和建议的朋友
