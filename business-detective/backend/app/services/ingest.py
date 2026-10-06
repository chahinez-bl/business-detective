"""File intake: validation, safe storage, and defensive parsing of CSV/XLSX uploads."""
import io
import uuid
import zipfile
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from ..config import get_settings
from ..errors import ApiError
from .util import safe_filename

ALLOWED = {".csv", ".xlsx"}
CHUNK = 1024 * 1024


def business_dir(business_id: int) -> Path:
    d = get_settings().storage_dir / f"business_{business_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(file: UploadFile, business_id: int) -> dict:
    s = get_settings()
    display = safe_filename(file.filename)
    ext = Path(display).suffix.lower()
    if ext not in ALLOWED:
        raise ApiError(415, "This file type isn't supported. Please upload a .csv or .xlsx file (in Excel: File → Save As → CSV).")
    stored = uuid.uuid4().hex + ext
    path = business_dir(business_id) / stored
    size, head = 0, b""
    try:
        with open(path, "wb") as out:
            while chunk := file.file.read(CHUNK):
                if not head:
                    head = chunk[:8192]
                size += len(chunk)
                if size > s.max_upload_bytes:
                    raise ApiError(413, f"This file is too large. The maximum size is {s.max_upload_mb} MB; try splitting it by period.")
                out.write(chunk)
        if size == 0 or not head.strip(b"\x00\r\n\t "):
            raise ApiError(422, "The file is empty.")
        if ext == ".xlsx" and not head.startswith(b"PK\x03\x04"):
            raise ApiError(422, "This doesn't look like a valid Excel (.xlsx) file. It may be corrupted or renamed from another format.")
        if ext == ".csv" and (b"\x00" in head):
            raise ApiError(422, "This doesn't look like a text CSV file. In Excel use “Save As → CSV UTF-8”.")
        if ext == ".xlsx":
            try:
                with zipfile.ZipFile(path) as z:
                    if sum(i.file_size for i in z.infolist()) > 400 * 1024 * 1024:
                        raise ApiError(413, "This spreadsheet expands to an unusually large size. Please export fewer rows.")
            except zipfile.BadZipFile:
                raise ApiError(422, "This Excel file appears to be corrupted. Try opening and re-saving it in Excel, then upload it again.")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return dict(filename=display, stored_name=stored, file_type=ext[1:], size_bytes=size)


def file_path(business_id: int, stored_name: str) -> Path:
    if "/" in stored_name or "\\" in stored_name or ".." in stored_name:
        raise ApiError(404, "File not found.")
    return business_dir(business_id) / stored_name


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _delimiter(text: str) -> str:
    lines = [l for l in text[:50000].splitlines() if l.strip()][:15]
    best, score = ",", 0
    for d in [",", ";", "\t", "|"]:
        counts = [l.count(d) for l in lines]
        if counts and min(counts) > 0 and min(counts) * (1 if len(set(counts)) == 1 else 0.5) > score:
            best, score = d, min(counts) * (1 if len(set(counts)) == 1 else 0.5)
    return best


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    seen, names = {}, []
    for i, c in enumerate(df.columns):
        n = str(c).strip() or f"Column {i + 1}"
        seen[n] = seen.get(n, 0) + 1
        names.append(n if seen[n] == 1 else f"{n} ({seen[n]})")
    df.columns = names
    return df.reset_index(drop=True)


def load_frame(path: Path, file_type: str) -> tuple[pd.DataFrame, dict]:
    """Returns (DataFrame with raw values, meta). Raises ApiError with friendly text for unreadable files."""
    s = get_settings()
    meta = {"skipped_lines": 0, "sheet": None}
    try:
        if file_type == "csv":
            text = _decode(path.read_bytes())
            bad = []
            df = pd.read_csv(io.StringIO(text), sep=_delimiter(text), dtype=str, engine="python", on_bad_lines=lambda r: bad.append(1) or None)
            meta["skipped_lines"] = len(bad)
        else:
            sheets = pd.read_excel(path, sheet_name=None, dtype=object, engine="openpyxl")
            sheets = {k: _tidy(v) for k, v in sheets.items()}
            sheets = {k: v for k, v in sheets.items() if len(v) and len(v.columns)}
            if not sheets:
                raise ApiError(422, "The spreadsheet has no data.")
            meta["sheet"] = next(iter(sheets))
            df = sheets[meta["sheet"]]
    except ApiError:
        raise
    except (pd.errors.EmptyDataError,):
        raise ApiError(422, "The file is empty.")
    except Exception:
        raise ApiError(422, "We couldn't read this file. Check that it is a valid CSV or Excel (.xlsx) file with a header row, then try again.")
    df = _tidy(df)
    if df.empty or len(df.columns) < 2:
        raise ApiError(422, "We couldn't find a table in this file. It needs a header row and at least two columns.")
    if len(df) > s.max_rows:
        raise ApiError(413, f"This file has more than {s.max_rows:,} rows. Please upload a smaller period.")
    return df, meta
