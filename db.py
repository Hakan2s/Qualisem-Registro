"""
db.py — Conexión y schema SQLite (Lun–Sáb, cierre de semana y catálogo de trabajadores)
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
    activo  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entradas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    semana_id    INTEGER NOT NULL,
    fecha        TEXT NOT NULL,
    trabajador   TEXT NOT NULL,
    actividad    TEXT,
    monto        REAL NOT NULL DEFAULT 0,
    extra_sabado INTEGER NOT NULL DEFAULT 0, -- 0/1, solo válido si fecha es sábado
    extra_monto  REAL NOT NULL DEFAULT 0,    -- monto adicional del sábado
    UNIQUE(semana_id, fecha, trabajador),
    FOREIGN KEY (semana_id) REFERENCES semanas(id)
);
"""


def init_db() -> None:
    """Crea las tablas si no existen."""
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
