"""
db.py — Conexión y schema SQLite (Lun–Sáb, cierre de semana y catálogo de trabajadores con cargo)
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# La DB se crea en runtime aquí:
DB_PATH = Path("data/registro.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    """Devuelve una conexión SQLite con row_factory tipo dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS semanas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    semana_inicio  TEXT NOT NULL,   -- Lunes (YYYY-MM-DD)
    semana_fin     TEXT NOT NULL,   -- Sábado (YYYY-MM-DD)  ⚠️ versiones antiguas pueden tener Domingo
    encargado      TEXT NOT NULL,
    cerrada        INTEGER NOT NULL DEFAULT 0, -- 0: abierta, 1: cerrada
    UNIQUE (semana_inicio, semana_fin)
);

CREATE TABLE IF NOT EXISTS trabajadores (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE,
    cargo   TEXT,                      -- NUEVO
    activo  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entradas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    semana_id    INTEGER NOT NULL,
    fecha        TEXT NOT NULL,
    trabajador   TEXT NOT NULL,        -- texto; se asocia por nombre al catálogo
    actividad    TEXT,
    monto        REAL NOT NULL DEFAULT 0,
    extra_sabado INTEGER NOT NULL DEFAULT 0, -- 0/1, solo válido si fecha es sábado
    extra_monto  REAL NOT NULL DEFAULT 0,    -- monto adicional del sábado
    UNIQUE(semana_id, fecha, trabajador),
    FOREIGN KEY (semana_id) REFERENCES semanas(id)
);
"""


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)


def _ensure_column(conn: sqlite3.Connection, table: str, col_def: str) -> None:
    """col_def: ej. 'cargo TEXT'"""
    col_name = col_def.split()[0]
    if not _has_column(conn, table, col_name):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")


def init_db() -> None:
    """Crea tablas si no existen y migra columnas nuevas sin perder datos."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        # Migraciones por si la DB ya existía
        _ensure_column(conn, "trabajadores", "cargo TEXT")
        _ensure_column(conn, "semanas", "cerrada INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "entradas", "extra_sabado INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "entradas", "extra_monto REAL NOT NULL DEFAULT 0")
