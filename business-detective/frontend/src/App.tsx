import { lazy, Suspense } from "react"
import { Route, Routes } from "react-router-dom"
import { Loading } from "./components/ui"
import PublicLayout from "./layouts/PublicLayout"
import Home from "./pages/public/Home"
import { Contact, Faq, Features, HowItWorks, Login, Pricing, Privacy, Product, Register } from "./pages/public/Pages"

const AppRoutes = lazy(() => import("./pages/app/AppRoutes"))

export default function App() {
  return <Suspense fallback={<Loading />}><Routes>
    <Route element={<PublicLayout />}>
      <Route index element={<Home />} /><Route path="product" element={<Product />} /><Route path="features" element={<Features />} /><Route path="how-it-works" element={<HowItWorks />} />
      <Route path="pricing" element={<Pricing />} /><Route path="faq" element={<Faq />} /><Route path="privacy" element={<Privacy />} /><Route path="contact" element={<Contact />} />
      <Route path="login" element={<Login />} /><Route path="register" element={<Register />} />
    </Route>
    <Route path="/app/*" element={<AppRoutes mode="customer" />} />
    <Route path="/demo/*" element={<AppRoutes mode="demo" />} />
    <Route path="*" element={<PublicLayout />}><Route path="*" element={<div className="wrap center" style={{ padding: "80px 0" }}><h1>Page not found</h1><p className="mute">The page you're looking for doesn't exist.</p></div>} /></Route>
  </Routes></Suspense>
}
