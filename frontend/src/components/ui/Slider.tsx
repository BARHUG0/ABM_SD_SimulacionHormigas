import * as RadixSlider from '@radix-ui/react-slider'

interface SliderProps {
  value: number
  min: number
  max: number
  step: number
  label: string
  disabled?: boolean
  onChange?: (value: number) => void
  onCommit?: (value: number) => void
}

export function Slider({ value, min, max, step, label, disabled, onChange, onCommit }: SliderProps) {
  return (
    <RadixSlider.Root
      className="relative flex h-5 w-full touch-none items-center select-none data-[disabled]:opacity-40"
      value={[value]}
      min={min}
      max={max}
      step={step}
      disabled={disabled}
      onValueChange={([next]) => onChange?.(next)}
      onValueCommit={([next]) => onCommit?.(next)}
    >
      <RadixSlider.Track className="relative h-1.5 grow rounded-full bg-soil-700">
        <RadixSlider.Range className="absolute h-full rounded-full bg-amber-500" />
      </RadixSlider.Track>
      <RadixSlider.Thumb
        aria-label={label}
        className="block size-4 rounded-full border-2 border-amber-500 bg-sand-100 shadow focus:ring-2 focus:ring-amber-500/50 focus:outline-none"
      />
    </RadixSlider.Root>
  )
}
