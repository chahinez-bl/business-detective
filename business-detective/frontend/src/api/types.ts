export interface Insight {
  id: number; kind: string; area: string; category: "Anomaly" | "Risk" | "Opportunity" | "Financial"; severity: "Critical" | "High" | "Medium" | "Low"
  title: string; what: string; why: string; impact_amount: number | null; impact_text: string; evidence: string[]; action: string
  confidence: number; priority_score: number; detected_on: string | null; details: Record<string, any>; recommendation_id: number | null
  action_item: { id: number; status: string } | null; rank: number
}
export interface Recommendation {
  id: number; insight_id: number; title: string; area: string; problem: string; evidence: string; action: string; objective: string
  priority: string; confidence: number; impact_amount: number | null; action_item: { id: number; status: string } | null
}
export interface ActionItem {
  id: number; title: string; note: string; status: "todo" | "in_progress" | "resolved" | "dismissed"; insight_id: number | null; recommendation_id: number | null
  source_title: string; assignee_id: number | null; assignee: string | null; due_date: string | null; created_at: string; resolved_at: string | null; overdue: boolean
}
export interface Business { id: number; name: string; industry: string; currency: string; role: string }
export interface Bundle {
  has_data: boolean; mode: "customer" | "demo"; business: Business; currency: string
  dataset: { id: number; filename: string; rows: number } | null; analysis: any; quality: any
  kpis: any; capabilities: Record<string, { label: string; available: boolean; reason: string }>; health: any; root_cause: any
  products: any[]; inventory: any[]; suppliers: any[]; supplier_drift: any[]; customers: any; returns: any; profitability: any; forecast: any
  daily: { date: string; revenue: number }[]; monthly: any[]; weekday: any[]; leaks: any[]
  insights: Insight[]; recommendations: Recommendation[]
  overview: { attention: Insight[]; opportunities: Insight[] }
  monitoring: { status: string; health: any; areas: any[]; alerts: Insight[]; total_alerts: number; opportunities: Insight[]; recent_events: Insight[] }
  decision: { groups: Record<string, Insight[]>; count: number; opportunities: Insight[] }
}
