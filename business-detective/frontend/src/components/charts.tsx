import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { moneyShort, num } from "../lib/format"

const AX = { tick: { fill: "#7b8a92", fontSize: 11 }, axisLine: false, tickLine: false } as const
const TT = { contentStyle: { borderRadius: 10, border: "1px solid #e1e7ea", fontSize: 13 } }

export function RevenueChart({ data, cur, height = 260, marks = [] }: { data: { date: string; revenue: number }[]; cur: string; height?: number; marks?: string[] }) {
  return <div style={{ height }} role="img" aria-label="Daily revenue chart"><ResponsiveContainer><LineChart data={data} margin={{ left: 0, right: 8, top: 6 }}>
    <CartesianGrid stroke="#edf1f3" vertical={false} /><XAxis dataKey="date" {...AX} minTickGap={50} /><YAxis {...AX} width={56} tickFormatter={v => moneyShort(v, "").trim()} />
    <Tooltip {...TT} formatter={(v: any) => [`${num(v)} ${cur}`, "Revenue"]} />{marks.map(m => <ReferenceLine key={m} x={m} stroke="#c4560a" strokeDasharray="3 3" />)}
    <Line isAnimationActive={false} dataKey="revenue" stroke="#0f4c5c" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>
}

export function Bars({ data, x, y, cur, height = 240, color = "#0f4c5c", horizontal = false, fmt }: { data: any[]; x: string; y: string; cur?: string; height?: number; color?: string; horizontal?: boolean; fmt?: (v: number) => string }) {
  const f = fmt ?? ((v: number) => (cur ? `${num(v)} ${cur}` : num(v, 1)))
  return <div style={{ height }}><ResponsiveContainer><BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: horizontal ? 30 : 0, right: 8 }}>
    <CartesianGrid stroke="#edf1f3" horizontal={!horizontal} vertical={horizontal} />
    {horizontal ? <><XAxis type="number" {...AX} tickFormatter={v => num(v)} /><YAxis type="category" dataKey={x} width={110} {...AX} /></> : <><XAxis dataKey={x} {...AX} /><YAxis {...AX} width={56} tickFormatter={v => moneyShort(v, "").trim()} /></>}
    <Tooltip {...TT} formatter={(v: any) => [f(v), ""]} /><Bar isAnimationActive={false} dataKey={y} fill={color} radius={4} /></BarChart></ResponsiveContainer></div>
}

export function ForecastChart({ history, forecast, cur }: { history: any[]; forecast: any[]; cur: string }) {
  const data = [...history.map(h => ({ date: h.date, hist: h.value })), ...forecast.map(p => ({ date: p.date, fc: p.value, range: [p.low, p.high] }))]
  return <div style={{ height: 300 }} role="img" aria-label="Revenue forecast chart"><ResponsiveContainer><ComposedChart data={data}>
    <CartesianGrid stroke="#edf1f3" vertical={false} /><XAxis dataKey="date" {...AX} minTickGap={50} /><YAxis {...AX} width={56} tickFormatter={v => moneyShort(v, "").trim()} />
    <Tooltip {...TT} formatter={(v: any) => Array.isArray(v) ? [`${num(v[0])} – ${num(v[1])} ${cur}`, "Likely range"] : [`${num(v)} ${cur}`, ""]} />
    <Area isAnimationActive={false} dataKey="range" fill="#f2b134" fillOpacity={0.25} stroke="none" /><Line isAnimationActive={false} dataKey="hist" stroke="#0f4c5c" strokeWidth={2} dot={false} /><Line isAnimationActive={false} dataKey="fc" stroke="#c4560a" strokeWidth={2} strokeDasharray="5 4" dot={false} /></ComposedChart></ResponsiveContainer></div>
}
