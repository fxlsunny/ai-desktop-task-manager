"""
i18n - 极简国际化模块
======================================
- 默认语言 zh_CN，可切换 en_US
- 通过 t("key", **fmt) 取词；找不到键时返回 zh_CN 文本兜底；再没有就返回 key
- set_lang() 由 main.py / 设置面板调用
- 不依赖任何第三方库，跨平台

使用约定：
    from i18n import t, set_lang, current_lang
    btn = tk.Button(text=t("manager.btn.new"))
"""
from __future__ import annotations
from typing import Any

DEFAULT_LANG = "zh_CN"
SUPPORTED = ("zh_CN", "en_US")

LANG_LABELS = {
    "zh_CN": "中文 (Chinese)",
    "en_US": "English",
}

# 当前激活语言
_current = DEFAULT_LANG

# ════════════════════════════════════════════════════════════
# 翻译表：key 一律小写、点分；中文为基准
# ════════════════════════════════════════════════════════════
TRANSLATIONS: dict[str, dict[str, str]] = {

    # ─── 通用 ────────────────────────────────────────────
    "common.app_name":         {"zh_CN": "桌面任务管家",         "en_US": "AI Desktop Task Manager"},
    "common.ok":               {"zh_CN": "确定",                 "en_US": "OK"},
    "common.cancel":           {"zh_CN": "取消",                 "en_US": "Cancel"},
    "common.save":             {"zh_CN": "保存",                 "en_US": "Save"},
    "common.delete":           {"zh_CN": "删除",                 "en_US": "Delete"},
    "common.edit":             {"zh_CN": "编辑",                 "en_US": "Edit"},
    "common.close":            {"zh_CN": "关闭",                 "en_US": "Close"},
    "common.yes":              {"zh_CN": "是",                   "en_US": "Yes"},
    "common.no":               {"zh_CN": "否",                   "en_US": "No"},
    "common.tip":              {"zh_CN": "提示",                 "en_US": "Tip"},
    "common.warn":             {"zh_CN": "警告",                 "en_US": "Warning"},
    "common.error":            {"zh_CN": "错误",                 "en_US": "Error"},
    "common.success":          {"zh_CN": "成功",                 "en_US": "Success"},
    "common.failed":           {"zh_CN": "失败",                 "en_US": "Failed"},
    "common.loading":          {"zh_CN": "加载中…",              "en_US": "Loading…"},
    "common.copy":             {"zh_CN": "复制",                 "en_US": "Copy"},
    "common.copy_selection":   {"zh_CN": "复制选中",             "en_US": "Copy selection"},
    "common.copy_all":         {"zh_CN": "复制整条",             "en_US": "Copy all"},
    "common.browse":           {"zh_CN": "浏览…",                "en_US": "Browse…"},
    "common.confirm":          {"zh_CN": "确认",                 "en_US": "Confirm"},
    "common.exit":             {"zh_CN": "退出",                 "en_US": "Exit"},
    "common.exit_confirm":     {"zh_CN": "确定要退出{app}吗？",  "en_US": "Quit {app}?"},
    "common.detect":           {"zh_CN": "检测",                 "en_US": "Detect"},
    "common.preview_empty":    {"zh_CN": "（预览为空）",         "en_US": "(Preview is empty)"},
    "common.untitled":         {"zh_CN": "新对话",               "en_US": "New chat"},
    "common.required":         {"zh_CN": "*",                    "en_US": "*"},

    # ─── 优先级 ─────────────────────────────────────────
    "pri.urgent":              {"zh_CN": "紧急",                 "en_US": "Urgent"},
    "pri.high":                {"zh_CN": "高",                   "en_US": "High"},
    "pri.mid":                 {"zh_CN": "中",                   "en_US": "Medium"},
    "pri.low":                 {"zh_CN": "低",                   "en_US": "Low"},
    "pri.urgent.tip":          {"zh_CN": "⚠ 立即行动",           "en_US": "⚠ Act now"},
    "pri.high.tip":            {"zh_CN": "● 优先处理",           "en_US": "● High priority"},
    "pri.mid.tip":             {"zh_CN": "◑ 正常安排",           "en_US": "◑ Normal"},
    "pri.low.tip":             {"zh_CN": "○ 可以推迟",           "en_US": "○ Can defer"},

    # ─── 悬浮窗 ─────────────────────────────────────────
    "overlay.title":           {"zh_CN": "桌面任务管家",         "en_US": "Task Manager"},
    "overlay.show":            {"zh_CN": "显示:",                "en_US": "Show:"},
    "overlay.todo":            {"zh_CN": "待办",                 "en_US": "Todo"},
    "overlay.all":             {"zh_CN": "全部",                 "en_US": "All"},
    "overlay.empty":           {"zh_CN": "暂无待办任务\n点击 ＋ 添加",
                                "en_US": "No tasks yet\nClick ＋ to add"},
    "overlay.status":          {"zh_CN": "待办 {active} / 共 {total} 项  ·  双击管理",
                                "en_US": "Todo {active} / Total {total}  ·  Double-click to manage"},
    "overlay.today":           {"zh_CN": "今天",                 "en_US": "Today"},
    "overlay.days":            {"zh_CN": "{n}天",                "en_US": "{n}d"},
    "overlay.tip_ai":          {"zh_CN": "AI 助手",              "en_US": "AI Assistant"},

    # ─── 任务管理窗 - 通用 ──────────────────────────────
    "manager.title":           {"zh_CN": "桌面任务管家 · 管理",  "en_US": "AI Desktop Task Manager · Manager"},
    "manager.tab.list":        {"zh_CN": "📋 任务列表",          "en_US": "📋 Tasks"},
    "manager.tab.edit":        {"zh_CN": "✏️ 新建/编辑",          "en_US": "✏️ New / Edit"},
    "manager.tab.trash":       {"zh_CN": "🗑 回收站",            "en_US": "🗑 Trash"},
    "manager.tab.cfg":         {"zh_CN": "⚙️ 设置",              "en_US": "⚙️ Settings"},
    "manager.tab.bkp":         {"zh_CN": "💾 备份/恢复",          "en_US": "💾 Backup / Restore"},

    # 列表 Tab
    "manager.btn.new":         {"zh_CN": "＋ 新建",              "en_US": "＋ New"},
    "manager.btn.edit":        {"zh_CN": "✏️ 编辑",               "en_US": "✏️ Edit"},
    "manager.btn.toggle":      {"zh_CN": "✔ 完成",               "en_US": "✔ Done"},
    "manager.btn.delete":      {"zh_CN": "🗑 删除",              "en_US": "🗑 Delete"},
    "manager.filter.label":    {"zh_CN": "筛选:",                "en_US": "Filter:"},
    "manager.filter.all":      {"zh_CN": "全部",                 "en_US": "All"},
    "manager.filter.todo":     {"zh_CN": "待办",                 "en_US": "Todo"},
    "manager.filter.done":     {"zh_CN": "已完成",               "en_US": "Done"},
    "manager.col.title":       {"zh_CN": "任务标题",             "en_US": "Title"},
    "manager.col.priority":    {"zh_CN": "优先级",               "en_US": "Priority"},
    "manager.col.progress":    {"zh_CN": "进度",                 "en_US": "Progress"},
    "manager.col.status":      {"zh_CN": "状态",                 "en_US": "Status"},
    "manager.col.elapsed":     {"zh_CN": "耗时(天)",             "en_US": "Elapsed (d)"},
    "manager.col.alarm":       {"zh_CN": "提醒时间",             "en_US": "Reminder"},
    "manager.col.tags":        {"zh_CN": "标签",                 "en_US": "Tags"},
    "manager.col.created":     {"zh_CN": "创建时间",             "en_US": "Created"},
    "manager.col.updated":     {"zh_CN": "更新时间",             "en_US": "Updated"},
    "manager.status.done":     {"zh_CN": "✔ 已完成",             "en_US": "✔ Done"},
    "manager.status.todo":     {"zh_CN": "○ 待办",               "en_US": "○ Todo"},
    "manager.ctx.set_progress":{"zh_CN": "📊 设置进度  (当前{pct}%)",
                                "en_US": "📊 Set progress  (current {pct}%)"},
    "manager.ctx.set_priority":{"zh_CN": "🔥 设置优先级  (当前{label})",
                                "en_US": "🔥 Set priority  (current {label})"},
    "manager.ctx.mark_todo":   {"zh_CN": "○ 标记为待办",         "en_US": "○ Mark as todo"},
    "manager.ctx.mark_done":   {"zh_CN": "✔ 标记为完成",         "en_US": "✔ Mark as done"},
    "manager.ctx.edit":        {"zh_CN": "✏️ 编辑任务",           "en_US": "✏️ Edit task"},
    "manager.ctx.trash":       {"zh_CN": "🗑 移入回收站",         "en_US": "🗑 Move to trash"},
    "manager.msg.select_first":{"zh_CN": "请先选中一条任务",     "en_US": "Please select a task first"},
    "manager.msg.trash_confirm":{"zh_CN":"将任务「{title}」移入回收站（可恢复）？",
                                "en_US":"Move task '{title}' to trash (can be restored)?"},
    "manager.msg.trash_title": {"zh_CN": "移入回收站",            "en_US": "Move to trash"},

    # 编辑 Tab
    "edit.title.label":        {"zh_CN": "任务标题 *",           "en_US": "Title *"},
    "edit.content.label":      {"zh_CN": "任务内容  (支持 Markdown)",
                                "en_US": "Content  (Markdown supported)"},
    "edit.btn.expand":         {"zh_CN": "🔍 放大编辑",           "en_US": "🔍 Expand editor"},
    "edit.btn.shot":           {"zh_CN": "📷 截图",              "en_US": "📷 Screenshot"},
    "edit.goal.label":         {"zh_CN": "目标",                 "en_US": "Goal"},
    "edit.problem.label":      {"zh_CN": "问题/障碍",            "en_US": "Problem / Obstacle"},
    "edit.tags.label":         {"zh_CN": "标签（逗号分隔）",     "en_US": "Tags (comma-separated)"},
    "edit.priority.section":   {"zh_CN": "⚡ 轻重缓急",          "en_US": "⚡ Priority"},
    "edit.completed.section":  {"zh_CN": "✅ 完成状态",           "en_US": "✅ Completion"},
    "edit.completed.checkbox": {"zh_CN": "  标记为已完成",       "en_US": "  Mark as completed"},
    "edit.progress.section":   {"zh_CN": "📊 任务进度",          "en_US": "📊 Progress"},
    "edit.alarm.section":      {"zh_CN": "⏰ 提醒设置",          "en_US": "⏰ Reminder"},
    "edit.alarm.date_label":   {"zh_CN": "提醒日期（留空=每天）","en_US": "Date (empty = every day)"},
    "edit.alarm.time_label":   {"zh_CN": "提醒时间（HH:MM）",    "en_US": "Time (HH:MM)"},
    "edit.alarm.example":      {"zh_CN": "例：09:30",            "en_US": "e.g. 09:30"},
    "edit.btn.save":           {"zh_CN": "💾 保存任务",           "en_US": "💾 Save task"},
    "edit.btn.clear":          {"zh_CN": "🗑 清空表单",           "en_US": "🗑 Clear form"},
    "edit.hint.shortcut":      {"zh_CN": "Ctrl+S 保存",          "en_US": "Ctrl+S to save"},
    "edit.msg.empty_title":    {"zh_CN": "任务标题不能为空",     "en_US": "Title cannot be empty"},
    "edit.msg.bad_time":       {"zh_CN": "提醒时间格式应为 HH:MM","en_US": "Reminder time must be HH:MM"},
    "edit.msg.bad_date":       {"zh_CN": "提醒日期格式应为 YYYY-MM-DD",
                                "en_US": "Reminder date must be YYYY-MM-DD"},
    "edit.msg.saved":          {"zh_CN": "✔ 已保存",             "en_US": "✔ Saved"},
    "edit.msg.editing":        {"zh_CN": "  ✏️ 编辑中：{title}   (ID: {id})",
                                "en_US": "  ✏️ Editing: {title}   (ID: {id})"},
    "edit.msg.created_today":  {"zh_CN": "今天创建",             "en_US": "Created today"},
    "edit.msg.created_days":   {"zh_CN": "已创建 {n} 天",        "en_US": "Created {n} d ago"},
    "edit.msg.times_summary":  {"zh_CN": "创建: {c}  更新: {u}  {elapsed}",
                                "en_US": "Created: {c}  Updated: {u}  {elapsed}"},
    "edit.msg.shot_inserted":  {"zh_CN": "  📷 已插入截图：{name}",
                                "en_US": "  📷 Inserted screenshot: {name}"},
    "edit.msg.shot_failed":    {"zh_CN": "截图模块加载失败：{e}\n请确认已安装 Pillow: pip install pillow",
                                "en_US": "Screenshot module failed: {e}\nMake sure Pillow is installed: pip install pillow"},
    "edit.msg.shot_unavail":   {"zh_CN": "截图不可用",            "en_US": "Screenshot unavailable"},
    "edit.msg.md_failed":      {"zh_CN": "无法加载 Markdown 编辑器：{e}",
                                "en_US": "Cannot load Markdown editor: {e}"},
    "edit.msg.from_editor":    {"zh_CN": "  ✏️ 内容已从放大编辑器更新（{n} 字符）",
                                "en_US": "  ✏️ Content updated from expanded editor ({n} chars)"},
    "edit.placeholder.date":   {"zh_CN": "YYYY-MM-DD",           "en_US": "YYYY-MM-DD"},
    "edit.title.hint":         {"zh_CN": "任务内容",             "en_US": "Task content"},
    "edit.window.title":       {"zh_CN": "📝 编辑任务内容 — {hint}",
                                "en_US": "📝 Edit task content — {hint}"},

    # 回收站 Tab
    "trash.btn.restore":       {"zh_CN": "♻ 恢复选中",            "en_US": "♻ Restore selected"},
    "trash.btn.purge":         {"zh_CN": "💀 永久删除",           "en_US": "💀 Delete permanently"},
    "trash.btn.purge_all":     {"zh_CN": "🗑 清空回收站",         "en_US": "🗑 Empty trash"},
    "trash.count":             {"zh_CN": "回收站共 {n} 条",       "en_US": "{n} items in trash"},
    "trash.empty":             {"zh_CN": "回收站为空",            "en_US": "Trash is empty"},
    "trash.col.deleted_at":    {"zh_CN": "删除时间",              "en_US": "Deleted at"},
    "trash.col.elapsed":       {"zh_CN": "创建耗时",              "en_US": "Age"},
    "trash.col.original":      {"zh_CN": "原状态",                "en_US": "Original status"},
    "trash.msg.select_restore":{"zh_CN": "请先选中要恢复的任务",  "en_US": "Please select a task to restore"},
    "trash.msg.restored":      {"zh_CN": "已恢复",                "en_US": "Restored"},
    "trash.msg.restored_body": {"zh_CN": "任务「{title}」已恢复到任务列表",
                                "en_US": "Task '{title}' restored"},
    "trash.msg.purge_title":   {"zh_CN": "永久删除",              "en_US": "Delete permanently"},
    "trash.msg.purge_body":    {"zh_CN": "将彻底删除「{title}」，此操作不可撤销，确认？",
                                "en_US": "'{title}' will be permanently deleted. This cannot be undone. Continue?"},
    "trash.msg.purge_all":     {"zh_CN": "清空回收站",            "en_US": "Empty trash"},
    "trash.msg.purge_all_body":{"zh_CN": "将永久删除回收站中全部 {n} 条任务，此操作不可撤销，确认？",
                                "en_US": "Permanently delete all {n} items in trash? This cannot be undone."},
    "trash.msg.empty":         {"zh_CN": "回收站已经是空的",      "en_US": "Trash is already empty"},

    # 设置 Tab
    "cfg.section.general":     {"zh_CN": " ⚙️ 常规设置 ",         "en_US": " ⚙️ General "},
    "cfg.section.ai":          {"zh_CN": " 🤖 AI 配置 ",          "en_US": " 🤖 AI Settings "},
    "cfg.data_dir":            {"zh_CN": "数据保存目录",          "en_US": "Data directory"},
    "cfg.data_dir.hint":       {"zh_CN": "当前实际位置: {path}",   "en_US": "Resolved to: {path}"},
    "cfg.opacity":             {"zh_CN": "悬浮窗透明度",          "en_US": "Overlay opacity"},
    "cfg.font_size":           {"zh_CN": "字体大小",              "en_US": "Font size"},
    "cfg.max_show":            {"zh_CN": "悬浮窗最多显示",        "en_US": "Max tasks on overlay"},
    "cfg.always_top":          {"zh_CN": "悬浮窗始终置顶",        "en_US": "Always on top"},
    "cfg.show_done":           {"zh_CN": "悬浮窗显示已完成",      "en_US": "Show completed"},
    "cfg.autostart":           {"zh_CN": "开机自启动",            "en_US": "Run at startup"},
    "cfg.language":            {"zh_CN": "界面语言",              "en_US": "Language"},
    "cfg.language.note":       {"zh_CN": "切换后会重新打开管理窗口",
                                "en_US": "Manager window will reopen after switching"},
    "cfg.ai.tip":              {"zh_CN": "💡 开箱即用：已内置腾讯混元演示 Key，留空 API Key 即自动使用\n   其他选择：Groq 免费 / DeepSeek / Moonshot / OpenAI / 本地 Ollama",
                                "en_US": "💡 Ready to use: built-in Hunyuan demo key works out of the box (leave key empty)\n   Or pick: Groq Free / DeepSeek / Moonshot / OpenAI / local Ollama"},
    "cfg.ai.prefer_ollama":    {"zh_CN": "优先使用本地 Ollama",   "en_US": "Prefer local Ollama"},
    "cfg.ai.ollama_base":      {"zh_CN": "Ollama 地址",           "en_US": "Ollama base URL"},
    "cfg.ai.ollama_model":     {"zh_CN": "Ollama 模型",           "en_US": "Ollama model"},
    "cfg.ai.provider":         {"zh_CN": "云端服务商",            "en_US": "Cloud provider"},
    "cfg.ai.api_key":          {"zh_CN": "API Key",              "en_US": "API Key"},
    "cfg.ai.base_url":         {"zh_CN": "API Base URL",         "en_US": "API Base URL"},
    "cfg.ai.model":            {"zh_CN": "模型名称",              "en_US": "Model"},
    "cfg.ai.note":             {"zh_CN": "💡 未配置 Key 时留空即可，混元会自动使用内置演示 Key",
                                "en_US": "💡 Leave key empty to use the built-in Hunyuan demo key"},
    "cfg.ai.detect_pending":   {"zh_CN": "⏳ 检测 Ollama 中…",     "en_US": "⏳ Detecting Ollama…"},
    "cfg.ai.detect_ok":        {"zh_CN": "✅ Ollama 在线，可用模型：{models}",
                                "en_US": "✅ Ollama online. Available models: {models}"},
    "cfg.ai.detect_no_models": {"zh_CN": "（无模型）",             "en_US": "(no models)"},
    "cfg.ai.detect_fail":      {"zh_CN": "❌ Ollama 未响应（{base}），请确认已启动",
                                "en_US": "❌ Ollama not responding ({base}). Make sure it is running."},
    "cfg.btn.save":            {"zh_CN": "💾 保存所有设置",       "en_US": "💾 Save all settings"},
    "cfg.msg.saved":           {"zh_CN": "✔ 设置已保存",          "en_US": "✔ Settings saved"},
    "cfg.msg.restart_required":{"zh_CN": "界面语言已切换为 {lang}，将重新打开管理器使其生效。",
                                "en_US": "Language changed to {lang}. The manager window will reopen to apply."},
    "cfg.dialog.choose_dir":   {"zh_CN": "选择数据保存目录",      "en_US": "Choose data directory"},

    # 备份 Tab
    "bkp.tip":                 {"zh_CN": "💡 备份会把当前 任务列表 + AI 对话历史 + 配置（脱敏） 打包成单个 .zip 文件；\n   可以直接导出到本地，也可以配置邮箱后一键发送到自己的邮箱，方便跨机器迁移。\n   邮箱授权码 ≠ 登录密码，需要登录 QQ/163 邮箱后台单独开启并生成。",
                                "en_US": "💡 Backup packs your tasks + AI chat history + (sanitized) config into a single .zip;\n   you can export it locally, or send it to your inbox once SMTP is configured.\n   The auth code is NOT your login password — generate it in your mailbox provider's settings."},
    "bkp.section.local":       {"zh_CN": " 📦 本地备份 ",         "en_US": " 📦 Local backup "},
    "bkp.section.email":       {"zh_CN": " 📧 邮箱发送 ",         "en_US": " 📧 Email "},
    "bkp.include_cfg":         {"zh_CN": "  一并备份 config.json（API Key / 授权码将自动脱敏）",
                                "en_US": "  Include config.json (API key / auth code will be sanitized)"},
    "bkp.btn.export":          {"zh_CN": "📤 导出到本地…",        "en_US": "📤 Export…"},
    "bkp.btn.import":          {"zh_CN": "📥 从文件恢复…",        "en_US": "📥 Restore from file…"},
    "bkp.import_hint":         {"zh_CN": "💡 恢复时默认采用「合并」模式：已存在的任务/对话不会被覆盖，\n   只会追加本地缺失的条目，安全无损。",
                                "en_US": "💡 Restore uses 'merge' mode by default: existing tasks/chats are kept,\n   only missing entries are appended — safe and lossless."},
    "bkp.preset_label":        {"zh_CN": "快速选择：",            "en_US": "Presets:"},
    "bkp.smtp_host":           {"zh_CN": "SMTP 服务器",           "en_US": "SMTP host"},
    "bkp.smtp_port":           {"zh_CN": "端口",                  "en_US": "Port"},
    "bkp.sender":              {"zh_CN": "发件邮箱",              "en_US": "Sender"},
    "bkp.auth_code":           {"zh_CN": "授权码",                "en_US": "Auth code"},
    "bkp.recipient":           {"zh_CN": "收件邮箱",              "en_US": "Recipient"},
    "bkp.recipient.hint":      {"zh_CN": "（留空则发给自己）",    "en_US": "(empty → send to self)"},
    "bkp.btn.save_email":      {"zh_CN": "💾 保存邮箱配置",       "en_US": "💾 Save SMTP"},
    "bkp.btn.export_send":     {"zh_CN": "📨 一键备份并发送邮箱", "en_US": "📨 Backup & send email"},
    "bkp.log.section":         {"zh_CN": " 📜 执行日志 ",          "en_US": " 📜 Log "},
    "bkp.log.ready":           {"zh_CN": "就绪。配置好邮箱后即可一键备份发送。",
                                "en_US": "Ready. Configure SMTP, then click the email button."},
    "bkp.log.saved":           {"zh_CN": "✔ 邮箱配置已保存",      "en_US": "✔ SMTP saved"},
    "bkp.dialog.export":       {"zh_CN": "保存备份文件",          "en_US": "Save backup file"},
    "bkp.dialog.import":       {"zh_CN": "选择备份文件",          "en_US": "Choose backup file"},
    "bkp.dialog.zip_filter":   {"zh_CN": "ZIP 备份",              "en_US": "ZIP archive"},
    "bkp.dialog.all":          {"zh_CN": "所有文件",              "en_US": "All files"},
    "bkp.msg.export_ok":       {"zh_CN": "已保存到：\n{path}\n\n任务 {tasks} 条 · 对话 {chats} 个",
                                "en_US": "Saved to:\n{path}\n\n{tasks} tasks · {chats} chats"},
    "bkp.msg.export_failed":   {"zh_CN": "导出失败",              "en_US": "Export failed"},
    "bkp.msg.export_ok_title": {"zh_CN": "导出成功",              "en_US": "Export succeeded"},
    "bkp.msg.choose_mode":     {"zh_CN": "选择恢复模式",          "en_US": "Choose restore mode"},
    "bkp.msg.choose_mode_body":{"zh_CN": "【是】合并恢复（推荐）：保留当前数据，只追加缺失条目\n【否】覆盖恢复：清空现有对话并完全使用备份数据（危险）\n【取消】放弃此次恢复",
                                "en_US": "[Yes] Merge (recommended): keep current data, append missing only\n[No]  Overwrite: clear current chats and use backup completely (DANGEROUS)\n[Cancel] Abort"},
    "bkp.msg.confirm_overwrite":{"zh_CN":"二次确认",              "en_US": "Confirm again"},
    "bkp.msg.confirm_overwrite_body":{"zh_CN":"确定要覆盖现有对话历史吗？此操作不可撤销！",
                                "en_US":"Really overwrite current chat history? This cannot be undone!"},
    "bkp.msg.import_failed":   {"zh_CN": "恢复失败",              "en_US": "Restore failed"},
    "bkp.msg.import_ok_title": {"zh_CN": "恢复完成",              "en_US": "Restore done"},
    "bkp.msg.import_ok_body":  {"zh_CN": "任务：新增 {ti} · 跳过 {ts}\n对话：新增/更新 {ci} · 跳过 {cs}\n\n任务列表已刷新；AI 对话历史将在下次打开 AI 助手时生效。",
                                "en_US": "Tasks: added {ti} · skipped {ts}\nChats: added/updated {ci} · skipped {cs}\n\nTask list refreshed; AI chats reload next time you open the assistant."},
    "bkp.msg.cfg_missing":     {"zh_CN": "配置不完整",            "en_US": "Incomplete SMTP"},
    "bkp.msg.cfg_missing_body":{"zh_CN": "请先填写：{fields}",     "en_US": "Please fill in: {fields}"},
    "bkp.msg.send_started":    {"zh_CN": "🚀 开始一键备份并发送 …","en_US": "🚀 Backup & send started…"},
    "bkp.msg.send_ok_title":   {"zh_CN": "发送成功",              "en_US": "Sent"},
    "bkp.msg.send_ok_body":    {"zh_CN": "备份已发送到 {to}",      "en_US": "Backup sent to {to}"},
    "bkp.msg.send_failed":     {"zh_CN": "发送失败",              "en_US": "Send failed"},
    "bkp.email.subject":       {"zh_CN": "[桌面任务管家备份] {name}",
                                "en_US": "[AI Desktop Task Manager Backup] {name}"},
    "bkp.email.body":          {"zh_CN": "桌面任务管家数据备份\n文件：{name}\n大小：{size}\n生成时间：{ts}\n来源机器：{host}\n\n请妥善保管此附件。在新机器上可通过「管理 → 备份/恢复 → 导入」还原。",
                                "en_US": "AI Desktop Task Manager backup\nFile: {name}\nSize: {size}\nGenerated: {ts}\nFrom host: {host}\n\nKeep this attachment safe. On a new machine, restore via 'Manage → Backup → Import'."},

    # ─── AI 对话窗 ──────────────────────────────────────
    "ai.title":                {"zh_CN": "🤖 AI 智能助手",         "en_US": "🤖 AI Assistant"},
    "ai.btn.rebuild":          {"zh_CN": "🔄 重建连接",           "en_US": "🔄 Rebuild"},
    "ai.label.model":          {"zh_CN": "模型:",                 "en_US": "Model:"},
    "ai.history":              {"zh_CN": "历史对话",              "en_US": "History"},
    "ai.btn.new":              {"zh_CN": "＋ 新建",               "en_US": "＋ New"},
    "ai.history.empty":        {"zh_CN": "（暂无历史对话）\n开始聊天后会自动保存",
                                "en_US": "(No history yet)\nChats are saved automatically"},
    "ai.history.saved_to":     {"zh_CN": "对话自动保存至：\ndata/chat_history/",
                                "en_US": "Chats auto-saved to:\ndata/chat_history/"},
    "ai.status.ready":         {"zh_CN": "就绪",                  "en_US": "Ready"},
    "ai.status.thinking":      {"zh_CN": "AI 正在思考中…",        "en_US": "AI is thinking…"},
    "ai.status.done":          {"zh_CN": "回复完成 · {n} 字  ·  已保存",
                                "en_US": "Reply complete · {n} chars · saved"},
    "ai.status.failed":        {"zh_CN": "发送失败，请检查配置",  "en_US": "Send failed, check config"},
    "ai.btn.send":             {"zh_CN": "发送 ⏎",                "en_US": "Send ⏎"},
    "ai.btn.thinking":         {"zh_CN": "⏳ 思考中",              "en_US": "⏳ Thinking"},
    "ai.hint.shift_enter":     {"zh_CN": "Shift+Enter 换行",       "en_US": "Shift+Enter for newline"},
    "ai.hint.examples":        {"zh_CN": "💡 示例提问（可自由输入任何问题）：",
                                "en_US": "💡 Example prompts (you can ask anything):"},
    "ai.hint.today_tasks":     {"zh_CN": "今日任务建议",          "en_US": "Today's plan"},
    "ai.hint.today_tasks.msg": {"zh_CN": "请帮我分析当前任务的优先级，给出今日工作安排建议",
                                "en_US": "Analyse my current tasks and suggest a daily plan."},
    "ai.hint.time":            {"zh_CN": "时间规划",              "en_US": "Time planning"},
    "ai.hint.time.msg":        {"zh_CN": "如何合理规划每天的时间，提升工作效率？",
                                "en_US": "How can I plan my day to be more productive?"},
    "ai.hint.goal":            {"zh_CN": "目标拆解",              "en_US": "Goal breakdown"},
    "ai.hint.goal.msg":        {"zh_CN": "帮我把一个大目标拆解为可执行的小步骤",
                                "en_US": "Help me split a big goal into actionable steps."},
    "ai.hint.tips":            {"zh_CN": "效率技巧",              "en_US": "Efficiency tips"},
    "ai.hint.tips.msg":        {"zh_CN": "推荐几个提升个人效率的实用方法",
                                "en_US": "Recommend practical methods to boost personal efficiency."},
    "ai.label.you":            {"zh_CN": "👤 你",                 "en_US": "👤 You"},
    "ai.label.ai":             {"zh_CN": "🤖 AI",                 "en_US": "🤖 AI"},
    "ai.label.error":          {"zh_CN": "❌ 错误",                "en_US": "❌ Error"},
    "ai.bk.ollama":             {"zh_CN": "🟢 Ollama 本地 · {m}",   "en_US": "🟢 Local Ollama · {m}"},
    "ai.bk.cloud":              {"zh_CN": "🔵 {disp} · {m}",        "en_US": "🔵 {disp} · {m}"},
    "ai.bk.offline":            {"zh_CN": "⚫ 离线模式（未配置）",   "en_US": "⚫ Offline (not configured)"},
    "ai.welcome.ollama":       {"zh_CN": "已连接本地 Ollama（{m}）",
                                "en_US": "Connected to local Ollama ({m})"},
    "ai.welcome.cloud":        {"zh_CN": "已连接 {label}（{m}）",   "en_US": "Connected to {label} ({m})"},
    "ai.welcome.offline":      {"zh_CN": "当前为离线模式，请在「设置 → AI 配置」填写 API Key",
                                "en_US": "Offline. Please configure an API key in Settings → AI."},
    "ai.welcome.full":         {"zh_CN": "欢迎使用 AI 智能助手 🤖\n当前模式：{mode}\n💬 Enter 发送 / Shift+Enter 换行 · 对话自动保存到 data/chat_history/",
                                "en_US": "Welcome to the AI assistant 🤖\nMode: {mode}\n💬 Enter to send / Shift+Enter for newline · auto-saved to data/chat_history/"},
    "ai.switched":             {"zh_CN": "✅ 已切换到「{label}」",  "en_US": "✅ Switched to '{label}'"},
    "ai.switched.no_key":      {"zh_CN": "⚠ 已切换到「{label}」，但尚未配置 API Key。请到「任务管家 → 设置 → AI 配置」填入。",
                                "en_US": "⚠ Switched to '{label}' but no API key set yet. Add it in Manager → Settings → AI."},
    "ai.rebuilt":              {"zh_CN": "✅ 已重建 AI 连接",      "en_US": "✅ AI connection rebuilt"},
    "ai.history.loaded":       {"zh_CN": "📂 已载入历史对话：{title}\n创建 {c}  ·  更新 {u}  ·  {label} / {model}",
                                "en_US": "📂 History loaded: {title}\nCreated {c}  ·  Updated {u}  ·  {label} / {model}"},
    "ai.history.delete_title": {"zh_CN": "删除对话",              "en_US": "Delete chat"},
    "ai.history.delete_body":  {"zh_CN": "确定删除对话「{title}」？\n此操作不可恢复。",
                                "en_US": "Delete chat '{title}'?\nThis cannot be undone."},
    "ai.history.wait_thinking":{"zh_CN": "AI 正在回复，请等待完成后再切换对话",
                                "en_US": "AI is replying, please wait before switching chats"},
    "ai.history.wait_new":     {"zh_CN": "AI 正在回复，请等待完成后再新建对话",
                                "en_US": "AI is replying, please wait before starting a new chat"},
    "ai.history.read_failed":  {"zh_CN": "对话文件读取失败",      "en_US": "Failed to load chat file"},
    "ai.history.new_done":     {"zh_CN": "已新建对话",            "en_US": "Started a new chat"},
    "ai.history.loaded_status":{"zh_CN": "已载入：{title}",         "en_US": "Loaded: {title}"},
    "ai.history.entry_count":  {"zh_CN": "{ts}  ·  {n} 条",        "en_US": "{ts}  ·  {n} msgs"},

    # ─── Markdown 编辑器 ────────────────────────────────
    "md.view.edit":            {"zh_CN": "✏️ 编辑",                "en_US": "✏️ Edit"},
    "md.view.split":           {"zh_CN": "🗂 分屏",               "en_US": "🗂 Split"},
    "md.view.preview":         {"zh_CN": "👁 预览",                "en_US": "👁 Preview"},
    "md.font.label":           {"zh_CN": "字号:",                 "en_US": "Font:"},
    "md.btn.search":           {"zh_CN": "🔍 搜索 (Ctrl+F)",      "en_US": "🔍 Find (Ctrl+F)"},
    "md.btn.shot":             {"zh_CN": "📷 截图 (Ctrl+Shift+A)","en_US": "📷 Screenshot (Ctrl+Shift+A)"},
    "md.find.prev":            {"zh_CN": "▲ 上一处",              "en_US": "▲ Previous"},
    "md.find.next":            {"zh_CN": "▼ 下一处",              "en_US": "▼ Next"},
    "md.replace.label":        {"zh_CN": "  替换为：",            "en_US": "  Replace with:"},
    "md.replace.cur":          {"zh_CN": "替换当前",              "en_US": "Replace"},
    "md.replace.all":          {"zh_CN": "全部替换",              "en_US": "Replace all"},
    "md.case_sensitive":       {"zh_CN": "区分大小写",            "en_US": "Case sensitive"},
    "md.find.none":            {"zh_CN": "未找到",                "en_US": "Not found"},
    "md.find.replaced":        {"zh_CN": "已替换 {n} 处",         "en_US": "Replaced {n} occurrence(s)"},
    "md.editor.label":         {"zh_CN": "✏️ 编辑",                "en_US": "✏️ Editor"},
    "md.preview.label":        {"zh_CN": "👁 Markdown 预览",      "en_US": "👁 Markdown Preview"},
    "md.bottom.hint":          {"zh_CN": "💡 Ctrl+F 搜索  |  Ctrl+H 替换  |  Ctrl+S 保存  |  Esc 关闭",
                                "en_US": "💡 Ctrl+F find  |  Ctrl+H replace  |  Ctrl+S save  |  Esc close"},
    "md.btn.save_close":       {"zh_CN": "✔ 保存并关闭",          "en_US": "✔ Save & close"},
    "md.stats":                {"zh_CN": "{lines} 行  |  {chars} 字符",
                                "en_US": "{lines} lines  |  {chars} chars"},
    "md.shot_failed":          {"zh_CN": "截图失败",              "en_US": "Screenshot failed"},
    "md.insert_failed":        {"zh_CN": "插入失败",              "en_US": "Insert failed"},
    "md.insert_failed_body":   {"zh_CN": "图片已保存到 {path}\n但插入失败: {e}",
                                "en_US": "Image saved to {path}\nbut insert failed: {e}"},
    "md.image_missing":        {"zh_CN": "⚠️ 图片未找到: {path}",   "en_US": "⚠️ Image not found: {path}"},
    "md.image_failed":         {"zh_CN": "⚠️ 图片加载失败: {path} ({e})",
                                "en_US": "⚠️ Image load failed: {path} ({e})"},
    "md.image_no_pil":         {"zh_CN": "[图片 需要安装 Pillow] {path}",
                                "en_US": "[image — install Pillow] {path}"},

    # ─── 截图 / 标注 ─────────────────────────────────────
    "shot.hint":               {"zh_CN": "🎯 按住鼠标左键拖拽选择区域    |    ESC 取消",
                                "en_US": "🎯 Drag with the left button to select    |    ESC to cancel"},
    "shot.hint.coord":         {"zh_CN": "🎯 鼠标 ({x}, {y})  按住拖拽选择    |    ESC 取消",
                                "en_US": "🎯 Mouse ({x}, {y})  drag to select    |    ESC to cancel"},
    "shot.hint.size":          {"zh_CN": "📐 区域 {w}×{h}（逻辑）    松开完成  ESC 取消",
                                "en_US": "📐 {w}×{h} (logical)    release to confirm  ESC to cancel"},
    "shot.window.title":       {"zh_CN": "📷 截图编辑",            "en_US": "📷 Screenshot Editor"},
    "shot.tools":              {"zh_CN": "🛠 工具",                "en_US": "🛠 Tools"},
    "shot.tool.rect":          {"zh_CN": "▭ 矩形",                "en_US": "▭ Rectangle"},
    "shot.tool.oval":          {"zh_CN": "○ 椭圆",                "en_US": "○ Ellipse"},
    "shot.tool.arrow":         {"zh_CN": "➤ 箭头",                "en_US": "➤ Arrow"},
    "shot.tool.pen":           {"zh_CN": "✎ 画笔",                "en_US": "✎ Pen"},
    "shot.tool.text":          {"zh_CN": "T 文字",                "en_US": "T Text"},
    "shot.tool.mosaic":        {"zh_CN": "▨ 马赛克",              "en_US": "▨ Mosaic"},
    "shot.color":              {"zh_CN": "颜色",                  "en_US": "Color"},
    "shot.color.more":         {"zh_CN": "🎨 更多...",            "en_US": "🎨 More…"},
    "shot.thickness":          {"zh_CN": "粗细",                  "en_US": "Width"},
    "shot.btn.undo":           {"zh_CN": "↶ 撤销 (Ctrl+Z)",       "en_US": "↶ Undo (Ctrl+Z)"},
    "shot.btn.redo":           {"zh_CN": "↷ 重做 (Ctrl+Y)",       "en_US": "↷ Redo (Ctrl+Y)"},
    "shot.btn.clear":          {"zh_CN": "🗑 清空标注",            "en_US": "🗑 Clear annotations"},
    "shot.confirm.clear":      {"zh_CN": "清空所有标注？",        "en_US": "Clear all annotations?"},
    "shot.text.dialog.title":  {"zh_CN": "添加文字",              "en_US": "Add text"},
    "shot.text.dialog.prompt": {"zh_CN": "请输入文字内容：",      "en_US": "Enter text:"},
    "shot.btn.cancel":         {"zh_CN": "取消 (Esc)",            "en_US": "Cancel (Esc)"},
    "shot.btn.save":           {"zh_CN": "💾 保存 (Ctrl+S)",      "en_US": "💾 Save (Ctrl+S)"},
    "shot.filename":           {"zh_CN": "文件名：",              "en_US": "Filename:"},
    "shot.info":               {"zh_CN": "原图尺寸 {w}×{h}  显示比例 {pct}%  ·  保存为 JPEG 品质 90",
                                "en_US": "Source {w}×{h}  zoom {pct}%  ·  saved as JPEG q=90"},
    "shot.cancel.confirm":     {"zh_CN": "有未保存的标注，确定放弃？",
                                "en_US": "There are unsaved annotations. Discard?"},
    "shot.save_failed":        {"zh_CN": "保存失败",              "en_US": "Save failed"},
    "shot.toast.saved":        {"zh_CN": "截图已保存",            "en_US": "Screenshot saved"},
    "shot.toast.saved_body":   {"zh_CN": "已保存到：\n{path}",     "en_US": "Saved to:\n{path}"},
    "shot.tag.suffix":         {"zh_CN": "_桌面管理",              "en_US": "_TaskManager"},
    "shot.alt_prefix":         {"zh_CN": "截图_",                 "en_US": "shot_"},

    # ─── 闹钟 ────────────────────────────────────────────
    "alarm.title":             {"zh_CN": "⏰ 任务提醒",           "en_US": "⏰ Task reminder"},
    "alarm.btn.ack":           {"zh_CN": "知道了",                "en_US": "Got it"},

    # ─── 系统托盘 ────────────────────────────────────────
    "tray.open_manager":       {"zh_CN": "📋 打开管理器",         "en_US": "📋 Open manager"},
    "tray.ai":                 {"zh_CN": "🤖 AI 问答",            "en_US": "🤖 AI assistant"},
    "tray.shot":               {"zh_CN": "📷 截图",                "en_US": "📷 Screenshot"},
    "tray.toggle_overlay":     {"zh_CN": "👁 显示/隐藏悬浮窗",     "en_US": "👁 Show / hide overlay"},
    "tray.quit":               {"zh_CN": "❌ 退出",                "en_US": "❌ Quit"},
}


# ════════════════════════════════════════════════════════════
# API
# ════════════════════════════════════════════════════════════
def set_lang(lang: str) -> str:
    """切换语言。未知值时回落到默认。返回最终生效语言。"""
    global _current
    if lang in SUPPORTED:
        _current = lang
    else:
        _current = DEFAULT_LANG
    return _current


def current_lang() -> str:
    return _current


def t(key: str, **fmt: Any) -> str:
    """取词；找不到时回落 zh_CN，再没有就返回 key。
    fmt 用于 .format(**fmt) 的占位替换。
    """
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key.format(**fmt) if fmt else key
    text = entry.get(_current) or entry.get(DEFAULT_LANG) or key
    if fmt:
        try:
            return text.format(**fmt)
        except Exception:
            return text
    return text


def lang_options() -> list[tuple[str, str]]:
    """返回可供 UI 下拉使用的 [(code, label), ...]"""
    return [(code, LANG_LABELS[code]) for code in SUPPORTED]
