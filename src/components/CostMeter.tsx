import { cn } from '../../utils/cn'
import { TrendingUp, DollarSign } from 'lucide-react'

interface CostMeterProps {
  cost: {
    totalTokens: number
    promptTokens: number
    completionTokens: number
    totalCost: number
  }
}

export function CostMeter({ cost }: CostMeterProps) {
  if (cost.totalTokens === 0) return null

  return (
    <div className={cn('fixed bottom-4 right-4 z-20 animate-slide-up')}>
      <div className="card flex items-center gap-3 p-3 min-w-[280px] shadow-lg">
        <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
          <DollarSign className="w-4 h-4 text-primary-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium text-gray-100">Session Cost</span>
            <TrendingUp className="w-4 h-4 text-green-500" />
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>${cost.totalCost.toFixed(4)}</span>
            <span className="text-gray-600">{cost.totalTokens.toLocaleString()} tokens</span>
            <span className="text-gray-600">{cost.promptTokens.toLocaleString()} in / {cost.completionTokens.toLocaleString()} out</span>
          </div>
        </div>
      </div>
    </div>
  )
}