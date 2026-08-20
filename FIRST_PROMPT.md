# 贴到新工作区的第一条消息

下面整段复制到 Cursor Agent。工作区根目录必须是本仓库 `hearth/`。

---

你在 Hearth 仓库里。这是一个 coding agent harness：一个 Agent Loop，能力进 Tool Pool 或 Hook。

先读：

- AGENTS.md
- CONTEXT.md
- docs/architecture.md
- docs/phased-plan.md
- docs/adr/*.md
- 现有 `src/hearth/` 和 `tests/`

当前目标是 **做完 MVP**，不要跳到 teams / workflow 产品壳：

1. 补全 `hearth/loop.py` 的 `run_turn`：while True；调 LLM；有 tool_use 则 PreToolUse → handler → PostToolUse → 写回 messages；没有 tool_use 则问 Goal 闸门（默认 allow）再 Stop。
2. 实现 bash、read_file、write_file、edit_file、glob、grep、todo_write。路径锁在 Workspace。
3. Permission 只作为 PreToolUse hook。测试里注入自动放行/拒绝，不要在单测里弹 input()。
4. `LLMClient` 接缝：`AnthropicClient` + `FakeClient`。pytest 只用 FakeClient。
5. CLI：`hearth` 交互；`hearth "任务"` 跑一轮。
6. `pytest` 必须绿。

用 CONTEXT.md 里的词。缩进用 tab。一次只把 MVP 做完整，再停下来告诉我如何填 `.env` 跑一次真模型。

---
