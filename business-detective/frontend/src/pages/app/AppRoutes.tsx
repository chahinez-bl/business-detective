import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import AppLayout from "../../layouts/AppLayout"
import { useAuth } from "../../state/auth"
import { WorkspaceProvider } from "../../state/workspace"
import { Loading } from "../../components/ui"
import { common, customerOnly } from "./routes"

function Guard({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth(); const loc = useLocation()
  if (loading) return <Loading />
  return user ? children : <Navigate to="/login" replace state={{ from: loc.pathname }} />
}

/** Lazy-loaded chunk: everything behind /app and /demo. */
export default function AppRoutes({ mode }: { mode: "customer" | "demo" }) {
  const layout = <WorkspaceProvider mode={mode}><AppLayout /></WorkspaceProvider>
  return <Routes><Route element={mode === "customer" ? <Guard>{layout}</Guard> : layout}>{common}{mode === "customer" && customerOnly}<Route path="*" element={<Navigate to="overview" replace />} /></Route></Routes>
}
