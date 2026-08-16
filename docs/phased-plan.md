# 阶段计划

每次只把一个机制接进同一个 loop。做完再开下一阶段。

## MVP（骨架已可跑，循环与工具有单测）

可对真实仓库改文件、跑命令、列 todo。无 API 时用 FakeClient 测循环。`pytest` 当前应全绿。

- [x] 包结构、CONTEXT、ADR、Agent 指令
- [x] `run_turn`：while True + tool_use 分发
- [x] bash / read_file / write_file / edit_file / glob / grep
- [x] Hooks 四事件
- [x] Permission：路径不出 Workspace；危险命令拒绝或询问
- [x] todo_write
- [x] 交互 CLI
- [x] FakeClient 单测不打网

完成标准：填 `.env` 后 `hearth --yes "列出当前目录的 Python 文件"` 能对真实模型跑通。然后进入 v1。

## v1 长期工作

- compact（LLM 前）
- skills 目录 + load_skill
- memory 筛选 / 提取 / 整理
- 一次性 subagent（独立 messages，只回摘要）
- bash `run_in_background` + 通知注入
- 真实 MCP → 同一 Tool Pool
- 429/529 重试；prompt too long 再 compact

完成标准：一次长会话不炸上下文；`connect_mcp` 后下一轮出现 `mcp__*` 工具。

## v2 编排与收口

- Task Graph 文件
- Teammate + 任务绑定 Worktree（记住：不是沙箱）
- Cron 至少一次投递
- Workflow 工具 + journal 续跑
- Goal 闸门接到 return；后台未完成则 defer

完成标准：`/goal pytest 退出码 0` 会自动续轮直到对话里出现证据，或把控制权交还用户。

## 产品层（有意排最后）

流式 UI、会话持久化、IDE、沙箱、遥测。没有这些也可以是完整 Harness；有了才像「产品」。
