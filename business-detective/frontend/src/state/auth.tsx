import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react"
import { api, setUnauthorizedHandler, token } from "../api/client"
import type { Business } from "../api/types"

interface User { id: number; email: string; name: string }
interface AuthCtx {
  user: User | null; businesses: Business[]; loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [loading, setLoading] = useState(!!token.get())

  const refresh = useCallback(async () => {
    if (!token.get()) { setUser(null); setBusinesses([]); setLoading(false); return }
    try {
      const me = await api.get("/auth/me")
      setUser(me.user); setBusinesses(me.businesses)
    } catch { token.clear(); setUser(null); setBusinesses([]) }
    setLoading(false)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => { token.clear(); setUser(null); setBusinesses([]) })
    refresh()
  }, [refresh])

  const start = async (r: any) => { token.set(r.token); await refresh() }
  return <Ctx.Provider value={{
    user, businesses, loading, refresh,
    login: async (email, password) => start(await api.post("/auth/login", { email, password })),
    register: async (name, email, password) => start(await api.post("/auth/register", { name, email, password })),
    logout: async () => { try { await api.post("/auth/logout") } catch { /* already invalid */ } token.clear(); setUser(null); setBusinesses([]) },
  }}>{children}</Ctx.Provider>
}
