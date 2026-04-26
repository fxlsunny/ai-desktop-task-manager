# 🖥️ AI Desktop Task Manager (桌面任务管家)

> 一个极简、低资源占用的 Windows 桌面任务管理工具。集成多模型 AI 助手、Markdown 编辑器、桌面截图标注、闹钟提醒等实用功能，全部由 Python 标准库 + Tkinter 构建，**零强依赖、毫秒级启动、内存占用 ~20MB**。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![License](https://img.shields.io/badge/License-MIT-green) ![Dependencies](https://img.shields.io/badge/Core%20Deps-Zero-success)

---

## 📸 界面预览

![桌面任务管家 - 主界面](./img/ai_task_manager_01.jpg)

> 半透明悬浮窗（可拖拽 / 折叠 / 调透明度） + 任务管理窗 + AI 对话窗 + 放大编辑器 + 桌面截图标注，一套串起来。

---

## ✨ 核心功能

### 🖥️ 桌面悬浮窗
- 始终置顶显示，可拖拽到屏幕任意位置
- **透明度可调**（20% ~ 100%），不干扰工作
- **一键折叠**，只保留顶栏标题条
- 可选系统托盘图标（依赖 `pystray`，已自动降级）
- 开机自启动（写入注册表，一键开关）

### 📝 任务管理
- 任务支持：**标题 / 内容 / 优先级 / 截止日期 / 闹钟提醒 / 分类标签**
- 状态：未完成 / 已完成（可只看未完成）
- 按优先级颜色标记（🔴 高 / 🟡 中 / 🟢 低）
- 搜索、筛选、排序一应俱全
- **放大编辑器**：双击任务内容区打开独立窗口（1200×720），左编辑右预览
  - 支持搜索/替换、字号缩放（Ctrl+滚轮）、快捷键 Ctrl+S/Z/F
  - **Markdown 预览** 纯 Tk tag 实现（# / ## / **粗体** / *斜体* / `code` / > 引用 / - 列表 / [链接]）
  - **本地图片预览**：`![alt](relative/path.jpg)` 可直接显示缩略图

### 🤖 AI 助手（多模型）
内置 **7 个主流 AI 服务商** 配置模板，一键切换：

| Provider | 说明 | 费用 |
|----------|------|------|
| 🐉 **腾讯混元** | `hunyuan-turbos-latest`，中文优化，内置 DEMO Key 可零配置即用 | 免费额度 |
| 🟢 **Ollama 本地** | 完全离线运行，默认模型 `qwen2:7b` | 免费（需本地部署） |
| ⚡ **Groq** | `llama3-8b-8192`，推理极快 | 免费额度较大 |
| 🔵 **DeepSeek** | `deepseek-chat`，代码能力强 | 低价 |
| 🌙 **Moonshot** | `moonshot-v1-8k`，长上下文 | 付费 |
| 🤖 **OpenAI** | `gpt-4o-mini` 等 | 付费 |
| 🔧 **自定义** | 任意 OpenAI 兼容 API | 取决于服务 |

**特性**：
- **SSE 流式输出**：回复逐字打字，支持中途停止
- **持久化会话**：每次对话自动保存到 `data/chat_history/`
  - 左侧会话列表可查看/删除/切换，类似 ChatGPT
- **系统提示词可定制**：在设置中自定义人设
- **请求透传**：`extra_body` 支持（例如混元的 `enable_enhancement`）

### 📷 桌面截图 & 标注
- 全屏半透明遮罩 → 拖拽选区 → 进入标注编辑器
- **标注工具**：矩形、椭圆、箭头、画笔、文字、马赛克
- 颜色盘 + 粗细滑块、撤销/重做/清空
- 快捷键：Ctrl+Z/Y（撤销/重做）、Ctrl+S（保存）、Esc（退出）
- **多屏 + HiDPI 适配**（启动前自动开启 DPI Awareness）
- **自动插入任务**：截图保存后直接追加到当前编辑的任务内容中
- **全局热键**：`Ctrl+Alt+A`（需安装 `keyboard` 库）

### ⏰ 闹钟提醒
- 每分钟精确检测一次（自动对齐系统时钟）
- 到点弹窗 + 可选声音提醒
- 支持"提前 N 分钟"

### 💾 备份 / 邮件导出
- 一键把 `tasks.json` + 对话历史打包为 zip
- 可选通过 SMTP 邮件发送（默认 QQ 邮箱 465 SSL）
- 支持主流服务商：QQ/163/126/Gmail/Outlook/新浪/Yahoo 一键选择
- 可选是否包含 `config.json`（敏感字段自动脱敏）

---

## 🗂️ 项目结构

```
ai-desktop-task-manager/
├── src/                         # 所有 Python 源码
│   ├── main.py                  # ← 程序入口
│   ├── config.py                # 配置加载/保存
│   ├── models.py                # 任务数据模型 & Store
│   ├── overlay.py               # 桌面悬浮窗
│   ├── manager.py               # 任务管理窗
│   ├── ai_window.py             # AI 对话窗
│   ├── ai_chat.py               # AI 后端抽象（OpenAI/Ollama）
│   ├── chat_history.py          # 对话会话持久化
│   ├── markdown_editor.py       # 放大编辑器（MD 预览 + 搜索替换）
│   ├── screenshot.py            # 桌面截图 & 标注
│   ├── alarm.py                 # 闹钟提醒
│   ├── backup.py                # 备份 & 邮件导出
│   └── autostart.py             # 开机自启动（Windows 注册表）
├── scripts/
│   ├── 桌面任务管理.bat          # 启动脚本（双击运行）
│   └── 安装可选依赖.bat          # 一键装 pystray / pillow / keyboard
├── config/
│   ├── config.example.json      # 配置模板（入库）
│   └── config.json              # 本地真实配置（含 Key，.gitignore，首次启动自动生成）
├── data/                        # 运行数据（.gitignore）
│   ├── tasks.json               # 任务列表
│   ├── chat_history/            # AI 会话 JSON
│   └── img/YYYYMMDD/            # 截图按日期归档
├── img/                         # README 展示图（入库）
│   └── ai_task_manager_01.jpg
├── README.md
├── LICENSE
└── .gitignore
```

---

## 🚀 快速开始

### 1. 环境要求
- **Python 3.8+**（Windows 系统）
- 只需 Python 标准库 + Tkinter（Python 自带）即可运行
- 可选依赖（增强体验，非必须）：
  - `pystray` + `pillow`：系统托盘图标 & 截图
  - `keyboard`：全局热键 Ctrl+Alt+A 截图

### 2. 克隆 & 启动

```bash
git clone https://github.com/fxlsunny/ai-desktop-task-manager.git
cd ai-desktop-task-manager
```

**方式 A：双击 `.bat`（推荐，Windows）**

```
scripts\桌面任务管理.bat
```

> 首次启动会自动从 `config/config.example.json` 生成 `config/config.json`，然后退出并提示你填 API Key。  
> 填好后再次双击即可启动。

**方式 B：命令行**

```bash
# 首次使用：复制配置模板
copy config\config.example.json config\config.json    # Windows
# cp config/config.example.json config/config.json     # Linux/macOS

# 启动
pythonw src\main.py
# 或前台模式（能看日志）
python src\main.py
```

### 3. 安装可选依赖（可跳过）

```
scripts\安装可选依赖.bat
```

或手动：
```bash
python -m pip install pystray pillow keyboard
```

---

## ⚙️ AI 模型配置

### 方式 1：修改 `config/config.json`（不会入库）

打开 `config/config.json`，找到 `ai.providers.<你想用的服务商>.api_key`，填入你的 Key：

```jsonc
{
  "ai": {
    "active_provider": "hunyuan",        // 默认使用腾讯混元
    "providers": {
      "hunyuan": {
        "label": "腾讯混元",
        "api_key": "sk-your-hunyuan-key-here",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "model": "hunyuan-turbos-latest"
      },
      "deepseek": {
        "label": "DeepSeek",
        "api_key": "sk-your-deepseek-key",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
      }
      // ... 其它服务商
    }
  }
}
```

### 方式 2：在程序 UI 里配置（推荐）

启动程序 → 点击 `⚙️ 设置` → 切换到 `🤖 AI 配置` → 下拉选择服务商 → 填入 Key → 保存。

### 方式 3：使用本地 Ollama（完全免费离线）

1. 安装 [Ollama](https://ollama.com)，运行 `ollama pull qwen2:7b`
2. 在 `config/config.json` 里把 `ai.prefer_ollama` 设为 `true`
3. 启动程序，AI 助手会优先走本地 Ollama

### 🔑 获取 API Key 的渠道

| 模型 | 获取地址 | 备注 |
|------|---------|------|
| 腾讯混元 | https://cloud.tencent.com/product/hunyuan | 新用户有免费 Token 额度 |
| Groq | https://console.groq.com/keys | 免费额度充足，推理极快 |
| DeepSeek | https://platform.deepseek.com/api_keys | 低价高质量，国内可直连 |
| Moonshot | https://platform.moonshot.cn/console/api-keys | 新用户赠送额度 |
| OpenAI | https://platform.openai.com/api-keys | 需海外信用卡 |

---

## ⌨️ 快捷键

### 全局
| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Alt+A` | 桌面截图（需 `pip install keyboard`） |

### 放大编辑器（双击任务内容打开）
| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 保存 |
| `Ctrl+Z / Y` | 撤销 / 重做 |
| `Ctrl+F` | 搜索 |
| `Ctrl++ / -` | 放大 / 缩小字号 |
| `Ctrl+滚轮` | 缩放字号 |
| `Esc` | 关闭 |

### 截图标注
| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Z / Y` | 撤销 / 重做 |
| `Ctrl+S` | 保存并插入 |
| `Esc` | 取消 |

---

## 🛡️ 隐私与安全

- **所有数据 100% 本地存储**：任务、对话记录、截图都在 `data/` 目录，不会上传到任何云端
- **API Key 仅用于调用对应 AI 服务商**，程序本身不收集、不上传任何信息
- **配置文件 `config/config.json` 已加入 `.gitignore`**，不会意外上传到仓库
- 如要同步任务到其它设备，可用"备份 → 邮件发送"功能手动同步

---

## 🧪 开发 / 调试

```bash
# 前台启动（能看 print 输出）
python src\main.py

# 单独测某模块
python -c "import sys; sys.path.insert(0,'src'); import config; print(config.load())"
```

### 代码架构速查

- 主循环在 `main.py::main()`，用 Tk mainloop 驱动
- 任务数据流：`models.Store` ← → `data/tasks.json`（原子写入）
- AI 后端抽象：`ai_chat.py` 里 `OllamaBackend` / `OpenAICompatBackend` 实现统一 `stream(messages)` 接口
- 悬浮窗与管理窗通过回调解耦，`_on_cfg_saved` 负责配置变更后的整体刷新

---

## ❓ FAQ

**Q1. 为什么悬浮窗没有透明效果？**  
A. Windows 需要显卡支持 `WS_EX_LAYERED`，几乎所有 Win10/11 机器都支持；如果是远程桌面场景可能被降级，改用"可调透明"滑块即可。

**Q2. 截图后图片保存在哪？**  
A. `data/img/YYYYMMDD/HHMMSS_xxx_桌面管理.jpg`，按日期归档；任务内容里插入的是**相对路径**，即使迁移 data 目录也不坏图。

**Q3. AI 回复很慢？**  
A. 检查三个方向：
- 网络：部分海外 API（OpenAI / Groq）需要科学上网
- 服务商：切换到国内的腾讯混元 / DeepSeek
- 本地：启用 Ollama，离线运行完全无延迟

**Q4. 能不能同步到手机？**  
A. 目前没做移动端；可用"备份 → 邮件发送 zip"功能把 tasks.json 传到手机查看。

**Q5. 能否打包成 exe？**  
A. 可以，用 PyInstaller：  
```bash
pyinstaller --noconsole --onefile --add-data "config/config.example.json;config" src/main.py
```

---

## 📋 路线图

- [x] 多模型 AI 助手 + 会话持久化
- [x] 放大编辑器 + Markdown 预览
- [x] 桌面截图标注 + 任务内联
- [x] 邮件备份
- [ ] 云同步（WebDAV / S3）
- [ ] 移动端查看（只读 Web）
- [ ] 任务看板（Kanban）视图
- [ ] 番茄钟集成

---

## 🤝 贡献

欢迎 issue / PR。代码风格：
- Python 标准库优先，避免引入重型依赖
- 新增功能必须"可降级"：缺少可选依赖时只提示、不崩溃
- 每个 UI 文件保持单一职责（窗口/组件一一对应）

---

## 📜 License

[MIT License](./LICENSE) © 2026 fxlsunny
