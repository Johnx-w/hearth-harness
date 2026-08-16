# 与 learn-claude-code 的对应

课程仓库是教学标本。本仓库按规格重写。不要复制章节文件。

| 课程 | 机制 | 本仓库落点 | 阶段 |
|------|------|------------|------|
| s01 | Agent Loop + bash | `hearth/loop.py` + `tools/bash.py` | MVP |
| s02 | 加工具只加 handler | `tools/pool.py` | MVP |
| s03 | Permission | `permission.py` 注册为 PreToolUse | MVP |
| s04 | Hooks | `hooks.py` | MVP |
| s05 | Todo | `tools/todo.py` | MVP |
| s06 | Subagent | `tools/subagent.py` | v1 |
| s07 | Skills | `skills.py` + `load_skill` | v1 |
| s08 | Compaction | `compact.py` | v1 |
| s09 | Memory | `memory.py` | v1 |
| s10 | Task Graph | `tasks.py` | v2 |
| s11 | Background | `background.py` | v1 |
| s12 | Cron | `cron.py` | v2 |
| s13 | Teams + Worktree | `teams.py` | v2 |
| s14 | MCP | `mcp.py`（接真实 SDK，课程是 mock） | v1 |
| s15 | 集成宿主 | 本仓库的包结构，不是单文件 | 全程 |
| s16 | Workflow Runtime | `workflow/` 打进 Tool Pool | v2 |
| s17 | Goal Loop | `goal.py` 接到 loop 退出点 | v2（接口 MVP 已留） |

## 组装方式（不要 cat 三个文件）

```text
宿主 = 重写后的 s15 循环
s16  = assemble_tool_pool 的补丁，加入 Workflow
s17  = 无 tool_use 时调用 Goal.evaluate_after_turn
```

s17 课程代码是缩小的 kernel（约 5 个工具），用来看清闸门。把 Goal 接到本宿主，不要用 s17 覆盖本仓库。

## 课程有、产品没有、这里要自己补

- 流式 token 输出与工具调用实时展示
- 会话落盘与恢复
- TUI / 编辑器扩展
- 真正沙箱（seccomp、容器、OS 权限）；Worktree 只换 cwd
- 生产级 system prompt 与工具描述
- 真实 MCP 传输（stdio/SSE），不是 mock server
