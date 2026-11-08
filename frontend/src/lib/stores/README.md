文件列表：chat-store / agent-store / portfolio-store / watchlist-store / theme-store / settings-store
地位：Zustand 客户端持久化层,localStorage 化身
功能：对话/Agent实时状态/自选/组合/主题/设置的全局状态管理
约定：portfolio-store.addHolding 对同 code 执行「加仓合并」——股数累加、成本按加权平均重算，不新增重复行

一旦这里的结构发生变化，请务必更新我... 就像重新标记领地一样。
