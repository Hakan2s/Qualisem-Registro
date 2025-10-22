# =============================
# app.py – QUALISEM G. (registros)
# Hojas estilo Excel: cada hoja = una semana (LUN–SÁB)
# Registro diario, adicional solo sábado, abrir/cerrar hoja,
# editor de trabajadores con borrado de registros y totales.
# =============================
import pandas as pd
import streamlit as st
from datetime import date, timedelta

from db import get_conn, init_db

st.set_page_config(page_title="QUALISEM G. (registros)", layout="wide")
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

def list_hojas():
    """Devuelve DataFrame de semanas como 'hojas' ordenadas desc por inicio."""
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT id, semana_inicio, semana_fin, encargado, cerrada
            FROM semanas
            ORDER BY date(semana_inicio) DESC
            """,
            conn,
        )
    if df.empty:
        return pd.DataFrame(columns=["id","semana_inicio","semana_fin","encargado","cerrada"])
    df["semana_inicio"] = pd.to_datetime(df["semana_inicio"]).dt.date
    df["semana_fin"]    = pd.to_datetime(df["semana_fin"]).dt.date
    return df

# -------------------- Sidebar: selector de HOJA (semana) --------------------
st.sidebar.title("📄 QUALISEM G. (registros)")

# Estado inicial: asegura al menos la hoja de la semana actual
if "hoja_id" not in st.session_state:
    ini = monday_of_week(date.today())
    fin = saturday_of_week(date.today())
    sid, _, _ = ensure_semana(ini, fin, None)
    st.session_state["hoja_id"] = int(sid)

df_hojas = list_hojas()
if df_hojas.empty:
    ini = monday_of_week(date.today())
    fin = saturday_of_week(date.today())
    sid, _, _ = ensure_semana(ini, fin, None)
    st.session_state["hoja_id"] = int(sid)
    df_hojas = list_hojas()

def hoja_label(row):
    estado = "🔒" if row["cerrada"] else "🟢"
    enc = row["encargado"] or "—"
    return f"{row['semana_inicio']} → {row['semana_fin']}  | Enc: {enc} {estado}"

opciones = {hoja_label(r): int(r["id"]) for _, r in df_hojas.iterrows()}
labels = list(opciones.keys())
label_actual = next((k for k,v in opciones.items() if v == st.session_state["hoja_id"]), labels[0])

sel_label = st.sidebar.selectbox("Hoja (semana)", options=labels, index=labels.index(label_actual))
st.session_state["hoja_id"] = opciones[sel_label]

row_sel = df_hojas[df_hojas["id"] == st.session_state["hoja_id"]].iloc[0]
semana_id = int(row_sel["id"])
sem_ini   = row_sel["semana_inicio"]
sem_fin   = row_sel["semana_fin"]
encargado_guardado = row_sel["encargado"] or "—"
cerrada   = int(row_sel["cerrada"])

# Navegación rápida
col_nav1, col_nav2, col_nav3 = st.sidebar.columns([1,1,1])
with col_nav1:
    if st.button("◀ Ant.", use_container_width=True):
        idx = df_hojas.index[df_hojas["id"] == semana_id][0]
        if idx + 1 < len(df_hojas):
            st.session_state["hoja_id"] = int(df_hojas.iloc[idx+1]["id"])
            st.rerun()
with col_nav2:
    if st.button("Hoy", use_container_width=True):
        ini = monday_of_week(date.today())
        fin = saturday_of_week(date.today())
        sid, _, _ = ensure_semana(ini, fin, None)
        st.session_state["hoja_id"] = int(sid)
        st.rerun()
with col_nav3:
    if st.button("Sig. ▶", use_container_width=True):
        idx = df_hojas.index[df_hojas["id"] == semana_id][0]
        if idx - 1 >= 0:
            st.session_state["hoja_id"] = int(df_hojas.iloc[idx-1]["id"])
            st.rerun()

# Crear nueva hoja (Lun–Sáb)
st.sidebar.markdown("#### ➕ Nueva hoja (Lun–Sáb)")
fecha_ref = st.sidebar.date_input("Fecha de referencia", value=sem_fin + timedelta(days=2))
if st.sidebar.button("Crear hoja", use_container_width=True):
    ini_n = monday_of_week(fecha_ref)
    fin_n = saturday_of_week(fecha_ref)
    sid_n, _, _ = ensure_semana(ini_n, fin_n, None)
    st.session_state["hoja_id"] = int(sid_n)
    st.success(f"Hoja creada: {ini_n} → {fin_n}")
    st.rerun()

# Encargado + estado de la HOJA actual
st.sidebar.caption(f"Hoja: **{sem_ini} → {sem_fin}** (Lun–Sáb)")
encargado_input = st.sidebar.text_input("Encargado de la semana", value=encargado_guardado, key="wk_encargado_input")
if (encargado_input or "—") != encargado_guardado:
    with get_conn() as conn:
        conn.execute("UPDATE semanas SET encargado=? WHERE id=?", (encargado_input.strip() or "—", int(semana_id)))
    encargado_guardado = encargado_input.strip() or "—"

if cerrada:
    st.sidebar.error(f"Semana CERRADA. Encargado: {encargado_guardado}")
    if st.sidebar.button("🔓 Abrir hoja", use_container_width=True):
        with get_conn() as conn:
            conn.execute("UPDATE semanas SET cerrada=0 WHERE id=?", (int(semana_id),))
        st.success("✅ Hoja abierta.")
        st.rerun()
else:
    st.sidebar.success(f"Semana ABIERTA. Encargado: {encargado_guardado}")
    if st.sidebar.button("🔒 Cerrar hoja", use_container_width=True):
        with get_conn() as conn:
            conn.execute("UPDATE semanas SET cerrada=1 WHERE id=?", (int(semana_id),))
        st.warning("🔒 Hoja cerrada.")
        st.rerun()

# -------------------- Tabs --------------------
reg_tab, montos_tab = st.tabs(["📋 Registros (Lun–Sáb)", "💰 Montos y Total (pago sábado)"])

# -------------------- TAB 1 – Registros --------------------
with reg_tab:
    st.markdown(f"## 📋 Registros (Lunes a Sábado) — Hoja {sem_ini} → {sem_fin}")
    st.subheader("Registrar día por trabajador")

    if cerrada:
        st.info("🔒 Esta hoja está cerrada. No se permiten altas ni ediciones.")

    disabled = bool(cerrada)

    # Fecha limitada a la hoja L–S
    c1, c2 = st.columns([1, 2])
    with c1:
        add_fecha = st.date_input(
            "Fecha",
            value=monday_of_week(sem_ini),
            min_value=sem_ini,
            max_value=sem_fin,
            key=f"add_fecha_{semana_id}",
            disabled=disabled,
        )

    # Modo trabajador
    modo = st.radio(
        "Modo de trabajador",
        ["Existente", "Nuevo"],
        horizontal=True,
        key=f"modo_trab_{semana_id}",
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
            key=f"trab_existente_{semana_id}",
            disabled=disabled,
        )

        coln1, coln2 = st.columns(2)
        with coln1:
            st.text_input("Nombre", value=sel_trab if sel_trab != "(Seleccione)" else "",
                          disabled=True, key=f"readonly_nombre_{semana_id}")
        with coln2:
            st.text_input("Cargo", value=cargos_map.get(sel_trab, "") if sel_trab != "(Seleccione)" else "",
                          disabled=True, key=f"readonly_cargo_{semana_id}")

        if sel_trab != "(Seleccione)":
            add_trab = sel_trab
            add_cargo = cargos_map.get(sel_trab, "")

    else:
        coln1, coln2 = st.columns(2)
        with coln1:
            add_trab = st.text_input("Nombre (nuevo)", key=f"nuevo_nombre_{semana_id}", disabled=disabled).strip()
        with coln2:
            add_cargo = st.text_input("Cargo", key=f"nuevo_cargo_{semana_id}", disabled=disabled).strip()

    # Monto y actividad
    col3, col4 = st.columns(2)
    with col3:
        add_monto = st.number_input(
            "Monto del día (S/)", min_value=0.0, step=1.0, value=0.0,
            key=f"add_monto_{semana_id}", disabled=disabled
        )
    with col4:
        add_act = st.text_input("Actividad (opcional)", key=f"add_act_{semana_id}", disabled=disabled)

    # Adicional sábado
    es_sabado = (isinstance(add_fecha, date) and add_fecha.weekday() == 5)
    colx = st.columns([1, 1])
    with colx[0]:
        add_extra_flag = st.checkbox(
            "Pago adicional de sábado",
            value=False,
            key=f"add_extra_flag_{semana_id}",
            disabled=(disabled or not es_sabado),
        )
    with colx[1]:
        add_extra_monto = st.number_input(
            "Monto adicional (solo sábado)",
            min_value=0.0, step=1.0, value=0.0,
            key=f"add_extra_monto_{semana_id}",
            disabled=(disabled or not es_sabado),
        )

    guardar = st.button("💾 Guardar registro", use_container_width=True, disabled=disabled, key=f"btn_guardar_{semana_id}")

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
                st.rerun()
            except Exception as e:
                st.error(f"Error guardando registro: {e}")

    # ----- Editor de trabajador (con BORRADO de registros) -----
    st.divider()
    st.markdown("### ✏️ Editar trabajador (catálogo)")
    with get_conn() as conn:
        cat_rows = conn.execute(
            "SELECT id, nombre, COALESCE(cargo, '') AS cargo, activo FROM trabajadores ORDER BY nombre"
        ).fetchall()

    if cat_rows:
        nombres_cat = [r["nombre"] for r in cat_rows]
        sel_edit = st.selectbox(
            "Selecciona trabajador",
            options=["(Seleccione)"] + nombres_cat,
            index=0,
            key=f"edit_trab_sel_{semana_id}"
        )

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

            # ---- BORRAR REGISTROS DE ESTA HOJA (SEMANA) ----
            st.markdown("#### 🧹 Registros de esta hoja para este trabajador")
            with get_conn() as conn:
                df_regs = pd.read_sql_query(
                    """
                    SELECT fecha, actividad, monto, extra_monto
                    FROM entradas
                    WHERE semana_id=? AND trabajador=?
                    ORDER BY date(fecha)
                    """,
                    conn,
                    params=(semana_id, sel_edit),
                )

            if df_regs.empty:
                st.info("Sin registros de esta hoja para este trabajador.")
            else:
                df_regs["fecha"] = pd.to_datetime(df_regs["fecha"]).dt.date.astype(str)
                df_regs = df_regs.rename(columns={
                    "fecha": "Fecha",
                    "actividad": "Actividad",
                    "monto": "Monto",
                    "extra_monto": "Monto adicional"
                })
                df_regs["Seleccionar"] = False

                edited = st.data_editor(
                    df_regs,
                    key=f"ed_regs_{semana_id}_{sel_edit}",
                    hide_index=True,
                    num_rows="fixed",
                    column_config={
                        "Fecha": st.column_config.DateColumn("Fecha", format="YYYY-MM-DD"),
                        "Monto": st.column_config.NumberColumn("Monto", step=1.0, help="Monto del día"),
                        "Monto adicional": st.column_config.NumberColumn("Monto adicional", step=1.0, help="Solo sábado"),
                        "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", help="Marca para eliminar"),
                    }
                )

                col_del1, col_del2 = st.columns([1, 1])
                with col_del1:
                    if st.button("🗑️ Eliminar seleccionados", type="primary", key=f"del_sel_{semana_id}_{sel_edit}"):
                        fechas_sel = [str(f) for f, s in zip(edited["Fecha"], edited["Seleccionar"]) if s]
                        if not fechas_sel:
                            st.warning("No hay filas seleccionadas.")
                        else:
                            try:
                                with get_conn() as conn:
                                    for f in fechas_sel:
                                        conn.execute(
                                            "DELETE FROM entradas WHERE semana_id=? AND trabajador=? AND fecha=?",
                                            (int(semana_id), sel_edit, f),
                                        )
                                st.success(f"Eliminados {len(fechas_sel)} registro(s).")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al eliminar: {e}")
                with col_del2:
                    if st.button("🗑️ Eliminar TODOS los registros de esta hoja", key=f"del_all_{semana_id}_{sel_edit}"):
                        try:
                            with get_conn() as conn:
                                conn.execute(
                                    "DELETE FROM entradas WHERE semana_id=? AND trabajador=?",
                                    (int(semana_id), sel_edit),
                                )
                            st.warning("Se eliminaron todos los registros de esta hoja para este trabajador.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar todo: {e}")
    else:
        st.info("Aún no tienes trabajadores en el catálogo.")

    # ----- Vista semanal -----
    st.divider()
    st.markdown(f"## 📊 Vista semanal (Lun–Sáb) — Hoja {sem_ini} → {sem_fin}")

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
        st.info("Sin registros en esta hoja.")
    else:
        df_det["fecha"] = pd.to_datetime(df_det["fecha"]).dt.date
        df_det["dow"] = pd.to_datetime(df_det["fecha"]).dt.weekday

        df_pivot = df_det.pivot_table(index=["trabajador"], columns="dow", values="monto", aggfunc="sum").fillna(0)
        df_pivot = df_pivot.rename(columns={i: label_dow(i) for i in range(6)})

        extras = (
            df_det[df_det["dow"] == 5]
            .groupby("trabajador", as_index=False)
            .agg(monto_adicional=("extra_monto", "sum"))
        )
        dias = df_det.groupby("trabajador")["fecha"].nunique().rename("dias").reset_index()
        cargos = df_det.groupby("trabajador")["cargo"].agg(lambda x: next((v for v in x if v), "")).rename("cargo").reset_index()

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
    st.markdown(f"## 💰 Montos y Total (pago sábado) — Hoja {sem_ini} → {sem_fin}")

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
        st.info("Sin registros en esta hoja.")
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
