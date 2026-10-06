export const num = (n: number | null | undefined, d = 0) => n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: d })
export const money = (n: number | null | undefined, cur: string) => n == null ? "—" : `${num(n)} ${cur}`
export const moneyShort = (n: number | null | undefined, cur: string) => {
  if (n == null) return "—"
  const a = Math.abs(n)
  const v = a >= 1e9 ? (n / 1e9).toFixed(1) + "B" : a >= 1e6 ? (n / 1e6).toFixed(1) + "M" : a >= 1e4 ? (n / 1e3).toFixed(0) + "K" : num(n)
  return `${v} ${cur}`
}
export const pct = (n: number | null | undefined, signed = false, d = 1) => n == null ? "—" : `${signed && n > 0 ? "+" : ""}${n.toFixed(d)}%`
export const dateLabel = (s: string | null | undefined) => s ? new Date(s.length === 10 ? s + "T00:00:00" : s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—"
export const greeting = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening" }
