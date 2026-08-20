# Hearth

Hearth 是一个 coding agent 的 **Harness**：给模型工具、工作区、权限和生命周期，不替模型做推理。

模型负责想下一步、选工具。Hearth 负责能不能做、怎么做、何时真正结束。

## 它做什么

一次用户请求跑在**同一个 Agent Loop** 上：调模型 → 有工具调用就执行并写回对话 → 没有工具调用再问 Goal 闸门，通过才把控制权交还给你。

新能力只进两处，不另开循环：

- **Tool Pool**：bash、读写文件、todo、skill、memory、MCP、subagent、Task Graph、Teammate、Cron、Workflow
- **Hook**：提示提交、调用前权限、调用后处理、会话结束

没有 tool_use 不等于任务完成。有活跃 Goal 时，独立判断器只读对话里已有的证据，决定放行、续轮、失败或等后台结束。判断器自己没有工具。

## 现在具备

- 在工作区内改文件、跑命令；路径不得逃出 Workspace
- 危险命令拒绝或询问；MCP 工具进同一工具池，权限看宿主名单
- 长会话压缩、技能按需加载、跨会话记忆
- 后台命令完成后通知写回同一份对话；定时任务至少投递一次
- 跨会话任务图、队友绑定 git worktree（只换工作目录，不是沙箱）
- 宿主注册的 Workflow 脚本；模型只传名称、参数和续跑 ID
- `/goal ...` 续轮直到对话里出现验证证据，或把控制权交还用户

流式 UI、会话持久化、IDE 和沙箱不在当前范围。没有它们也是完整的 Harness。

## 怎么跑

```text
cp .env.example .env   # 填 ANTHROPIC_API_KEY 和 MODEL_ID
pip install -e ".[dev]"
hearth
hearth "列出当前目录里的 Python 文件"
```
