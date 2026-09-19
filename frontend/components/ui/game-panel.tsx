import { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function GamePanel({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('game-panel hud-corners', className)} {...props}>{children}</div>
}
