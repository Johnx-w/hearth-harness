# Hearth

Hearth 是一个 coding agent 的 **Harness**：给模型工具、工作区、权限和生命周期，不替模型做推理。模型是 intelligence，本仓库是栖居环境。

## Language

**Harness**：
围绕一次 Agent Loop 搭建的运行时：工具、权限、压缩、记忆、调度、编排、完成判断。
_Avoid_: 框架, 平台, Agent 本身, 中间件

**Agent Loop**：
同一份 `messages[]` 上的 `while True`：调模型 → 若有 tool_use 则执行并写回 → 否则考虑结束。
_Avoid_: 工作流引擎, 多 Agent 编排器, 状态机

**Tool Use**：
模型在响应里发出的结构化调用。有它就继续循环；没有它只表示本轮想停，不表示目标已完成。
_Avoid_: Function calling（可作实现细节，不作领域词）

**Tool Pool**：
每一轮组装的工具 schema + handler 映射。内置工具和 MCP 工具进同一个池。
_Avoid_: 插件列表, API 集合

**Hook**：
循环上的插口，不写进循环分支。事件：`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`Stop`。
_Avoid_: 中间件, 回调总线, 插件系统

**Permission**：
挂在 `PreToolUse` 上的策略：拒绝、询问或放行。不是工具 handler 内部的 if。
_Avoid_: 鉴权, Auth, 沙箱（沙箱是隔离执行，Permission 是允不允许）

**Workspace**：
工具默认工作目录。文件路径不得逃出该根。
_Avoid_: 沙箱, worktree（worktree 是任务级额外工作副本）

**Subagent**：
一次性派发：独立 `messages[]`，中间过程丢弃，只把最终摘要当一条 tool_result 返回。
_Avoid_: 队友, 子进程, 线程

**Teammate**：
持久协作线程。按 WORK → 结果 → IDLE 运行，可认领任务、收发消息。
_Avoid_: Subagent, worker, 微服务

**Task Graph**：
跨会话、带依赖、可认领的持久任务记录（文件）。不是会话内的 todo 清单。
_Avoid_: Todo, 工单, Issue

**Todo**：
当前会话内的轻量步骤表，整表替换，防漂移。不跨会话。
_Avoid_: Task Graph, 计划文档

**Worktree**：
绑定到某个 Task 的独立 git 工作副本，只改变工具的默认 cwd。不是安全沙箱。
_Avoid_: 沙箱, 容器, Workspace（Workspace 是宿主根目录）

**Skill**：
按需加载的操作说明。System prompt 只放目录，完整正文经 `load_skill` 展开。
_Avoid_: 插件, Prompt 模板, RAG 文档

**Memory**：
跨会话该记住的记录：筛选进本轮、回合后提取、必要时整理。
_Avoid_: 上下文, 聊天记录, 向量库（存储可选，概念不是检索）

**Compaction**：
上下文将满时腾地方：先裁工具结果，再摘要历史。发生在调用模型之前。
_Avoid_: 压缩文件, 总结（总结只是最后一步）

**Background Task**：
显式标记的慢操作。主循环先返回占位 tool_result，完成后以通知写回同一份 `messages[]`。
_Avoid_: 异步 Agent, 队列消费者

**Cron**：
按时间把 prompt 注入 `messages[]`。交付至少一次；不另开一条 Agent 循环。
_Avoid_: 定时 Agent, crontab 守护进程（实现可以是 daemon thread）

**MCP Tool**：
外部服务器提供的工具，进入同一 Tool Pool，名称 `mcp__server__tool`。权限由宿主策略决定，不信任服务器自己的 description。
_Avoid_: 插件, HTTP API, 函数调用

**Workflow**：
宿主注册的可信脚本。一次 tool_use 跑完整套编排；模型只传名称、参数和可选续跑 ID。
_Avoid_: Agent Loop, 多 Agent 系统, 聊天里凑出来的步骤

**Journal**：
Workflow 里每个 `agent()` 调用的稳定键缓存。续跑时未改动的调用直接复用。
_Avoid_: 日志, 审计, 聊天历史

**Goal**：
会话级完成条件。模型不再 tool_use 时，由独立判断器阅读对话，决定放行、阻止并续轮、判定失败或推迟。
_Avoid_: 任务, Todo, 停止原因, 测试框架

**Goal Evaluator**：
另一次、无工具的模型调用，只根据对话里已出现的证据判断 Goal 是否满足。
_Avoid_: 主模型, 监督者 Agent, 测试运行器

**Stop Decision**：
Goal 闸门的输出：`allow` / `block` / `achieved` / `failed` / `defer` / `error`。`block` 把理由写回同一份 `messages[]` 再 continue。
_Avoid_: return, 异常, 用户命令
