import * as Tooltip from '@radix-ui/react-tooltip'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  shortcut?: string
  active?: boolean
  children: ReactNode
}

export function IconButton({ label, shortcut, active, className = '', children, ...props }: IconButtonProps) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          aria-label={label}
          aria-pressed={active}
          className={`grid size-10 place-items-center rounded-xl transition-colors duration-150 disabled:opacity-35 ${
            active ? 'bg-amber-500 text-soil-950' : 'text-sand-200 hover:bg-soil-700'
          } ${className}`}
          {...props}
        >
          {children}
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="bottom"
          sideOffset={6}
          className="z-50 rounded-lg bg-soil-700 px-2.5 py-1 text-xs font-semibold text-sand-100 shadow-lg"
        >
          {label}
          {shortcut && <kbd className="ml-2 rounded bg-soil-900 px-1.5 py-0.5 text-sand-400">{shortcut}</kbd>}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  )
}
