# 扩展走 Hook，不改循环分支

权限、审计、日志、Goal 闸门都注册到 `UserPromptSubmit` / `PreToolUse` / `PostToolUse` / `Stop`。循环只负责：调模型、看有没有 tool_use、触发 hook、分发 handler、写回 messages。

把 `if name == "bash": ask_user()` 写进 dispatch 行，每个新工具都要复制策略，循环会变成业务清单。

**Status**: accepted
