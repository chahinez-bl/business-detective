import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import models  # noqa: F401  (register tables)
from .config import get_settings
from .database import Base, engine
from .errors import ApiError
from .routers import actions, auth, businesses, datasets, demo, reports, workspace

log = logging.getLogger("businessdetective")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_url.startswith("sqlite"):
        Path(settings.database_url.replace("sqlite:///", "", 1)).parent.mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:      # development convenience; staging/production use `alembic upgrade head`
        Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Business Detective API", version="2.0.0", lifespan=lifespan,
              docs_url="/api/docs" if settings.env != "production" else None, redoc_url=None, openapi_url="/api/openapi.json" if settings.env != "production" else None)
origins = settings.cors_origins or (["http://localhost:5173", "http://127.0.0.1:5173"] if settings.env == "development" else [])
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"], max_age=600)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin"})
    if request.url.path.startswith("/api"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


@app.exception_handler(ApiError)
async def api_error(_, e: ApiError):
    return JSONResponse({"detail": e.message, **e.extra}, status_code=e.status)


@app.exception_handler(StarletteHTTPException)
async def http_error(_, e: StarletteHTTPException):
    msg = {404: "We couldn't find what you were looking for.", 405: "This action isn't allowed.", 401: "Please sign in to continue."}.get(e.status_code, "The request could not be completed.")
    return JSONResponse({"detail": msg}, status_code=e.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_, e: RequestValidationError):
    parts = []
    for err in e.errors()[:3]:
        loc = ".".join(str(x) for x in err["loc"] if x not in ("body", "query", "path"))
        msg = str(err["msg"]).removeprefix("Value error, ")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return JSONResponse({"detail": "Please check your input — " + "; ".join(parts)}, status_code=422)


@app.exception_handler(Exception)
async def unexpected(request: Request, e: Exception):
    ref = uuid.uuid4().hex[:8]
    log.error("Unhandled error ref=%s path=%s type=%s", ref, request.url.path, type(e).__name__, exc_info=True)   # message only, never request bodies
    return JSONResponse({"detail": f"Something went wrong on our side. Please try again. (reference {ref})"}, status_code=500)


api = "/api"
for r in (auth.router, businesses.router, datasets.router, workspace.router, actions.router, reports.router, demo.router):
    app.include_router(r, prefix=api)


@app.get("/api/health")
def health():
    return {"ok": True, "env": settings.env}


def _mount_frontend():
    dist = Path(settings.frontend_dist) if settings.frontend_dist else Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if not (dist / "index.html").exists():
        return
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "We couldn't find what you were looking for."}, status_code=404)
        f = (dist / path).resolve()
        if path and f.is_file() and dist.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(dist / "index.html")


_mount_frontend()
