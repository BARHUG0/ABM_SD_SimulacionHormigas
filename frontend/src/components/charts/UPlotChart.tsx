import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'

interface UPlotChartProps {
  options: Omit<uPlot.Options, 'width'>
  data: number[][]
}

export function UPlotChart({ options, data }: UPlotChartProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const plotRef = useRef<uPlot | null>(null)
  const dataRef = useRef(data)

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    const plot = new uPlot({ ...options, width: host.clientWidth || 320 }, dataRef.current as uPlot.AlignedData, host)
    plotRef.current = plot
    const observer = new ResizeObserver(() => plot.setSize({ width: host.clientWidth, height: options.height }))
    observer.observe(host)
    return () => {
      observer.disconnect()
      plot.destroy()
      plotRef.current = null
    }
  }, [options])

  useEffect(() => {
    dataRef.current = data
    plotRef.current?.setData(data as uPlot.AlignedData)
  }, [data])

  return <div ref={hostRef} className="w-full" />
}
