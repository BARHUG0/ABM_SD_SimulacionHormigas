import { AnimatePresence, motion } from 'motion/react'
import { useEffect } from 'react'
import { useUi, type Toast, type ToastTone } from '../sim/ui'

const TONES: Record<ToastTone, string> = {
  info: 'border-sand-400/40',
  success: 'border-leaf-500/70',
  warning: 'border-amber-500/70',
  error: 'border-ember-500/80',
}

const LIFETIME_MS = 3500

function ToastItem({ toast }: { toast: Toast }) {
  const dismiss = useUi((state) => state.dismissToast)
  useEffect(() => {
    const timer = setTimeout(() => dismiss(toast.id), LIFETIME_MS)
    return () => clearTimeout(timer)
  }, [dismiss, toast.id])

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: -12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ duration: 0.2 }}
    >
      <button
        onClick={() => dismiss(toast.id)}
        className={`panel w-full border-l-4 px-4 py-2 text-left text-sm font-semibold text-sand-100 ${TONES[toast.tone]}`}
      >
        {toast.text}
      </button>
    </motion.li>
  )
}

export function Toasts() {
  const toasts = useUi((state) => state.toasts)
  return (
    <div role="status" aria-live="polite" className="pointer-events-auto absolute top-24 left-1/2 z-30 w-80 -translate-x-1/2">
      <ul className="flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} />
          ))}
        </AnimatePresence>
      </ul>
    </div>
  )
}
