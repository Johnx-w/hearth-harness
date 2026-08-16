# 架构

Hearth = 一个 Agent Loop + 挂在循环上的 Harness 机制。模型决定调用什么；Harness 决定能不能做、怎么做、何时真正结束。

```text
用户输入
  → UserPromptSubmit
  → cron / background 通知注入 messages[]
  → Compaction
  → 组装 system prompt（identity / 工具 / workspace / skills 目录 / memory）
  → 组装 Tool Pool
  → LLM
  → 有 tool_use?
        是 → PreToolUse（Permission）
            → handler 或后台占位 或 MCP 或 Workflow
            → PostToolUse
            → tool_result 写回 messages[]
            → 下一轮
        否 → Goal 闸门（无活跃 Goal 则直接 Stop）
            → block：理由写回 messages[]，继续
            → defer：等后台通知
            → allow / achieved / failed / error：Stop hook，返回
```

## 模块与接缝

深度模块：调用方只依赖小接口；复杂实现藏在模块内。循环不 import 各工具的内部细节。

| 模块 | 接口（调用方必须知道的） | 实现藏什么 | 接缝 |
|------|--------------------------|------------|------|
| `loop` | `run_turn(session) -> TurnResult` | 注入、压缩、调模型、分发、Goal | 唯一主循环 |
| `tools.pool` | `assemble() -> (schemas, handlers)` | 内置 + MCP + Workflow 合并、名称冲突 | 每轮重装 |
| `hooks` | `register` / `emit`；非 None 可短路 | 回调顺序 | 四类事件 |
| `permission` | 作为 `PreToolUse` 注册 | deny 列表、路径逃逸、询问、MCP 策略 | 策略 adapter |
| `llm` | `complete(...) -> LLMResponse` | Anthropic SDK、重试 | FakeClient / AnthropicClient |
| `goal` | `evaluate_after_turn(messages, background) -> StopDecision` | Evaluator 调用、block 上限 | 无 Goal 时恒 allow |
| `workflow` | handler `Workflow(name, args, resume_from_run_id)` | 脚本、journal、parallel/pipeline | 宿主 registry |
| `cli` | 读用户输入、打印、确认权限 | 终端细节 | 以后可换 TUI/IDE |

后续模块（v1/v2）同样只通过 Tool Pool 或 Hook 接入，不新增循环：`memory`、`skills`、`compact`、`background`、`cron`、`tasks`、`teams`、`mcp`。

## 依赖方向

```text
cli → loop → llm
         → hooks → permission
         → tools.pool → bash / filesystem / todo / (mcp) / (workflow)
         → compact / memory / skills   （LLM 前）
         → goal                        （无 tool_use 时）
         → background / cron           （注入 messages）
```

禁止：工具 handler import `loop`；Goal Evaluator 调用工具；Workflow 脚本直接 shell/写文件（只通过 `agent()` 等原语）。

## 运行时数据

- **会话态**：`messages[]`、当前 Todo、活跃 Goal、token 计数
- **工作区文件**：`.memory/`、`.tasks/`、`.skills/`（v1+）
- **Workflow**：`.runtime/<runId>.json` + `.journal.jsonl`（v2）
- **不持久化（MVP）**：整段聊天；Goal 进程内有效

## 刻意不做（直到对应阶段）

- 第二条监督循环、把 Workflow 当主循环、拼接课程 `code.py`
- 把 Worktree 当成沙箱
- 信任 MCP 工具 description 作为授权
- 为 Goal 设私有 turn 预算（用全局 `max_turns` + Stop hook block 上限）
