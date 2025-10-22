# =============================
# app.py – Planilla LUN–SÁB con abrir/cerrar semana, autocomplete y cargo
# =============================
import pandas as pd
import streamlit as st
from datetime import date, timedelta

from db import get_conn, init_db

st.set_page_config(
    page_title="Planilla semanal – Lunes a Sábado",
    layout="wide",
)

# Inicializa DB
init_db()

# -------------------- Utilidades (LUN–SÁB) --------------------
def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def saturday_of_week(d: date) -> date:
    return monday_of_week(d) + timedelta(days=5)

def label_dow(idx: int) -> str:
    return ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"][idx]

# -------------------- Sidebar: semana + encargado + abrir/cerrar --------------------
st.sidebar.title("🗓️ Semana & Encargado")

fecha_ref = st.sidebar.date_input(
    "Semana de referencia (cualquier día)",
    value=date.today(),
    key="wk_fecha_ref",
)

sem_ini = monday_of_week(fecha_ref)
sem_fin = saturday_of_week(fecha_ref)  # LUN–SÁB

encargado_input = st.sidebar.text_input(
    "Encargado de la semana",
    value="",
    key="wk_encargado",
)

# Crear/obtener semana (compat: si no existe LUN–SÁB, busca LUN–DOM de semanas antiguas)
with get_conn() as conn:
    row = conn.execute(
        "SELECT id, encargado, cerrada FROM semanas WHERE semana_inicio=? AND semana_fin=?",
        (sem_ini.isoformat(), sem_fin.isoformat()),
    ).fetchone()

    if row is None:
        dom = sem_ini + timedelta(days=6)  # compat LUN–DOM
        row = conn.execute(
            "SELECT id, encargado, cerrada FROM semanas WHERE semana_inicio=? AND semana_fin=?",
            (sem_ini.isoformat(), dom.isoformat()),
        ).fetchone()

    if row is None and encargado_input:
        conn.execute(
            "INSERT INTO semanas(semana_inicio, semana_fin, encargado) VALUES (?,?,?)",
            (sem_ini.isoformat(), sem_fin.isoformat(), encargado_input.strip()),
        )
        row = conn.execute(
            "SELECT id, encargado, cerrada FROM semanas WHERE semana_inicio=? AND semana_fin=?",
            (sem_ini.isoformat(), sem_fin.isoformat()),
        ).fetchone()

    semana_id   = row["id"] if row else None
    encargado   = row["encargado"] if row else None
    cerrada     = int(row["cerrada"]) if row else 0

st.sidebar.caption(f"Semana: **{sem_ini} a {sem_fin}** (Lun–Sáb)")
if semana_id:
    if cerrada:
        st.sidebar.error(f"Semana CERRADA. Encargado: {encargado}")
        if st.sidebar.button("🔓 Abrir semana", use_container_width=True):
            with get_conn() as conn:
                conn.execute("UPDATE semanas SET cerrada=0 WHERE id=?", (int(semana_id),))
            st.success("✅ Semana abierta nuevamente.")
            st.rerun()
    else:
        st.sidebar.success(f"Semana ABIERTA. Encargado: {encargado}")
        if st.sidebar.button("🔒 Cerrar semana", use_container_width=True):
            with get_conn() as conn:
                conn.execute("UPDATE semanas SET cerrada=1 WHERE id=?", (int(semana_id),))
            st.warning("🔒 Semana cerrada correctamente.")
            st.rerun()
else:
    st.sidebar.info("Ingresa el encargado para registrar la semana y poder guardar entradas.")

# -------------------- Tabs --------------------
reg_tab, montos_tab = st.tabs(["📅 Registros (Lun–Sáb)", "💵 Montos y Total (pago sábado)"])

# -------------------- TAB 1 – Registros --------------------
with reg_tab:
    st.subheader("Registrar día por trabajador")

    if cerrada:
        st.info("🔒 Esta semana está cerrada. No se permiten altas ni ediciones.")

    with st.form("add_form", clear_on_submit=True):
        disabled = bool(cerrada)

        c1, c2, c3 = st.columns(3)
        with c1:
            max_fecha = sem_fin  # LUN–SÁB
            add_fecha = st.date_input(
                "Fecha",
                value=sem_ini,
                min_value=sem_ini,
                max_value=max_fecha,
                key="add_fecha",
                disabled=disabled,
            )
        with c2:
            # Autocomplete de trabajadores desde catálogo
            with get_conn() as conn:
                rows = conn.execute(
                    "SELECT nombre, COALESCE(cargo, '') AS cargo FROM trabajadores WHERE activo=1 ORDER BY nombre"
                ).fetchall()
            nombres = [r["nombre"] for r in rows]
            cargos_map = {r["nombre"]: r["cargo"] for r in rows}

            opciones = ["— Escribe nombre —", *nombres, "➕ Agregar nuevo…"]
            sel_nombre = st.selectbox(
                "Trabajador (autocompletar)",
                options=opciones,
                index=0,
                disabled=disabled,
                key="sel_trabajador",
            )

            if sel_nombre == "➕ Agregar nuevo…":
                add_trab_new = st.text_input("Nuevo trabajador", key="add_trab_new", disabled=disabled)
                add_cargo_new = st.text_input("Cargo", key="add_cargo_new", disabled=disabled)
                add_trab = add_trab_new.strip() if add_trab_new else ""
                add_cargo = add_cargo_new.strip() if add_cargo_new else ""
            elif sel_nombre == "— Escribe nombre —":
                add_trab = ""
                add_cargo = ""
            else:
                add_trab = sel_nombre
                add_cargo = cargos_map.get(sel_nombre, "")
                st.text_input("Cargo", value=add_cargo, disabled=True, key="cargo_existente")

        with c3:
            add_monto = st.number_input(
                "Monto del día (S/)",
                min_value=0.0,
                step=1.0,
                value=0.0,
                key="add_monto",
                disabled=disabled,
            )

        add_act = st.text_input("Actividad (opcional)", key="add_act", disabled=disabled)

        # Adicional sábado: solo se habilita si la fecha elegida es sábado
        es_sabado = (isinstance(add_fecha, date) and add_fecha.weekday() == 5)
        colx = st.columns([1, 1])
        with colx[0]:
            add_extra_flag = st.checkbox(
                "Pago adicional de sábado",
                value=False,
                key="add_extra_flag",
                disabled=(disabled or not es_sabado),
            )
        with colx[1]:
            add_extra_monto = st.number_input(
                "Monto adicional (solo sábado)",
                min_value=0.0,
                step=1.0,
                value=0.0,
                key="add_extra_monto",
                disabled=(disabled or not es_sabado),
            )

        submitted = st.form_submit_button(
            "💾 Guardar registro",
            use_container_width=True,
            disabled=disabled,
        )

    if submitted and not disabled:
        if not semana_id:
            st.error("Primero registra la semana (encargado en la barra lateral).")
        elif not add_trab:
            st.error("El nombre del trabajador es obligatorio.")
        else:
            # Guardar/actualizar catálogo de trabajadores (con cargo)
            with get_conn() as conn:
                if sel_nombre == "➕ Agregar nuevo…":
                    if not add_cargo:
                        st.error("Por favor, indica el Cargo del nuevo trabajador.")
                        st.stop()
                    conn.execute(
                        "INSERT OR IGNORE INTO trabajadores(nombre, cargo) VALUES (?, ?)",
                        (add_trab, add_cargo),
                    )
                else:
                    # Si ya existe pero no tenía cargo, no lo tocamos aquí (se podría editar en un módulo aparte)
                    pass

            # Reglas: adicional solo sábado
            extra_flag  = int(add_extra_flag and (add_fecha.weekday() == 5))
            extra_monto = float(add_extra_monto if extra_flag else 0)

            try:
                with get_conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO entradas(semana_id, fecha, trabajador, actividad, monto, extra_sabado, extra_monto)
                        VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(semana_id, fecha, trabajador) DO UPDATE SET
                            actividad=excluded.actividad,
                            monto=excluded.monto,
                            extra_sabado=excluded.extra_sabado,
                            extra_monto=excluded.extra_monto
                        """,
                        (
                            int(semana_id),
                            add_fecha.isoformat(),
                            add_trab.strip(),
                            add_act.strip(),
                            float(add_monto),
                            extra_flag,
                            extra_monto,
                        ),
                    )
                st.success("Registro guardado/actualizado.")
            except Exception as e:
                st.error(f"Error guardando registro: {e}")

    st.divider()
    st.subheader("Vista semanal (Lun–Sáb) por trabajador")

    # Cargar registros de la semana (LUN–SÁB)
    if semana_id:
        with get_conn() as conn:
            df_det = pd.read_sql_query(
                """
                SELECT e.fecha, e.trabajador, e.actividad, e.monto, e.extra_monto, t.cargo
                FROM entradas e
                LEFT JOIN trabajadores t ON t.nombre = e.trabajador
                WHERE e.semana_id=? AND date(e.fecha) BETWEEN date(?) AND date(?)
                ORDER BY e.trabajador, date(e.fecha)
                """,
                conn,
                params=(semana_id, sem_ini.isoformat(), sem_fin.isoformat()),
            )
    else:
        df_det = pd.DataFrame()

    if df_det.empty:
        st.info("Sin registros en la semana seleccionada.")
    else:
        # Tabla pivot Lunes–Sábado
        df_det["fecha"] = pd.to_datetime(df_det["fecha"]).dt.date
        df_det["dow"] = pd.to_datetime(df_det["fecha"]).dt.weekday

        df_pivot = (
            df_det.pivot_table(index="trabajador", columns="dow", values="monto", aggfunc="sum")
            .fillna(0)
        )
        df_pivot = df_pivot.rename(columns={i: label_dow(i) for i in range(6)})

        # Monto extra (solo sábado) -> una sola columna "Monto extra"
        extras = (
            df_det[df_det["dow"] == 5]
            .groupby("trabajador", as_index=False)
            .agg(monto_extra=("extra_monto", "max"))
        )

        # Días asistidos (fechas únicas LUN–SÁB)
        dias = (
            df_det.groupby("trabajador")["fecha"]
            .nunique()
            .rename("dias")
            .reset_index()
        )

        # Cargo por trabajador
        cargos = (
            df_det.groupby("trabajador")["cargo"]
            .agg(lambda x: next((v for v in x if pd.notna(v) and v != ""), ""))
            .rename("cargo")
            .reset_index()
        )

        # Unir todo
        df_sem = df_pivot.reset_index() \
            .merge(extras, on="trabajador", how="left") \
            .merge(dias, on="trabajador", how="left") \
            .merge(cargos, on="trabajador", how="left")

        df_sem["monto_extra"] = df_sem["monto_extra"].fillna(0.0)
        df_sem["dias"] = df_sem["dias"].fillna(0).astype(int)

        cols_dias = [c for c in df_sem.columns if c in [label_dow(i) for i in range(6)]]
        df_sem["Total semana"] = df_sem[cols_dias].sum(axis=1) + df_sem["monto_extra"]

        # Reordenar y renombrar para mostrar cargo, dias y monto extra
        columnas = ["trabajador", "cargo"] + cols_dias + ["dias", "monto_extra", "Total semana"]
        df_sem = df_sem[columnas]
        df_sem = df_sem.rename(columns={"monto_extra": "Monto extra"})

        st.dataframe(df_sem, use_container_width=True)

# -------------------- TAB 2 – Montos y Total (pago sábado) --------------------
with montos_tab:
    st.subheader("Montos por trabajador y total necesario el sábado")

    if not semana_id:
        st.info("Registra la semana para ver montos.")
    else:
        with get_conn() as conn:
            # LUN–SÁB en SQLite: %w -> 1..6 ; Domingo = 0
            df = pd.read_sql_query(
                """
                SELECT e.trabajador,
                       t.cargo,
                       COUNT(DISTINCT date(e.fecha)) AS dias,
                       SUM(CASE WHEN strftime('%w', e.fecha) IN ('1','2','3','4','5','6') THEN e.monto ELSE 0 END) AS monto_semana,
                       MAX(CASE WHEN strftime('%w', e.fecha) = '6' THEN e.extra_monto ELSE 0 END) AS extra_monto
                FROM entradas e
                LEFT JOIN trabajadores t ON t.nombre = e.trabajador
                WHERE e.semana_id=?
                GROUP BY e.trabajador, t.cargo
                ORDER BY e.trabajador
                """,
                conn,
                params=(semana_id,),
            )

        if df.empty:
            st.info("Sin registros todavía.")
        else:
            # Calcular Total a pagar y seleccionar columnas exactas
            df["Monto adicional"] = df["extra_monto"].fillna(0)
            df["Total a pagar"] = df["monto_semana"].fillna(0) + df["Monto adicional"]

            df = df[["trabajador", "cargo", "dias", "Monto adicional", "Total a pagar"]]
            df["dias"] = df["dias"].fillna(0).astype(int)
            st.dataframe(df, use_container_width=True)

            total_general = float(df["Total a pagar"].sum())
            st.metric("💰 Efectivo necesario el sábado", total_general)

            st.download_button(
                "⬇️ Exportar planilla de pagos (CSV)",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"pagos_semana_{sem_ini}_a_{sem_fin}.csv",
                mime="text/csv",
            )
