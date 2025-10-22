with st.form("add_form", clear_on_submit=True):
    disabled = bool(cerrada)

    # Fecha (Lun–Sáb)
    c1, c2 = st.columns([1, 2])
    with c1:
        add_fecha = st.date_input(
            "Fecha",
            value=sem_ini,
            min_value=sem_ini,
            max_value=sem_fin,
            key="add_fecha",
            disabled=disabled,
        )

    # --- Modo de trabajador: EXISTENTE vs NUEVO (mutuamente excluyente) ---
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
        # SOLO EXISTENTE: select con autocomplete + cargo en solo lectura
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
        # SOLO NUEVO: inputs activos para nombre y cargo (obligatorios)
        coln1, coln2 = st.columns(2)
        with coln1:
            add_trab = st.text_input(
                "Nombre (nuevo)",
                key="nuevo_nombre",
                disabled=disabled,
            ).strip()
        with coln2:
            add_cargo = st.text_input(
                "Cargo",
                key="nuevo_cargo",
                disabled=disabled,
            ).strip()

    # Monto día y actividad
    col3, col4 = st.columns(2)
    with col3:
        add_monto = st.number_input(
            "Monto del día (S/)", min_value=0.0, step=1.0, value=0.0, key="add_monto", disabled=disabled
        )
    with col4:
        add_act = st.text_input("Actividad (opcional)", key="add_act", disabled=disabled)

    # Adicional sábado (solo si es sábado)
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

    submitted = st.form_submit_button("💾 Guardar registro", use_container_width=True, disabled=disabled)
