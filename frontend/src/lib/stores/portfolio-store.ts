// Input: 用户持仓操作（添加/加仓合并/删除/更新价格/观察标记）
// Output: 持久化到 localStorage 的持仓列表（含 mode: live|watch；同 code 加仓累加股数、成本加权平均）
// Pos: Zustand store — 投资组合状态；agent 工具只读，不写仓
// 一旦我被修改，请更新我的头部注释，以及所属文件夹的md。

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/** live=实盘持仓；watch=观察组合（仅 UI 标记，agent 不写仓） */
export type HoldingMode = 'live' | 'watch';

export interface Holding {
  code: string;
  name: string;
  shares: number;
  costPrice: number;
  currentPrice?: number;
  addedAt: number;
  /** 可选：默认 live；watch 仅作观察标签 */
  mode?: HoldingMode;
}

interface PortfolioState {
  holdings: Holding[];
  addHolding: (item: Omit<Holding, 'addedAt'>) => void;
  updateHolding: (code: string, patch: Partial<Omit<Holding, 'code' | 'addedAt'>>) => void;
  removeHolding: (code: string) => void;
  updatePrice: (code: string, price: number) => void;
  /** 切换 live/watch 观察标记（仅 UI，agent 不得自动写仓） */
  setHoldingMode: (code: string, mode: HoldingMode) => void;
  getTotalValue: () => number;
  getTotalCost: () => number;
  getTotalPnl: () => number;
}

export const usePortfolioStore = create<PortfolioState>()(
  persist(
    (set, get) => ({
      holdings: [],

      addHolding: (item) =>
        set((state) => {
          const existing = state.holdings.find((h) => h.code === item.code);

          // 同 code 视为「加仓」：合并到原持仓，股数累加、成本按加权平均重算，不产生重复行
          if (existing) {
            const totalShares = existing.shares + item.shares;
            const mergedCost =
              totalShares > 0
                ? (existing.costPrice * existing.shares + item.costPrice * item.shares) /
                  totalShares
                : item.costPrice;
            return {
              holdings: state.holdings.map((h) =>
                h.code === item.code
                  ? {
                      ...h,
                      shares: totalShares,
                      costPrice: Number(mergedCost.toFixed(3)),
                      // 原名缺失时才回填；类型以本次提交为准（其余字段保持原值）
                      name: h.name && h.name !== h.code ? h.name : item.name,
                      mode: item.mode ?? h.mode ?? 'live',
                      currentPrice: h.currentPrice ?? item.currentPrice,
                    }
                  : h
              ),
            };
          }

          return {
            holdings: [
              ...state.holdings,
              { ...item, mode: item.mode ?? 'live', addedAt: Date.now() },
            ],
          };
        }),

      updateHolding: (code, patch) =>
        set((state) => ({
          holdings: state.holdings.map((h) =>
            h.code === code ? { ...h, ...patch } : h
          ),
        })),

      removeHolding: (code) =>
        set((state) => ({
          holdings: state.holdings.filter((h) => h.code !== code),
        })),

      updatePrice: (code, price) =>
        set((state) => ({
          holdings: state.holdings.map((h) =>
            h.code === code ? { ...h, currentPrice: price } : h
          ),
        })),

      setHoldingMode: (code, mode) =>
        set((state) => ({
          holdings: state.holdings.map((h) =>
            h.code === code ? { ...h, mode } : h
          ),
        })),

      getTotalValue: () => {
        const { holdings } = get();
        return holdings.reduce(
          (sum, h) => sum + (h.currentPrice ?? h.costPrice) * h.shares,
          0
        );
      },

      getTotalCost: () => {
        const { holdings } = get();
        return holdings.reduce((sum, h) => sum + h.costPrice * h.shares, 0);
      },

      getTotalPnl: () => {
        const state = get();
        return state.getTotalValue() - state.getTotalCost();
      },
    }),
    {
      name: 'stockanal-portfolio',
      version: 2,
      migrate: (persisted: unknown) => {
        const state = persisted as { holdings?: Holding[] } | null;
        if (!state || !Array.isArray(state.holdings)) return state as PortfolioState;
        return {
          ...state,
          holdings: state.holdings.map((h) => ({
            ...h,
            name: h.name && h.name !== h.code ? h.name : '',
            mode: h.mode === 'watch' ? 'watch' : 'live',
          })),
        };
      },
    }
  )
);
