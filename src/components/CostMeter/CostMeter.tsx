import { cn } from '../../utils/cn'
import { DollarSign, Info } from 'lucide-react'

interface CostMeterProps {
  cost: {
    totalTokens: number;
    inputTokens: number;
    outputTokens: number;
    estimatedCost: number;
    model: string;
  };
}

export function CostMeter({ cost }: CostMeterProps) {
  const isLocal = cost.estimatedCost === 0
  const isCloud = !isLocal

  return (
    <div className={cn(
      'fixed top-20 right-4 z-30 card animate-slide-down',
      'w-64'
    )}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <DollarSign className={cn('w-5 h-5', isCloud ? 'text-green-500' : 'text-gray-500')} />
          <span className="font-medium">Cost Meter</span>
          {isCloud && <span className="text-xs bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">LIVE</span>}
        </div>
      </div>
      
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-dark-bg rounded-lg p-3">
            <div className="text-xs text-gray-500">Total Tokens</div>
            <div className="font-mono text-lg font-semibold">{cost.totalTokens.toLocaleString()}</div>
          </div>
          <div className="bg-dark-bg rounded-lg p-3">
            <div className="text-xs text-gray-500">Est. Cost</div>
            <div className={cn('font-mono text-lg font-semibold', isCloud ? 'text-green-400' : 'text-gray-400')}>
              ${cost.estimatedCost.toFixed(6)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-dark-border">
          <div className="bg-dark-bg rounded-lg p-3">
            <div className="text-xs text-gray-500">Input</div>
            <div className="font-mono text-lg font-semibold text-blue-400">{cost.inputTokens.toLocaleString()}</div>
          </div>
          <div className="bg-dark-bg rounded-lg p-3">
            <div className="text-xs text-gray-500">Output</div>
            <div className="font-mono text-lg font-semibold text-purple-400">{cost.outputTokens.toLocaleString()}</div>
          </div>
        </div>

        <div className="text-xs text-gray-500 flex items-center gap-1">
          <Info className="w-3 h-3" />
          <span>Model: {cost.model}</span>
          {isLocal && <span className="text-green-500">(Local - Free)</span>}
        </div>
      </div>
    </div>
  )
}