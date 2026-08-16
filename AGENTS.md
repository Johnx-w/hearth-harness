# Agent 指令

你在写 **Hearth**，一个类 Claude Code 的 Harness。打开本仓库就是开工，不要去拼接 `learn-claude-code` 的 `s15/s16/s17/code.py`。

## 每次动手前

1. 读 [CONTEXT.md](CONTEXT.md)，用里面的词，不要另造同义词。
2. 读 [docs/architecture.md](docs/architecture.md) 和 [docs/phased-plan.md](docs/phased-plan.md)，只做当前阶段。
3. 循环形状以 `hearth/loop.py` 为准：有 tool_use 就执行写回；没有则走 Goal 闸门再 Stop。

## 硬规则

- **一个 loop。** 不为监督、定时、Goal、Workflow 再开 `while True` 调主模型。
- **扩展走接缝。** 新工具注册进 `assemble_tool_pool`；策略注册进 Hooks。禁止在 dispatch 行堆 `if tool_name == ...` 业务。
- **Permission 是 PreToolUse。** 文件路径必须落在 Workspace 内。危险 bash 先拒绝或询问。异步轮次不得抢交互确认。
- **Goal Evaluator 无工具。** 它只读 `messages[]`。验证命令由主模型跑，证据必须出现在对话里。
- **Workflow 不能提交代码。** 模型只传 name / args / resume_from_run_id。脚本由宿主 registry 提供。
- **Worktree ≠ 沙箱。** 只换 cwd。删除 worktree 是宿主操作，不暴露给模型。
- **MCP 权限看宿主名单。** 不要把 server 写的 description 当授权。
- **缩进用 tab。** Python 3.11+。不要引入未写入 `pyproject.toml` 的依赖。
- **先测后接真 API。** 循环行为用 `FakeClient` 覆盖；不要为了测 loop 打网。

## 当前阶段

MVP：让 `run_turn` + 文件/bash 工具 + hooks/permission + todo + CLI 可跑。`compact` / `memory` / `mcp` / `workflow` / `teams` 保持空操作或明确桩，直到 phased-plan 进入对应阶段。

Goal 接口已经留在 loop 退出点；MVP 的默认闸门无活跃 Goal 时直接 `allow`。

## 不要做

- 复制课程单文件、把三个章节 cat 在一起
- 在 README 里声称这是 Claude Code
- 一次 PR 做完 v1+v2+产品层
- 用 markdown 表格替代该写的代码；计划已在 `docs/`，继续实现即可
