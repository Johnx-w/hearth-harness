# Goal 是退出闸门，不是新循环

「没有 tool_use」只表示本轮想停。有活跃 Goal 时，独立 Evaluator 阅读对话再决定是否真的 return。未完成则把理由追加进同一份 `messages[]` 后 continue。后台或 Workflow 还在跑则 `defer`，不调用 Evaluator。

不为 Goal 再开循环或队列：谁做决定（Evaluator）和决定从哪路回来（还是这条 loop）必须分开。判断器没有工具，不能自己跑测试。

**Status**: accepted
