// All HTTP traffic goes through this file. VITE_API_URL is empty when the API serves the app on the same domain.
const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? ""
const KEY = "bd_token"

export const token = {
  get: () => localStorage.getItem(KEY),
  set: (t: string) => localStorage.setItem(KEY, t),
  clear: () => localStorage.removeItem(KEY),
}

export class ApiError extends Error {
  status: number
  extra: any
  constructor(message: string, status: number, extra?: any) {
    super(message)
    this.status = status
    this.extra = extra
  }
}

let onUnauthorized: () => void = () => {}
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn }

function friendly(status: number, body: any): string {
  if (body && typeof body.detail === "string") return body.detail
  if (status === 0) return "We couldn't reach the server. Please check your connection and try again."
  if (status >= 500) return "Something went wrong on our side. Please try again in a moment."
  return "The request could not be completed."
}

async function request<T = any>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  const t = token.get()
  if (t) headers["Authorization"] = `Bearer ${t}`
  if (body !== undefined) headers["Content-Type"] = "application/json"
  let res: Response
  try {
    res = await fetch(BASE + "/api" + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError(friendly(0, null), 0)
  }
  if (res.status === 401 && t) onUnauthorized()
  let data: any = null
  try { data = await res.json() } catch { /* non-JSON body */ }
  if (!res.ok) throw new ApiError(friendly(res.status, data), res.status, data)
  return data as T
}

export const api = {
  get: <T = any>(p: string) => request<T>("GET", p),
  post: <T = any>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}),
  patch: <T = any>(p: string, b: unknown) => request<T>("PATCH", p, b),
  del: <T = any>(p: string) => request<T>("DELETE", p),
  /** Multipart upload with progress (fetch cannot report upload progress). */
  upload<T = any>(path: string, file: File, onProgress: (pct: number) => void): Promise<T> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open("POST", BASE + "/api" + path)
      const t = token.get()
      if (t) xhr.setRequestHeader("Authorization", `Bearer ${t}`)
      xhr.upload.onprogress = e => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100))
      xhr.onerror = () => reject(new ApiError(friendly(0, null), 0))
      xhr.onload = () => {
        let data: any = null
        try { data = JSON.parse(xhr.responseText) } catch { /* ignore */ }
        if (xhr.status === 401) onUnauthorized()
        xhr.status >= 200 && xhr.status < 300 ? resolve(data) : reject(new ApiError(friendly(xhr.status, data), xhr.status, data))
      }
      const fd = new FormData()
      fd.append("file", file)
      xhr.send(fd)
    })
  },
  /** Authenticated file download (reports are never publicly reachable). */
  async download(path: string, filename: string) {
    const res = await fetch(BASE + "/api" + path, { headers: { Authorization: `Bearer ${token.get() ?? ""}` } })
    if (!res.ok) throw new ApiError("We couldn't download this file. Please try again.", res.status)
    const url = URL.createObjectURL(await res.blob())
    const a = document.createElement("a")
    a.href = url; a.download = filename; a.click()
    setTimeout(() => URL.revokeObjectURL(url), 5000)
  },
}
