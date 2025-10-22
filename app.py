# =============================
# app.py – Planilla LUN–SÁB con abrir/cerrar semana, NUEVA SEMANA,
# trabajador existente/nuevo, "Monto adicional" consistente y editor de trabajador
# =============================
import pandas as pd
import streamlit as st
from datetime import date, timedelta

from db import get_conn, init_db

st.set_page_config(page_title="Planilla semanal – Lunes a Sábado", layout="wide")
init_db()

# -------------------- Utilidades (LUN–SÁB) --------------------
def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def saturday_of_week(d: date) -> date:
    return monday_of_week(d) + timedelta(days=5)

def label_dow(idx: int) -> str:
    return ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"][idx]

def ensure_semana(ini: date, fin: date, encargado: str | None = None):
    """Crea semana si no existe; devuelve (id, encargado, cerrada)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, encargado, cerrada FROM semanas WHERE semana_inicio=? AND semana_fin=?",
            (ini.isoformat(), fin.isoformat()),
        ).fetchone()
        if row is None:
            enc = (encargado or "").strip() or "—"
            conn.execute(
                "INSERT INTO semanas(semana_inicio, semana_fin, encargado, cerrada) VALUES (?,?,?,0)",
                (ini.isoformat(), fin.isoformat(), enc),
            )
            row = conn.execute(
                "SELECT id, encargado, cerrada FROM semanas WHERE semana_inicio=? AND semana_fin=?",
                (ini.isoformat(), fin.isoformat()),
            ).fetchone()
        return row["id"], row["encargado"], int(row["cerrada"])

# -------------------- Sidebar: semana + encargado + abrir/cerrar + nueva semana --------------------
st.sidebar.title("🗓️ Semana & Encargado")

if "wk_fecha_ref" not in st.session_state:
    st.session_state["wk_fecha_ref"] = date.today()

fecha_ref = st.sidebar.date_input(
    "Semana de referencia (cualquier día)",
    value=st.session_state["wk_fecha_ref"],
    key="wk_fecha_ref_input",
)
st.session_state["wk_fecha_ref"] = fecha_ref

sem_ini = monday_of_week(fecha_ref)
sem_fin = saturday_of_week(fecha_ref)

encargado_input = st.sidebar.text_input("Encargado de la semana", value="", key="wk_encargado")

semana_id, encargado, cerrada = ensure_semana(sem_ini, sem_fin, encargado_input or None)

st.sidebar.caption(f"Semana: **{sem_ini} a {sem_fin}** (Lun–Sáb)")
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

if st.sidebar.button("🆕 Nueva semana (Lun–Sáb)", use_container_width=True):
    nueva_ref = fecha_ref + timedelta(days=7)
    st.session_state["wk_fecha_ref"] = nueva_ref
    ensure_semana(monday_of_week(nueva_ref), saturday_of_week(nueva_ref))
    st.rerun()

# -------------------- Tabs --------------------
reg_tab, montos_tab = st.tabs(["📅 Registros (Lun–Sáb)", "💵 Montos y Total (pago sábado)"])

# Helpers para limpiar inputs manualmente
def _reset_inputs():
    for k in [
        "add_fecha", "modo_trab", "trab_existente", "nuevo_nombre", "nuevo_cargo",
        "add_monto", "add_act", "add_extra_flag", "add_extra_monto"
    ]:
        if k in st.session_state:
            del st.session_state[k]

# -------------------- TAB 1 – Registros --------------------
with reg_tab:
    st.subheader("Registrar día por trabajador")

    if cerrada:
        st.info("🔒 Esta semana está cerrada. No se permiten altas ni ediciones.")

    # ==== Entrada de datos (SIN form para que reaccione en vivo) ====
    disabled = bool(cerrada)

    c1, c2 = st.columns([1, 2])
    with c1:
        add_fecha = st.date_input(
            "Fecha",
            value=st.session_state.get("add_fecha", sem_ini),
            min_value=sem_ini,
            max_value=sem_fin,
            key="add_fecha",
            disabled=disabled,
        )

    modo = st.radio(
        "Modo de trabajador",
        ["Existente", "Nuevo"],
        horizontal=True,
        key="modo_trab",
        disabled=disabled,
    )

    add_trab = ""
    add_cargo = ""

    if modo == "Existente":
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT nombre, COALESCE(cargo, '') AS cargo FROM trabajadores WHERE activo=1 ORDER BY nombre"
            ).fetchall()
        nombres = [r["nombre"] for r in rows]
        cargos_map = {r["nombre"]: r["cargo"] for r in rows}

        sel_trab = st.selectbox(
            "Trabajador (autocompletar)",
            options=["(Seleccione)"] + nombres,
            index=0,
            key="trab_existente",
            disabled=disabled,
        )

        coln1, coln2 = st.columns(2)
        with coln1:
            st.text_input(
                "Nombre",
                value=sel_trab if sel_trab != "(Seleccione)" else "",
                disabled=True,
                key="readonly_nombre",
            )
        with coln2:
            st.text_input(
                "Cargo",
                value=cargos_map.get(sel_trab, "") if sel_trab != "(Seleccione)" else "",
                disabled=True,
                key="readonly_cargo",
            )

        if sel_trab != "(Seleccione)":
            add_trab = sel_trab
            add_cargo = cargos_map.get(sel_trab, "")

    else:
        coln1, coln2 = st.columns(2)
        with coln1:
            add_trab = st.text_input("Nombre (nuevo)", key="nuevo_nombre", disabled=disabled).strip()
        with coln2:
            add_cargo = st.text_input("Cargo", key="nuevo_cargo", disabled=disabled).strip()

    # Monto y actividad
    col3, col4 = st.columns(2)
    with col3:
        add_monto = st.number_input(
            "Monto del día (S/)", min_value=0.0, step=1.0, value=st.session_state.get("add_monto", 0.0),
            key="add_monto", disabled=disabled
        )
    with col4:
        add_act = st.text_input("Actividad (opcional)", key="add_act", disabled=disabled)

    # Adicional sábado (habilita EN VIVO si la fecha es sábado)
    es_sabado = (isinstance(add_fecha, date) and add_fecha.weekday() == 5)
    colx = st.columns([1, 1])
    with colx[0]:
        add_extra_flag = st.checkbox(
            "Pago adicional de sábado",
            value=st.session_state.get("add_extra_flag", False),
            key="add_extra_flag",
            disabled=(disabled or not es_sabado),
        )
    with colx[1]:
        add_extra_monto = st.number_input(
            "Monto adicional (solo sábado)",
            min_value=0.0,
            step=1.0,
            value=st.session_state.get("add_extra_monto", 0.0),
            key="add_extra_monto",
            disabled=(disabled or not es_sabado),
        )

    guardar = st.button("💾 Guardar registro", use_container_width=True, disabled=disabled)

    # ==== Validación y guardado ====
    if guardar and not cerrada:
        if not add_trab:
            st.error("El nombre del trabajador es obligatorio.")
        elif modo == "Nuevo" and not add_cargo:
            st.error("Para un trabajador nuevo, el Cargo es obligatorio.")
        else:
            if modo == "Nuevo":
                with get_conn() as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO trabajadores(nombre, cargo) VALUES (?, ?)",
                        (add_trab, add_cargo),
                    )

            # Reglas robustas para el adicional: si es sábado y hay monto > 0, se fuerza el flag.
            extra_flag = 1 if (es_sabado and float(add_extra_monto or 0) > 0) else int(bool(add_extra_flag) and es_sabado)
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
                _reset_inputs()  # limpia los campos
                st.rerun()
            except Exception as e:
                st.error(f"Error guardando registro: {e}")

    # ==== Editor de trabajador (catálogo) ====
    st.divider()
    st.subheader("Editar trabajador (catálogo)")

    with get_conn() as conn:
        cat_rows = conn.execute(
            "SELECT id, nombre, COALESCE(cargo, '') AS cargo, activo FROM trabajadores ORDER BY nombre"
        ).fetchall()

    if not cat_rows:
        st.info("Aún no tienes trabajadores en el catálogo.")
    else:
        nombres_cat = [r["nombre"] for r in cat_rows]
        sel_edit = st.selectbox("Selecciona trabajador", options=["(Seleccione)"] + nombres_cat, index=0, key="edit_trab_sel")
        if sel_edit != "(Seleccione)":
            tr = next(r for r in cat_rows if r["nombre"] == sel_edit)
            c1, c2, c3 = st.columns([1.2, 1, 0.8])
            with c1:
                nuevo_nombre = st.text_input("Nombre", value=tr["nombre"], key=f"edit_nombre_{tr['id']}")
            with c2:
                nuevo_cargo = st.text_input("Cargo", value=tr["cargo"], key=f"edit_cargo_{tr['id']}")
            with c3:
                activo_flag = st.checkbox("Activo", value=bool(tr["activo"]), key=f"edit_activo_{tr['id']}")

            e1, e2 = st.columns(2)
            with e1:
                if st.button("💾 Guardar cambios", key=f"btn_save_trab_{tr['id']}"):
                    try:
                        with get_conn() as conn:
                            conn.execute(
                                "UPDATE trabajadores SET nombre=?, cargo=?, activo=? WHERE id=?",
                                (nuevo_nombre.strip(), nuevo_cargo.strip(), int(activo_flag), int(tr["id"]))
                            )
                        st.success("Trabajador actualizado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {e}")
            with e2:
                if st.button("🗑️ Desactivar (no mostrar)", key=f"btn_del_trab_{tr['id']}"):
                    with get_conn() as conn:
                        conn.execute("UPDATE trabajadores SET activo=0 WHERE id=?", (int(tr["id"]),))
                    st.warning("Trabajador desactivado.")
                    st.rerun()

    # ==== Vista semanal ====
    st.divider()
    st.subheader("Vista semanal (Lun–Sáb) por trabajador")

    with get_conn() as conn:
        df_det = pd.read_sql_query(
            """
            SELECT e.fecha, e.trabajador, e.actividad, e.monto, e.extra_monto,
                   COALESCE(t.cargo, '') AS cargo
            FROM entradas e
            LEFT JOIN trabajadores t ON t.nombre = e.trabajador
            WHERE e.semana_id=? AND date(e.fecha) BETWEEN date(?) AND date(?)
            ORDER BY e.trabajador, date(e.fecha)
            """,
            conn,
            params=(semana_id, sem_ini.isoformat(), sem_fin.isoformat()),
        )

    if df_det.empty:
        st.info("Sin registros en la semana seleccionada.")
    else:
        df_det["fecha"] = pd.to_datetime(df_det["fecha"]).dt.date
        df_det["dow"] = pd.to_datetime(df_det["fecha"]).dt.weekday

        # Montos por día LUN–SÁB
        df_pivot = df_det.pivot_table(index=["trabajador"], columns="dow", values="monto", aggfunc="sum").fillna(0)
        df_pivot = df_pivot.rename(columns={i: label_dow(i) for i in range(6)})

        # Monto adicional (sábado): SUMA (no max)
        extras = (
            df_det[df_det["dow"] == 5]
            .groupby("trabajador", as_index=False)
            .agg(monto_adicional=("extra_monto", "sum"))
        )

        # Días trabajados
        dias = df_det.groupby("trabajador")["fecha"].nunique().rename("dias").reset_index()

        # Cargo por trabajador
        cargos = df_det.groupby("trabajador")["cargo"].agg(lambda x: next((v for v in x if v), "")).rename("cargo").reset_index()

        # Unir
        df_sem = (
            df_pivot.reset_index()
            .merge(extras, on="trabajador", how="left")
            .merge(dias, on="trabajador", how="left")
            .merge(cargos, on="trabajador", how="left")
        )
        df_sem["monto_adicional"] = df_sem["monto_adicional"].fillna(0.0)
        df_sem["dias"] = df_sem["dias"].fillna(0).astype(int)

        cols_dias = [c for c in df_sem.columns if c in [label_dow(i) for i in range(6)]]
        df_sem["Total semana"] = df_sem[cols_dias].sum(axis=1) + df_sem["monto_adicional"]

        columnas = ["trabajador", "cargo"] + cols_dias + ["dias", "monto_adicional", "Total semana"]
        df_sem = df_sem[columnas].rename(columns={"monto_adicional": "Monto adicional"})

        st.dataframe(df_sem, use_container_width=True)

# -------------------- TAB 2 – Montos y Total (pago sábado) --------------------
with montos_tab:
    st.subheader("Montos por trabajador y total necesario el sábado")

    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT e.trabajador,
                   COALESCE(t.cargo, '') AS cargo,
                   COUNT(DISTINCT date(e.fecha)) AS dias,
                   SUM(CASE WHEN strftime('%w', e.fecha) IN ('1','2','3','4','5','6') THEN e.monto ELSE 0 END) AS monto_semana,
                   SUM(CASE WHEN strftime('%w', e.fecha) = '6' THEN e.extra_monto ELSE 0 END) AS monto_adicional
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
        df["Monto adicional"] = df["monto_adicional"].fillna(0)
        df["Total a pagar"] = df["monto_semana"].fillna(0) + df["Monto adicional"]
        df = df[["trabajador", "cargo", "dias", "Monto adicional", "Total a pagar"]]
        df["dias"] = df["dias"].fillna(0).astype(int)

        st.dataframe(df, use_container_width=True)
        st.metric("💰 Efectivo necesario el sábado", float(df["Total a pagar"].sum()))

        st.download_button(
            "⬇️ Exportar planilla de pagos (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"pagos_semana_{sem_ini}_a_{sem_fin}.csv",
            mime="text/csv",
        )
