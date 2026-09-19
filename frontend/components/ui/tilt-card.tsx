'use client'

import { MouseEvent, ReactNode, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '@/lib/utils'

export function TiltCard({ className, children }: { className?: string; children: ReactNode }) {
  const reduced = useReducedMotion()
  const [rotation, setRotation] = useState({ x: 0, y: 0 })
  const move = (event: MouseEvent<HTMLDivElement>) => {
    if (reduced) return
    const rect = event.currentTarget.getBoundingClientRect()
    setRotation({ x: ((event.clientY - rect.top) / rect.height - .5) * -5, y: ((event.clientX - rect.left) / rect.width - .5) * 5 })
  }
  return <motion.div onMouseMove={move} onMouseLeave={() => setRotation({ x: 0, y: 0 })} animate={{ rotateX: rotation.x, rotateY: rotation.y }} transition={{ type: 'spring', stiffness: 220, damping: 22 }} style={{ transformStyle: 'preserve-3d', perspective: 900 }} className={cn(className)}>{children}</motion.div>
}
