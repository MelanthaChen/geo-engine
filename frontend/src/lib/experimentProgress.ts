import { STRATEGY_LABELS, type OptimizationStrategy } from "@/lib/predictorStrategies";
import type { StrategyId } from "@/types/experimentLab";

export function validationRepetitionLabel(
  strategy: StrategyId,
  current: number,
  total: number,
) {
  const strategyLabel = strategy === "original"
    ? "Original"
    : STRATEGY_LABELS[strategy as OptimizationStrategy] || strategy;
  return `${strategyLabel} • repetition ${current}/${total}`;
}
