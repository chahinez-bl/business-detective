import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react"
import { api } from "../api/client"
import type { Bundle } from "../api/types"
import { useAuth } from "./auth"

interface WsCtx {
  mode: "customer" | "demo"; base: string; bid: number | null; setBid: (id: number) => void
  data: Bundle | null; loading: boolean; error: string; reload: () => Promise<void>
  readOnly: boolean
}
const Ctx = createContext<WsCtx>(null as unknown as WsCtx)
export const useWs = () => useContext(Ctx)
const KEY = "bd_business"

export function WorkspaceProvider({ mode, children }: { mode: "customer" | "demo"; children: ReactNode }) {
  const { businesses } = useAuth()
  const stored = Number(localStorage.getItem(KEY)) || null
  const [bid, setBidState] = useState<number | null>(mode === "demo" ? 0 : stored)
  const [data, setData] = useState<Bundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const current = mode === "demo" ? 0 : (businesses.find(b => b.id === bid)?.id ?? businesses[0]?.id ?? null)

  const reload = useCallback(async () => {
    if (mode === "customer" && current == null) { setData(null); setLoading(false); return }
    setLoading(true); setError("")
    try { setData(await api.get(mode === "demo" ? "/demo/workspace" : `/businesses/${current}/workspace`)) }
    catch (e: any) { setError(e.message); setData(null) }
    setLoading(false)
  }, [mode, current])

  useEffect(() => { setData(null); reload() }, [reload])

  const setBid = (id: number) => { localStorage.setItem(KEY, String(id)); setBidState(id) }
  const role = data?.business?.role ?? businesses.find(b => b.id === current)?.role
  return <Ctx.Provider value={{ mode, base: mode === "demo" ? "/demo" : "/app", bid: current, setBid, data, loading, error, reload, readOnly: mode === "demo" || role === "viewer" }}>{children}</Ctx.Provider>
}
