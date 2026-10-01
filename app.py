import streamlit as st
import pandas as pd
from datetime import date, timedelta
import db

st.set_page_config(page_title="Flujo", page_icon="💰", layout="wide")
st.title("💰 Flujo personal")

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt(v, moneda="ARS"):
    sym = "USD" if moneda == "USD" else "$"
    return f"{sym} {float(v or 0):,.0f}"


def _calcular_saldo_caja(caja_id, ajustes, ingresos, egresos, transferencias):
    """Saldo actual = saldo_inicial + ingresos - egresos ± transferencias ± ajustes libres."""
    saldo = 0.0
    fecha_ini = None
    for a in ajustes:
        if a["caja_id"] == caja_id and a["tipo"] == "inicial":
            saldo = float(a["monto"])
            fecha_ini = a["fecha"]
            break
    for r in ingresos:
        if r.get("caja_id") == caja_id and (not fecha_ini or r["fecha"] >= fecha_ini):
            saldo += float(r["monto"])
    for r in egresos:
        if r.get("caja_id") == caja_id and (not fecha_ini or r["fecha"] >= fecha_ini):
            saldo -= float(r["monto"])
    for r in transferencias:
        if not fecha_ini or r["fecha"] >= fecha_ini:
            if r.get("destino_id") == caja_id:
                saldo += float(r["monto"])
            if r.get("origen_id") == caja_id:
                saldo -= float(r["monto"])
    for a in ajustes:
        if a["caja_id"] == caja_id and a["tipo"] == "ajuste" and (not fecha_ini or a["fecha"] >= fecha_ini):
            saldo += float(a["monto"])
    return saldo


def _mes_actual():
    hoy = date.today()
    return date(hoy.year, hoy.month, 1), hoy


def _nombre_caja(row):
    c = row.get("cajas")
    return c["nombre"] if isinstance(c, dict) else "—"


def _nombre_rubro(row, tipo):
    r = row.get(f"rubros_{tipo}s")
    return r["nombre"] if isinstance(r, dict) else "—"


def _nombre_subrubro(row, tipo):
    s = row.get(f"subrubros_{tipo}s")
    return s["nombre"] if isinstance(s, dict) else "—"


def _nombre_item(row, tipo):
    i = row.get(f"items_{tipo}s")
    return i["nombre"] if isinstance(i, dict) else "—"


def _safe_date(val):
    if not val:
        return date.min
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return date.min


def _fmt_fecha(val):
    if not val:
        return "—"
    try:
        return pd.to_datetime(val).strftime("%d/%m/%Y")
    except Exception:
        return str(val)


# ── Tabs principales ──────────────────────────────────────────────────────────

tab_percibido, tab_movimientos, tab_ingresos, tab_egresos, tab_transferencias, tab_ajustes, tab_config = st.tabs([
    "📊 Percibido",
    "📋 Movimientos",
    "💰 Ingresos",
    "💸 Egresos",
    "↔️ Transferencias",
    "🔧 Ajustes",
    "⚙️ Configuración",
])

# ═══════════════════════════════════════════════════════════════════════════════
# PERCIBIDO
# ═══════════════════════════════════════════════════════════════════════════════

def _render_seccion_jerarquia(lista, tipo, titulo, moneda, color):
    """Renders a 3-level nested section (rubro→subrubro→item) identical to tab Todos."""
    _sym = "USD" if moneda == "USD" else "$"
    _fmt_n = f"{_sym} %,.0f"
    _total = sum(float(r.get("monto") or 0) for r in lista)
    st.markdown(
        f"**{titulo}** · {len(lista)} registros<br>"
        f"<span style='font-size:0.8em;color:#888'>Total</span><br>"
        f"<span style='font-size:1.3em;font-weight:700;color:{color}'>{fmt(_total, moneda)}</span>",
        unsafe_allow_html=True,
    )
    if not lista:
        st.caption("Sin registros en el período.")
        return _total
    _by_rub: dict = {}
    for r in lista:
        _rn  = _nombre_rubro(r, tipo)
        _sn  = _nombre_subrubro(r, tipo)
        _itn = _nombre_item(r, tipo)
        _by_rub.setdefault(_rn, {}).setdefault(_sn, {}).setdefault(_itn, []).append(r)
    for _rn, _subs in sorted(_by_rub.items()):
        _r_tot = sum(float(x.get("monto") or 0) for s in _subs.values() for items in s.values() for x in items)
        _r_cnt = sum(len(items) for s in _subs.values() for items in s.values())
        with st.expander(f"{_rn.upper()} ({_r_cnt}) — {fmt(_r_tot, moneda)}"):
            for _sn, _s_items in sorted(_subs.items()):
                _s_tot = sum(float(x.get("monto") or 0) for items in _s_items.values() for x in items)
                _s_cnt = sum(len(items) for items in _s_items.values())
                with st.expander(f"{_sn.upper()} ({_s_cnt}) — {fmt(_s_tot, moneda)}"):
                    for _itn, _it_rows in sorted(_s_items.items()):
                        _it_tot = sum(float(x.get("monto") or 0) for x in _it_rows)
                        _it_cnt = len(_it_rows)
                        with st.expander(f"{_itn.upper()} ({_it_cnt}) — {fmt(_it_tot, moneda)}"):
                            _rows = [{"Fecha": _fmt_fecha(r.get("fecha")),
                                      "Monto": float(r.get("monto") or 0),
                                      "Descripción": r.get("descripcion") or ""}
                                     for r in sorted(_it_rows, key=lambda x: str(x.get("fecha") or ""), reverse=True)]
                            st.dataframe(pd.DataFrame(_rows), hide_index=True, use_container_width=True,
                                         column_config={"Monto": st.column_config.NumberColumn("Monto", format=_fmt_n)})
    return _total


with tab_percibido:
    _d1, _d2 = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde = c1.date_input("Desde", value=_d1, format="DD/MM/YYYY", key="p_desde")
    _hasta = c2.date_input("Hasta", value=_d2, format="DD/MM/YYYY", key="p_hasta")

    _ing_all   = db.cargar_ingresos(_desde, _hasta)
    _egr_all   = db.cargar_egresos(_desde, _hasta)
    _trf_all   = db.cargar_transferencias()
    _aj_all    = db.cargar_ajustes()
    _cajas_all = db.cargar_cajas()
    _ing_todo  = db.cargar_ingresos()
    _egr_todo  = db.cargar_egresos()

    def _render_percibido(moneda):
        _cajas_m = [c for c in _cajas_all if c.get("moneda", "ARS") == moneda]
        _ids_m   = {c["id"] for c in _cajas_m}

        # Saldos actuales
        if _cajas_m:
            st.markdown("**Saldo actual por caja**")
            _saldo_cols = st.columns(max(len(_cajas_m), 1))
            for i, c in enumerate(_cajas_m):
                _s = _calcular_saldo_caja(c["id"], _aj_all, _ing_todo, _egr_todo, _trf_all)
                _saldo_cols[i].metric(c["nombre"], fmt(_s, moneda))
            st.divider()

        _ing   = [r for r in _ing_all if r.get("caja_id") in _ids_m]
        _egr_g = [r for r in _egr_all if r.get("caja_id") in _ids_m and r.get("tipo", "gasto") == "gasto"]
        _egr_i = [r for r in _egr_all if r.get("caja_id") in _ids_m and r.get("tipo") == "inversion"]

        _tot_ing = _render_seccion_jerarquia(_ing,   "ingreso", "Ingresos",   moneda, "#2e7d32")
        st.divider()
        _tot_gas = _render_seccion_jerarquia(_egr_g, "egreso",  "Gastos",     moneda, "#c62828")
        if _egr_i:
            st.divider()
            _render_seccion_jerarquia(_egr_i, "egreso", "Inversiones", moneda, "#5e35b1")

        st.divider()
        _neto = _tot_ing - _tot_gas
        _color_neto = "#2e7d32" if _neto >= 0 else "#c62828"
        st.markdown(
            f"**Neto (Ingresos − Gastos)**<br>"
            f"<span style='font-size:1.5em;font-weight:700;color:{_color_neto}'>{fmt(_neto, moneda)}</span>",
            unsafe_allow_html=True,
        )

    _ptab_ars, _ptab_usd = st.tabs(["🇦🇷 Pesos (ARS)", "🇺🇸 Dólares (USD)"])
    with _ptab_ars:
        _render_percibido("ARS")
    with _ptab_usd:
        _render_percibido("USD")


# ═══════════════════════════════════════════════════════════════════════════════
# MOVIMIENTOS
# ═══════════════════════════════════════════════════════════════════════════════

def _metricas_colores(col, label, valor, moneda, color):
    col.markdown(
        f"<div style='font-size:0.78em;color:#888;margin-bottom:2px'>{label}</div>"
        f"<div style='font-size:1.35em;font-weight:700;color:{color}'>{fmt(valor, moneda)}</div>",
        unsafe_allow_html=True,
    )


def _render_movimientos_caja(caja, desde, hasta, ing_all, egr_all, trf_all, aj_all, saldo_actual):
    caja_id = caja["id"]
    moneda  = caja.get("moneda", "ARS")
    _sym    = "USD" if moneda == "USD" else "$"
    _fmt_n  = f"{_sym} %,.0f"
    _ds     = str(desde)
    _hs     = str(hasta)

    def _en(fecha): return _ds <= str(fecha or "") <= _hs

    _ing   = [r for r in ing_all  if r.get("caja_id") == caja_id and _en(r.get("fecha"))]
    _egr_g = [r for r in egr_all  if r.get("caja_id") == caja_id and r.get("tipo","gasto") == "gasto"     and _en(r.get("fecha"))]
    _egr_i = [r for r in egr_all  if r.get("caja_id") == caja_id and r.get("tipo") == "inversion"         and _en(r.get("fecha"))]
    _trf_e = [r for r in trf_all  if r.get("destino_id") == caja_id and _en(r.get("fecha"))]
    _trf_s = [r for r in trf_all  if r.get("origen_id")  == caja_id and _en(r.get("fecha"))]
    _aj_p  = [r for r in aj_all   if r.get("caja_id") == caja_id and r.get("tipo") == "ajuste"
              and float(r.get("monto") or 0) > 0 and _en(r.get("fecha"))]
    _aj_n  = [r for r in aj_all   if r.get("caja_id") == caja_id and r.get("tipo") == "ajuste"
              and float(r.get("monto") or 0) < 0 and _en(r.get("fecha"))]

    _tot_ent = (sum(float(r.get("monto") or 0) for r in _ing)
              + sum(float(r.get("monto") or 0) for r in _trf_e)
              + sum(float(r.get("monto") or 0) for r in _aj_p))
    _tot_sal = (sum(float(r.get("monto") or 0) for r in _egr_g)
              + sum(float(r.get("monto") or 0) for r in _egr_i)
              + sum(float(r.get("monto") or 0) for r in _trf_s)
              + sum(-float(r.get("monto") or 0) for r in _aj_n))

    # Métricas de la caja
    _mc1, _mc2, _mc3 = st.columns(3)
    _metricas_colores(_mc1, "Saldo actual", saldo_actual, moneda, "#4472C4")
    _metricas_colores(_mc2, "Entradas",     _tot_ent,    moneda, "#2e7d32")
    _metricas_colores(_mc3, "Salidas",      _tot_sal,    moneda, "#c62828")

    # Helpers para armar filas de tabla
    def _rows_jerarquia(rows, tipo):
        return sorted([{
            "Fecha":       _fmt_fecha(r.get("fecha")),
            "Concepto":    " / ".join(x for x in [_nombre_rubro(r, tipo), _nombre_subrubro(r, tipo), _nombre_item(r, tipo)] if x and x != "—") or "—",
            "Monto":       float(r.get("monto") or 0),
            "Descripción": r.get("descripcion") or "",
        } for r in rows], key=lambda x: x["Fecha"], reverse=True)

    def _rows_trf(rows):
        return sorted([{
            "Fecha":           _fmt_fecha(r.get("fecha")),
            "Origen → Destino": f"{(r.get('origen') or {}).get('nombre','—')} → {(r.get('destino') or {}).get('nombre','—')}",
            "Monto":           float(r.get("monto") or 0),
            "Concepto":        r.get("concepto") or "",
        } for r in rows], key=lambda x: x["Fecha"], reverse=True)

    def _rows_aj(rows):
        return sorted([{
            "Fecha": _fmt_fecha(r.get("fecha")),
            "Nota":  r.get("nota") or "—",
            "Monto": abs(float(r.get("monto") or 0)),
        } for r in rows], key=lambda x: x["Fecha"], reverse=True)

    def _grupo(label, rows, build_fn):
        if not rows:
            return
        _tot = sum(float(r.get("monto") or 0) for r in rows)
        with st.expander(f"{label} ({len(rows)}) — {fmt(_tot, moneda)}"):
            _df = pd.DataFrame(build_fn(rows))
            st.dataframe(_df, hide_index=True, use_container_width=True,
                         column_config={"Monto": st.column_config.NumberColumn("Monto", format=_fmt_n)})

    _grupo("ENTRADAS - INGRESOS",       _ing,   lambda r: _rows_jerarquia(r, "ingreso"))
    _grupo("ENTRADAS - TRANSFERENCIAS", _trf_e, _rows_trf)
    _grupo("ENTRADAS - AJUSTES",        _aj_p,  _rows_aj)
    _grupo("SALIDAS - EGRESOS",         _egr_g, lambda r: _rows_jerarquia(r, "egreso"))
    _grupo("SALIDAS - INVERSIONES",     _egr_i, lambda r: _rows_jerarquia(r, "egreso"))
    _grupo("SALIDAS - TRANSFERENCIAS",  _trf_s, _rows_trf)
    _grupo("SALIDAS - AJUSTES",         _aj_n,  _rows_aj)


with tab_movimientos:
    _d1m, _d2m = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde_m = c1.date_input("Desde", value=_d1m, format="DD/MM/YYYY", key="m_desde")
    _hasta_m = c2.date_input("Hasta", value=_d2m, format="DD/MM/YYYY", key="m_hasta")

    _ing_m_all   = db.cargar_ingresos()
    _egr_m_all   = db.cargar_egresos()
    _trf_m_all   = db.cargar_transferencias()
    _aj_m_all    = db.cargar_ajustes()
    _cajas_m_all = db.cargar_cajas()

    def _render_mov_moneda(moneda):
        _cajas_mon = [c for c in _cajas_m_all if c.get("moneda", "ARS") == moneda and c.get("activa", True)]
        if not _cajas_mon:
            st.info("No hay cajas configuradas para esta moneda.")
            return

        _saldos = {c["id"]: _calcular_saldo_caja(c["id"], _aj_m_all, _ing_m_all, _egr_m_all, _trf_m_all)
                   for c in _cajas_mon}

        # Calcular entradas/salidas del período para el total general
        _ds, _hs = str(_desde_m), str(_hasta_m)
        def _en(f): return _ds <= str(f or "") <= _hs
        _ids_mon = {c["id"] for c in _cajas_mon}

        _tot_ent_g = (sum(float(r.get("monto") or 0) for r in _ing_m_all  if r.get("caja_id") in _ids_mon and _en(r.get("fecha")))
                    + sum(float(r.get("monto") or 0) for r in _trf_m_all  if r.get("destino_id") in _ids_mon and _en(r.get("fecha")))
                    + sum(float(r.get("monto") or 0) for r in _aj_m_all   if r.get("caja_id") in _ids_mon and r.get("tipo") == "ajuste" and float(r.get("monto") or 0) > 0 and _en(r.get("fecha"))))
        _tot_sal_g = (sum(float(r.get("monto") or 0) for r in _egr_m_all  if r.get("caja_id") in _ids_mon and _en(r.get("fecha")))
                    + sum(float(r.get("monto") or 0) for r in _trf_m_all  if r.get("origen_id")  in _ids_mon and _en(r.get("fecha")))
                    + sum(-float(r.get("monto") or 0) for r in _aj_m_all  if r.get("caja_id") in _ids_mon and r.get("tipo") == "ajuste" and float(r.get("monto") or 0) < 0 and _en(r.get("fecha"))))
        _tot_saldo_g = sum(_saldos.values())

        # ── Total general ──────────────────────────────────────────────────────
        st.markdown("### Total general")
        _tg1, _tg2, _tg3 = st.columns(3)
        _metricas_colores(_tg1, "Saldo",    _tot_saldo_g, moneda, "#4472C4")
        _metricas_colores(_tg2, "Entradas", _tot_ent_g,   moneda, "#2e7d32")
        _metricas_colores(_tg3, "Salidas",  _tot_sal_g,   moneda, "#c62828")
        st.divider()

        # ── Por caja ───────────────────────────────────────────────────────────
        for _caja in _cajas_mon:
            st.markdown(f"### {_caja['nombre']}")
            _render_movimientos_caja(_caja, _desde_m, _hasta_m,
                                     _ing_m_all, _egr_m_all, _trf_m_all, _aj_m_all,
                                     _saldos[_caja["id"]])
            st.divider()

    _mtab_ars, _mtab_usd = st.tabs(["🇦🇷 Pesos (ARS)", "🇺🇸 Dólares (USD)"])
    with _mtab_ars:
        _render_mov_moneda("ARS")
    with _mtab_usd:
        _render_mov_moneda("USD")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS JERARQUÍA (compartidos por ingresos y egresos)
# ═══════════════════════════════════════════════════════════════════════════════

def _render_fields_jerarquia(tipo, pfx, subs_by_rubro, items_by_sub, rubro_opts, caja_opts, defaults=None, show_tipo=False):
    """Renderiza fecha, rubro→subrubro→item, monto, caja, descripción. Retorna dict con los valores."""
    d = defaults or {}
    fecha  = st.date_input("Fecha", value=d.get("fecha", date.today()), format="DD/MM/YYYY", key=f"{pfx}_fecha")
    rubro_list = [""] + list(rubro_opts.keys())
    r_idx  = rubro_list.index(d.get("rubro_nm", "")) if d.get("rubro_nm") in rubro_list else 0
    rubro  = st.selectbox("Rubro", rubro_list, index=r_idx, key=f"{pfx}_rubro")
    sub_opts = {s["nombre"]: s["id"] for s in subs_by_rubro.get(rubro_opts.get(rubro), [])} if rubro else {}
    s_list = [""] + list(sub_opts.keys())
    s_idx  = s_list.index(d.get("sub_nm", "")) if d.get("sub_nm") in s_list else 0
    subrubro = st.selectbox("Subrubro", s_list, index=s_idx, key=f"{pfx}_sub")
    item_map = {i["nombre"]: i["id"] for i in items_by_sub.get(sub_opts.get(subrubro), [])} if subrubro else {}
    i_list = [""] + list(item_map.keys())
    i_idx  = i_list.index(d.get("item_nm", "")) if d.get("item_nm") in i_list else 0
    item_nm = st.selectbox("Ítem", i_list, index=i_idx, key=f"{pfx}_item")
    monto_str = st.text_input("Monto ($)", value=d.get("monto_str", ""), key=f"{pfx}_monto")
    try:
        monto = float(monto_str.replace(",", ".")) if monto_str else 0.0
    except ValueError:
        monto = 0.0
    caja_list = [""] + list(caja_opts.keys())
    c_idx  = caja_list.index(d.get("caja_nm", "")) if d.get("caja_nm") in caja_list else 0
    caja   = st.selectbox("Caja", caja_list, index=c_idx, key=f"{pfx}_caja")
    desc   = st.text_input("Descripción (opcional)", value=d.get("desc", ""), key=f"{pfx}_desc")
    if show_tipo:
        _tipo_list = ["gasto", "inversion"]
        _t_idx = _tipo_list.index(d.get("tipo", "gasto")) if d.get("tipo") in _tipo_list else 0
        egreso_tipo = st.selectbox("Tipo", _tipo_list, index=_t_idx,
                                   format_func=lambda x: "💸 Gasto" if x == "gasto" else "📈 Inversión",
                                   key=f"{pfx}_tipo")
    else:
        egreso_tipo = d.get("tipo", "gasto")
    return {"fecha": fecha, "rubro": rubro, "sub_opts": sub_opts, "subrubro": subrubro,
            "item_nm": item_nm, "item_id": item_map.get(item_nm),
            "monto": monto, "caja": caja, "desc": desc, "tipo": egreso_tipo}


# ═══════════════════════════════════════════════════════════════════════════════
# INGRESOS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_ingresos:
    _oi_rubros    = db.cargar_rubros_ingresos()
    _oi_cajas     = db.cargar_cajas()
    _oi_rubro_map = {r["id"]: r["nombre"] for r in _oi_rubros}
    _oi_caja_map  = {c["id"]: c["nombre"] for c in _oi_cajas}
    _oi_rubro_opts = {r["nombre"]: r["id"] for r in _oi_rubros}
    _oi_caja_opts  = {c["nombre"]: c["id"] for c in _oi_cajas}

    _all_oi_subs  = db.cargar_subrubros_ingresos()
    _all_oi_items = db.cargar_items_ingresos()
    _oi_subs_by_rubro: dict = {}
    for _s in _all_oi_subs:
        _oi_subs_by_rubro.setdefault(_s["rubro_id"], []).append(_s)
    _oi_items_by_sub: dict = {}
    for _i in _all_oi_items:
        _oi_items_by_sub.setdefault(_i["subrubro_id"], []).append(_i)

    _oi_tab1, _oi_tab2, _oi_tab3 = st.tabs(["➕ Ingresar", "✏️ Editar / Eliminar", "📋 Todos los ingresos"])

    with _oi_tab1:
        @st.fragment
        def _oi_nuevo():
            _seed = st.session_state.get("ni_seed", 0)
            _pfx  = f"ni{_seed}"
            _fecha_def = st.session_state.pop("ni_fecha_keep", date.today())
            with st.container(border=True):
                _f = _render_fields_jerarquia("ingreso", _pfx, _oi_subs_by_rubro, _oi_items_by_sub,
                                              _oi_rubro_opts, _oi_caja_opts, defaults={"fecha": _fecha_def})
                if st.button("Guardar ingreso", type="primary", key=f"ni_guardar{_seed}"):
                    if not _f["rubro"]:
                        st.error("Seleccioná un rubro.")
                    elif not _f["subrubro"]:
                        st.error("Seleccioná un subrubro.")
                    elif not _f["item_id"]:
                        st.error("Seleccioná un ítem.")
                    elif _f["monto"] <= 0:
                        st.error("El monto debe ser mayor a 0.")
                    else:
                        try:
                            db.guardar_ingreso(
                                fecha=_f["fecha"],
                                rubro_id=_oi_rubro_opts.get(_f["rubro"]),
                                subrubro_id=_f["sub_opts"].get(_f["subrubro"]),
                                item_id=_f["item_id"],
                                monto=_f["monto"],
                                caja_id=_oi_caja_opts.get(_f["caja"]),
                                descripcion=_f["desc"],
                            )
                            st.session_state["ni_fecha_keep"] = _f["fecha"]
                            st.session_state["ni_seed"] = _seed + 1
                            st.session_state["oi_ok"] = True
                            st.rerun(scope="fragment")
                        except Exception as e:
                            st.error(f"Error: {e}")
                if st.session_state.pop("oi_ok", False):
                    st.success("✅ Ingreso guardado.")
        _oi_nuevo()

    with _oi_tab2:
        @st.fragment
        def _oi_editar():
            _lista = db.cargar_ingresos()
            if not _lista:
                st.info("No hay ingresos cargados todavía.")
                return
            with st.form("oi_filt", border=False):
                _dc1, _dc2 = st.columns(2)
                _oi_e_desde = _dc1.date_input("Desde", value=date(date.today().year, date.today().month, 1), format="DD/MM/YYYY", key="oi_e_desde")
                _oi_e_hasta = _dc2.date_input("Hasta", value=date.today(), format="DD/MM/YYYY", key="oi_e_hasta")
                st.form_submit_button("🔄 Actualizar", type="primary")
            _lista = [o for o in _lista if _oi_e_desde <= _safe_date(o.get("fecha")) <= _oi_e_hasta]
            if not _lista:
                st.caption("Sin registros en el rango.")
                return
            for _oi in _lista:
                _oi_id   = _oi["id"]
                _r_nm    = (_oi.get("rubros_ingresos") or {}).get("nombre") or _oi_rubro_map.get(_oi.get("rubro_id"), "—")
                _s_nm    = (_oi.get("subrubros_ingresos") or {}).get("nombre") or "—"
                _it_nm   = (_oi.get("items_ingresos") or {}).get("nombre") or ""
                _cj_nm   = _oi_caja_map.get(_oi.get("caja_id"), "—")
                _mn      = float(_oi.get("monto") or 0)
                _fch     = _oi.get("fecha", "")
                with st.container(border=True):
                    _ca, _cb, _cc = st.columns([5, 1, 1])
                    _it_str = f" · {_it_nm}" if _it_nm else ""
                    _ca.markdown(f"**{_fmt_fecha(_fch)}** · {_r_nm} / {_s_nm}{_it_str} · **$ {_mn:,.0f}** · {_cj_nm}")
                    if _cb.button("✏️", key=f"oi_edit_{_oi_id}"):
                        st.session_state[f"oi_editing_{_oi_id}"] = True
                        st.rerun(scope="fragment")
                    if _cc.button("🗑️", key=f"oi_del_{_oi_id}"):
                        db.eliminar_ingreso(_oi_id)
                        st.rerun(scope="fragment")
                if st.session_state.get(f"oi_editing_{_oi_id}"):
                    with st.container(border=True):
                        _e = _render_fields_jerarquia("ingreso", f"oie{_oi_id}", _oi_subs_by_rubro, _oi_items_by_sub,
                                                      _oi_rubro_opts, _oi_caja_opts, defaults={
                                                          "fecha": _safe_date(_fch) or date.today(),
                                                          "rubro_nm": _r_nm, "sub_nm": _s_nm, "item_nm": _it_nm,
                                                          "monto_str": str(_mn), "caja_nm": _cj_nm,
                                                          "desc": _oi.get("descripcion") or "",
                                                      })
                        _ec1, _ec2 = st.columns(2)
                        if _ec1.button("Guardar", type="primary", key=f"oi_save_{_oi_id}"):
                            if not _e["rubro"] or not _e["item_id"] or _e["monto"] <= 0:
                                st.error("Completá rubro, ítem y monto.")
                            else:
                                db.actualizar_ingreso(_oi_id, _e["fecha"],
                                    _oi_rubro_opts.get(_e["rubro"]),
                                    _e["sub_opts"].get(_e["subrubro"]),
                                    _e["item_id"],
                                    _oi_caja_opts.get(_e["caja"]),
                                    _e["monto"], _e["desc"])
                                st.session_state.pop(f"oi_editing_{_oi_id}", None)
                                st.rerun(scope="fragment")
                        if _ec2.button("Cancelar", key=f"oi_cancel_{_oi_id}"):
                            st.session_state.pop(f"oi_editing_{_oi_id}", None)
                            st.rerun(scope="fragment")
        _oi_editar()

    with _oi_tab3:
        @st.fragment
        def _oi_todos():
            _lista = db.cargar_ingresos()
            if not _lista:
                st.info("No hay ingresos cargados todavía.")
                return
            with st.form("oi_all_filt", border=False):
                _dc1, _dc2 = st.columns(2)
                _oi_v_desde = _dc1.date_input("Desde", value=date(date.today().year, date.today().month, 1), format="DD/MM/YYYY", key="oi_v_desde")
                _oi_v_hasta = _dc2.date_input("Hasta", value=date.today(), format="DD/MM/YYYY", key="oi_v_hasta")
                st.form_submit_button("🔄 Actualizar", type="primary")
            _lista = [o for o in _lista if _oi_v_desde <= _safe_date(o.get("fecha")) <= _oi_v_hasta]
            if not _lista:
                st.caption("Sin registros en el rango.")
                return
            _by_rub: dict = {}
            for _oi in _lista:
                _r = (_oi.get("rubros_ingresos") or {}).get("nombre") or "—"
                _s = (_oi.get("subrubros_ingresos") or {}).get("nombre") or "—"
                _it = (_oi.get("items_ingresos") or {}).get("nombre") or "—"
                _by_rub.setdefault(_r, {}).setdefault(_s, {}).setdefault(_it, []).append(_oi)
            _total = sum(float(x.get("monto") or 0) for x in _lista)
            st.metric("Total", fmt(_total))
            for _r_nm, _subs in sorted(_by_rub.items()):
                _r_tot = sum(float(x.get("monto") or 0) for s in _subs.values() for items in s.values() for x in items)
                with st.expander(f"{_r_nm} — $ {_r_tot:,.0f}"):
                    for _s_nm, _s_items in sorted(_subs.items()):
                        _s_tot = sum(float(x.get("monto") or 0) for items in _s_items.values() for x in items)
                        with st.expander(f"{_s_nm} — $ {_s_tot:,.0f}"):
                            for _it_nm, _it_items in sorted(_s_items.items()):
                                _it_tot = sum(float(x.get("monto") or 0) for x in _it_items)
                                with st.expander(f"{_it_nm} — $ {_it_tot:,.0f}"):
                                    _rows = [{"Fecha": _fmt_fecha(_oi.get("fecha")),
                                              "Monto": float(_oi.get("monto") or 0),
                                              "Caja": _oi_caja_map.get(_oi.get("caja_id"), "—"),
                                              "Descripción": _oi.get("descripcion") or ""}
                                             for _oi in sorted(_it_items, key=lambda x: str(x.get("fecha") or ""), reverse=True)]
                                    st.dataframe(pd.DataFrame(_rows), hide_index=True, use_container_width=True,
                                                 column_config={"Monto": st.column_config.NumberColumn("Monto ($)", format="$ %,.0f")})
        _oi_todos()


# ═══════════════════════════════════════════════════════════════════════════════
# EGRESOS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_egresos:
    _oe_rubros    = db.cargar_rubros_egresos()
    _oe_cajas     = db.cargar_cajas()
    _oe_rubro_map = {r["id"]: r["nombre"] for r in _oe_rubros}
    _oe_caja_map  = {c["id"]: c["nombre"] for c in _oe_cajas}
    _oe_rubro_opts = {r["nombre"]: r["id"] for r in _oe_rubros}
    _oe_caja_opts  = {c["nombre"]: c["id"] for c in _oe_cajas}

    _all_oe_subs  = db.cargar_subrubros_egresos()
    _all_oe_items = db.cargar_items_egresos()
    _oe_subs_by_rubro: dict = {}
    for _s in _all_oe_subs:
        _oe_subs_by_rubro.setdefault(_s["rubro_id"], []).append(_s)
    _oe_items_by_sub: dict = {}
    for _i in _all_oe_items:
        _oe_items_by_sub.setdefault(_i["subrubro_id"], []).append(_i)

    _oe_tab1, _oe_tab2, _oe_tab3 = st.tabs(["➕ Ingresar", "✏️ Editar / Eliminar", "📋 Todos los egresos"])

    with _oe_tab1:
        @st.fragment
        def _oe_nuevo():
            _seed = st.session_state.get("ne_seed", 0)
            _pfx  = f"ne{_seed}"
            _fecha_def = st.session_state.pop("ne_fecha_keep", date.today())
            with st.container(border=True):
                _f = _render_fields_jerarquia("egreso", _pfx, _oe_subs_by_rubro, _oe_items_by_sub,
                                              _oe_rubro_opts, _oe_caja_opts, defaults={"fecha": _fecha_def}, show_tipo=True)
                if st.button("Guardar egreso", type="primary", key=f"ne_guardar{_seed}"):
                    if not _f["rubro"]:
                        st.error("Seleccioná un rubro.")
                    elif not _f["subrubro"]:
                        st.error("Seleccioná un subrubro.")
                    elif not _f["item_id"]:
                        st.error("Seleccioná un ítem.")
                    elif _f["monto"] <= 0:
                        st.error("El monto debe ser mayor a 0.")
                    else:
                        try:
                            db.guardar_egreso(
                                fecha=_f["fecha"],
                                rubro_id=_oe_rubro_opts.get(_f["rubro"]),
                                subrubro_id=_f["sub_opts"].get(_f["subrubro"]),
                                item_id=_f["item_id"],
                                monto=_f["monto"],
                                caja_id=_oe_caja_opts.get(_f["caja"]),
                                descripcion=_f["desc"],
                                tipo=_f["tipo"],
                            )
                            st.session_state["ne_fecha_keep"] = _f["fecha"]
                            st.session_state["ne_seed"] = _seed + 1
                            st.session_state["oe_ok"] = True
                            st.rerun(scope="fragment")
                        except Exception as e:
                            st.error(f"Error: {e}")
                if st.session_state.pop("oe_ok", False):
                    st.success("✅ Egreso guardado.")
        _oe_nuevo()

    with _oe_tab2:
        @st.fragment
        def _oe_editar():
            _lista = db.cargar_egresos()
            if not _lista:
                st.info("No hay egresos cargados todavía.")
                return
            with st.form("oe_filt", border=False):
                _dc1, _dc2 = st.columns(2)
                _oe_e_desde = _dc1.date_input("Desde", value=date(date.today().year, date.today().month, 1), format="DD/MM/YYYY", key="oe_e_desde")
                _oe_e_hasta = _dc2.date_input("Hasta", value=date.today(), format="DD/MM/YYYY", key="oe_e_hasta")
                st.form_submit_button("🔄 Actualizar", type="primary")
            _lista = [o for o in _lista if _oe_e_desde <= _safe_date(o.get("fecha")) <= _oe_e_hasta]
            if not _lista:
                st.caption("Sin registros en el rango.")
                return

            _rubros_en = sorted({(o.get("rubros_egresos") or {}).get("nombre") or "—" for o in _lista})
            _fil_r = st.selectbox("Rubro", ["Todos"] + _rubros_en, key="oe_fil_r")
            if _fil_r != "Todos":
                _lista = [o for o in _lista if (o.get("rubros_egresos") or {}).get("nombre") == _fil_r]
            _subs_en = sorted({(o.get("subrubros_egresos") or {}).get("nombre") or "—" for o in _lista})
            _fil_s = st.selectbox("Subrubro", ["Todos"] + _subs_en, key="oe_fil_s")
            if _fil_s != "Todos":
                _lista = [o for o in _lista if (o.get("subrubros_egresos") or {}).get("nombre") == _fil_s]

            for _oe in _lista:
                _oe_id  = _oe["id"]
                _r_nm   = (_oe.get("rubros_egresos") or {}).get("nombre") or _oe_rubro_map.get(_oe.get("rubro_id"), "—")
                _s_nm   = (_oe.get("subrubros_egresos") or {}).get("nombre") or "—"
                _it_nm  = (_oe.get("items_egresos") or {}).get("nombre") or ""
                _cj_nm  = _oe_caja_map.get(_oe.get("caja_id"), "—")
                _mn     = float(_oe.get("monto") or 0)
                _fch    = _oe.get("fecha", "")
                with st.container(border=True):
                    _ca, _cb, _cc = st.columns([5, 1, 1])
                    _it_str = f" · {_it_nm}" if _it_nm else ""
                    _ca.markdown(f"**{_fmt_fecha(_fch)}** · {_r_nm} / {_s_nm}{_it_str} · **$ {_mn:,.0f}** · {_cj_nm}")
                    if _cb.button("✏️", key=f"oe_edit_{_oe_id}"):
                        st.session_state[f"oe_editing_{_oe_id}"] = True
                        st.rerun(scope="fragment")
                    if _cc.button("🗑️", key=f"oe_del_{_oe_id}"):
                        db.eliminar_egreso(_oe_id)
                        st.rerun(scope="fragment")
                if st.session_state.get(f"oe_editing_{_oe_id}"):
                    with st.container(border=True):
                        _e = _render_fields_jerarquia("egreso", f"oee{_oe_id}", _oe_subs_by_rubro, _oe_items_by_sub,
                                                      _oe_rubro_opts, _oe_caja_opts, defaults={
                                                          "fecha": _safe_date(_fch) or date.today(),
                                                          "rubro_nm": _r_nm, "sub_nm": _s_nm, "item_nm": _it_nm,
                                                          "monto_str": str(_mn), "caja_nm": _cj_nm,
                                                          "desc": _oe.get("descripcion") or "",
                                                          "tipo": _oe.get("tipo", "gasto"),
                                                      }, show_tipo=True)
                        _ec1, _ec2 = st.columns(2)
                        if _ec1.button("Guardar", type="primary", key=f"oe_save_{_oe_id}"):
                            if not _e["rubro"] or not _e["item_id"] or _e["monto"] <= 0:
                                st.error("Completá rubro, ítem y monto.")
                            else:
                                db.actualizar_egreso(_oe_id, _e["fecha"],
                                    _oe_rubro_opts.get(_e["rubro"]),
                                    _e["sub_opts"].get(_e["subrubro"]),
                                    _e["item_id"],
                                    _oe_caja_opts.get(_e["caja"]),
                                    _e["monto"], _e["desc"], _e["tipo"])
                                st.session_state.pop(f"oe_editing_{_oe_id}", None)
                                st.rerun(scope="fragment")
                        if _ec2.button("Cancelar", key=f"oe_cancel_{_oe_id}"):
                            st.session_state.pop(f"oe_editing_{_oe_id}", None)
                            st.rerun(scope="fragment")
        _oe_editar()

    with _oe_tab3:
        @st.fragment
        def _oe_todos():
            _lista = db.cargar_egresos()
            if not _lista:
                st.info("No hay egresos cargados todavía.")
                return
            with st.form("oe_all_filt", border=False):
                _dc1, _dc2 = st.columns(2)
                _oe_v_desde = _dc1.date_input("Desde", value=date(date.today().year, date.today().month, 1), format="DD/MM/YYYY", key="oe_v_desde")
                _oe_v_hasta = _dc2.date_input("Hasta", value=date.today(), format="DD/MM/YYYY", key="oe_v_hasta")
                st.form_submit_button("🔄 Actualizar", type="primary")
            _lista = [o for o in _lista if _oe_v_desde <= _safe_date(o.get("fecha")) <= _oe_v_hasta]
            if not _lista:
                st.caption("Sin registros en el rango.")
                return
            _by_rub: dict = {}
            for _oe in _lista:
                _r = (_oe.get("rubros_egresos") or {}).get("nombre") or "—"
                _s = (_oe.get("subrubros_egresos") or {}).get("nombre") or "—"
                _it = (_oe.get("items_egresos") or {}).get("nombre") or "—"
                _by_rub.setdefault(_r, {}).setdefault(_s, {}).setdefault(_it, []).append(_oe)
            _total = sum(float(x.get("monto") or 0) for x in _lista)
            st.metric("Total", fmt(_total))
            for _r_nm, _subs in sorted(_by_rub.items()):
                _r_tot = sum(float(x.get("monto") or 0) for s in _subs.values() for items in s.values() for x in items)
                with st.expander(f"{_r_nm} — $ {_r_tot:,.0f}"):
                    for _s_nm, _s_items in sorted(_subs.items()):
                        _s_tot = sum(float(x.get("monto") or 0) for items in _s_items.values() for x in items)
                        with st.expander(f"{_s_nm} — $ {_s_tot:,.0f}"):
                            for _it_nm, _it_items in sorted(_s_items.items()):
                                _it_tot = sum(float(x.get("monto") or 0) for x in _it_items)
                                with st.expander(f"{_it_nm} — $ {_it_tot:,.0f}"):
                                    _rows = [{"Fecha": _fmt_fecha(_oe.get("fecha")),
                                              "Monto": float(_oe.get("monto") or 0),
                                              "Caja": _oe_caja_map.get(_oe.get("caja_id"), "—"),
                                              "Descripción": _oe.get("descripcion") or ""}
                                             for _oe in sorted(_it_items, key=lambda x: str(x.get("fecha") or ""), reverse=True)]
                                    st.dataframe(pd.DataFrame(_rows), hide_index=True, use_container_width=True,
                                                 column_config={"Monto": st.column_config.NumberColumn("Monto ($)", format="$ %,.0f")})
        _oe_todos()


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFERENCIAS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_transferencias:
    st.subheader("Transferencias entre cajas")

    _cajas_t = db.cargar_cajas()
    _cmap_t  = {c["nombre"]: c["id"] for c in _cajas_t}

    with st.expander("➕ Nueva transferencia", expanded=False):
        with st.form("form_nueva_trf"):
            ct1, ct2, ct3 = st.columns(3)
            _ft = ct1.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
            _ot = ct2.selectbox("Origen", list(_cmap_t.keys()), key="nt_orig")
            _dt = ct3.selectbox("Destino", list(_cmap_t.keys()), key="nt_dest")
            _mt = st.number_input("Monto", min_value=0.0, step=100.0, format="%.2f")
            _ct = st.text_input("Concepto (opcional)")
            _btn_nt = st.form_submit_button("Guardar", type="primary")

            if _btn_nt:
                if _mt <= 0:
                    st.error("El monto debe ser mayor a 0.")
                elif _ot == _dt:
                    st.error("Origen y destino no pueden ser iguales.")
                else:
                    db.guardar_transferencia(_ft, _cmap_t[_ot], _cmap_t[_dt], _mt, _ct)
                    st.success("✅ Transferencia guardada.")
                    st.rerun()

    # Listado
    _d1t, _d2t = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde_t = c1.date_input("Desde", value=_d1t, format="DD/MM/YYYY", key="t_desde")
    _hasta_t = c2.date_input("Hasta", value=_d2t, format="DD/MM/YYYY", key="t_hasta")

    _lista_t = db.cargar_transferencias(_desde_t, _hasta_t)
    if _lista_t:
        for _row in _lista_t:
            _orig_n = ((_row.get("origen") or {}).get("nombre") or "—")
            _dest_n = ((_row.get("destino") or {}).get("nombre") or "—")
            with st.expander(f"{_row['fecha']}  |  {_orig_n} → {_dest_n}  |  {fmt(_row['monto'])}"):
                st.write(f"**Concepto:** {_row.get('concepto') or '—'}")

                with st.form(f"edit_trf_{_row['id']}"):
                    et1, et2, et3 = st.columns(3)
                    _eft = et1.date_input("Fecha", value=date.fromisoformat(_row["fecha"]), format="DD/MM/YYYY")
                    _cnames = list(_cmap_t.keys())
                    _eot = et2.selectbox("Origen",  _cnames, index=_cnames.index(_orig_n) if _orig_n in _cnames else 0)
                    _edt = et3.selectbox("Destino", _cnames, index=_cnames.index(_dest_n) if _dest_n in _cnames else 0)
                    _emt = st.number_input("Monto", value=float(_row["monto"]), step=100.0, format="%.2f")
                    _ect = st.text_input("Concepto", value=_row.get("concepto") or "")

                    bt1, bt2 = st.columns(2)
                    _btn_tu = bt1.form_submit_button("💾 Guardar")
                    _btn_td = bt2.form_submit_button("🗑️ Eliminar", type="secondary")

                    if _btn_tu:
                        db.actualizar_transferencia(_row["id"], _eft, _cmap_t[_eot], _cmap_t[_edt], _emt, _ect)
                        st.success("✅ Actualizado.")
                        st.rerun()
                    if _btn_td:
                        db.eliminar_transferencia(_row["id"])
                        st.rerun()
    else:
        st.info("Sin transferencias en el período.")


# ═══════════════════════════════════════════════════════════════════════════════
# AJUSTES
# ═══════════════════════════════════════════════════════════════════════════════

with tab_ajustes:
    st.subheader("Ajustes y saldo inicial")

    _cajas_aj = db.cargar_cajas()
    _cmap_aj  = {c["nombre"]: c["id"] for c in _cajas_aj}

    with st.expander("💵 Saldo inicial por caja", expanded=True):
        with st.form("form_saldo_ini"):
            _caj_ini = st.selectbox("Caja", list(_cmap_aj.keys()), key="aj_caja_ini")
            _faj_ini = st.date_input("Fecha de corte", value=date.today(), format="DD/MM/YYYY")
            _maj_ini = st.number_input("Saldo inicial", step=100.0, format="%.2f")
            _naj_ini = st.text_input("Nota (opcional)")
            _btn_ini = st.form_submit_button("Guardar saldo inicial", type="primary")
            if _btn_ini:
                db.guardar_ajuste(_cmap_aj[_caj_ini], _faj_ini, _maj_ini, _naj_ini, tipo="inicial")
                st.success("✅ Saldo inicial guardado.")
                st.rerun()

    with st.expander("🔧 Nuevo ajuste libre", expanded=False):
        with st.form("form_ajuste_libre"):
            _caj_aj = st.selectbox("Caja", list(_cmap_aj.keys()), key="aj_caja_lib")
            _faj    = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
            _maj    = st.number_input("Monto (negativo para corrección a la baja)", step=100.0, format="%.2f")
            _naj    = st.text_input("Nota")
            _btn_aj = st.form_submit_button("Guardar ajuste", type="primary")
            if _btn_aj:
                db.guardar_ajuste(_cmap_aj[_caj_aj], _faj, _maj, _naj, tipo="ajuste")
                st.success("✅ Ajuste guardado.")
                st.rerun()

    # Listado de ajustes
    _ajustes = db.cargar_ajustes()
    if _ajustes:
        _df_aj = []
        for _a in _ajustes:
            _df_aj.append({
                "Fecha": _a["fecha"],
                "Caja": ((_a.get("cajas") or {}).get("nombre") or "—"),
                "Tipo": _a.get("tipo", ""),
                "Monto": fmt(_a["monto"]),
                "Nota": _a.get("nota") or "",
            })
        st.dataframe(pd.DataFrame(_df_aj), hide_index=True, use_container_width=True)

        st.divider()
        st.markdown("**Editar / eliminar ajuste**")
        _aj_opts = {f"{a['fecha']} | {(a.get('cajas') or {}).get('nombre', '—')} | {a.get('tipo')} | {fmt(a['monto'])}": a for a in _ajustes}
        _aj_sel_k = st.selectbox("Seleccioná un ajuste", list(_aj_opts.keys()), key="aj_sel")
        _aj_sel   = _aj_opts[_aj_sel_k]

        with st.form("form_edit_ajuste"):
            ea1, ea2 = st.columns(2)
            _eaf = ea1.date_input("Fecha", value=date.fromisoformat(_aj_sel["fecha"]), format="DD/MM/YYYY")
            _eam = ea2.number_input("Monto", value=float(_aj_sel["monto"]), step=100.0, format="%.2f")
            _eac_actual = ((_aj_sel.get("cajas") or {}).get("nombre") or list(_cmap_aj.keys())[0])
            _eac_sel    = st.selectbox("Caja", list(_cmap_aj.keys()), index=list(_cmap_aj.keys()).index(_eac_actual) if _eac_actual in _cmap_aj else 0)
            _ean = st.text_input("Nota", value=_aj_sel.get("nota") or "")
            ba1, ba2 = st.columns(2)
            _btn_aupd = ba1.form_submit_button("💾 Guardar")
            _btn_adel = ba2.form_submit_button("🗑️ Eliminar", type="secondary")
            if _btn_aupd:
                db.actualizar_ajuste(_aj_sel["id"], _cmap_aj[_eac_sel], _eaf, _eam, _ean)
                st.success("✅ Ajuste actualizado.")
                st.rerun()
            if _btn_adel:
                db.eliminar_ajuste(_aj_sel["id"])
                st.rerun()
    else:
        st.info("Sin ajustes registrados.")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

with tab_config:
    st.subheader("Configuración")

    _sub_cajas, _sub_ri, _sub_re = st.tabs(["🏦 Cajas", "💰 Rubros ingresos", "💸 Rubros egresos"])

    # ── Cajas ──────────────────────────────────────────────────────────────────
    with _sub_cajas:
        st.markdown("**Cajas activas**")
        _cajas_cfg = db.cargar_cajas()
        for _c in _cajas_cfg:
            _mon_icon = "🇦🇷" if _c.get("moneda", "ARS") == "ARS" else "🇺🇸"
            with st.expander(f"{'✅' if _c['activa'] else '❌'} {_mon_icon} {_c['nombre']}"):
                with st.form(f"edit_caja_{_c['id']}"):
                    _cn = st.text_input("Nombre", value=_c["nombre"])
                    cc1, cc2 = st.columns(2)
                    _ca = cc1.checkbox("Activa", value=_c["activa"])
                    _cm_opts = ["ARS", "USD"]
                    _cm = cc2.selectbox("Moneda", _cm_opts, index=_cm_opts.index(_c.get("moneda", "ARS")))
                    bc1, bc2 = st.columns(2)
                    if bc1.form_submit_button("💾 Guardar"):
                        db.actualizar_caja(_c["id"], _cn, _ca, _cm)
                        st.rerun()
                    if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                        db.eliminar_caja(_c["id"])
                        st.rerun()

        with st.form("form_nueva_caja"):
            _nc = st.text_input("Nueva caja")
            _nc_mon = st.selectbox("Moneda", ["ARS", "USD"])
            if st.form_submit_button("➕ Agregar", type="primary"):
                if _nc.strip():
                    db.guardar_caja(_nc, _nc_mon)
                    st.rerun()

    # ── Rubros ingresos ────────────────────────────────────────────────────────
    with _sub_ri:
        _rubros_cfg_i = db.cargar_rubros_ingresos()
        _rmap_cfg_i   = {r["nombre"]: r["id"] for r in _rubros_cfg_i}

        st.markdown("**Rubros**")
        for _r in _rubros_cfg_i:
            with st.expander(_r["nombre"]):
                with st.form(f"edit_ri_{_r['id']}"):
                    _rn = st.text_input("Nombre", value=_r["nombre"])
                    bc1, bc2 = st.columns(2)
                    if bc1.form_submit_button("💾 Guardar"):
                        db.actualizar_rubro_ingreso(_r["id"], _rn)
                        st.rerun()
                    if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                        db.eliminar_rubro_ingreso(_r["id"])
                        st.rerun()

                # Subrubros dentro del rubro
                st.markdown("*Subrubros*")
                _subs_i = db.cargar_subrubros_ingresos(_r["id"])
                for _s in _subs_i:
                    with st.expander(f"↳ {_s['nombre']}"):
                        with st.form(f"edit_si_{_s['id']}"):
                            _sn = st.text_input("Nombre", value=_s["nombre"])
                            bc1, bc2 = st.columns(2)
                            if bc1.form_submit_button("💾 Guardar"):
                                db.actualizar_subrubro_ingreso(_s["id"], _sn, _r["id"])
                                st.rerun()
                            if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                                db.eliminar_subrubro_ingreso(_s["id"])
                                st.rerun()

                        # Ítems dentro del subrubro
                        _items_i = db.cargar_items_ingresos(_s["id"])
                        for _it in _items_i:
                            with st.expander(f"  • {_it['nombre']} {'✅' if _it['activo'] else '❌'}"):
                                with st.form(f"edit_ii_{_it['id']}"):
                                    _itn = st.text_input("Nombre", value=_it["nombre"])
                                    _ita = st.checkbox("Activo", value=_it["activo"])
                                    bc1, bc2 = st.columns(2)
                                    if bc1.form_submit_button("💾 Guardar"):
                                        db.actualizar_item_ingreso(_it["id"], _itn, activo=_ita)
                                        st.rerun()
                                    if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                                        db.eliminar_item_ingreso(_it["id"])
                                        st.rerun()

                        with st.form(f"new_ii_{_s['id']}"):
                            _nitn = st.text_input("Nuevo ítem")
                            if st.form_submit_button("➕ Ítem"):
                                if _nitn.strip():
                                    db.guardar_item_ingreso(_nitn, _s["id"])
                                    st.rerun()

                with st.form(f"new_si_{_r['id']}"):
                    _nsn = st.text_input("Nuevo subrubro")
                    if st.form_submit_button("➕ Subrubro"):
                        if _nsn.strip():
                            db.guardar_subrubro_ingreso(_nsn, _r["id"])
                            st.rerun()

        with st.form("form_nuevo_ri"):
            _nrn = st.text_input("Nuevo rubro de ingreso")
            if st.form_submit_button("➕ Rubro", type="primary"):
                if _nrn.strip():
                    db.guardar_rubro_ingreso(_nrn)
                    st.rerun()

    # ── Rubros egresos ─────────────────────────────────────────────────────────
    with _sub_re:
        _rubros_cfg_e = db.cargar_rubros_egresos()

        st.markdown("**Rubros**")
        for _r in _rubros_cfg_e:
            with st.expander(_r["nombre"]):
                with st.form(f"edit_re_{_r['id']}"):
                    _rne = st.text_input("Nombre", value=_r["nombre"])
                    bc1, bc2 = st.columns(2)
                    if bc1.form_submit_button("💾 Guardar"):
                        db.actualizar_rubro_egreso(_r["id"], _rne)
                        st.rerun()
                    if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                        db.eliminar_rubro_egreso(_r["id"])
                        st.rerun()

                st.markdown("*Subrubros*")
                _subs_e = db.cargar_subrubros_egresos(_r["id"])
                for _s in _subs_e:
                    with st.expander(f"↳ {_s['nombre']}"):
                        with st.form(f"edit_se_{_s['id']}"):
                            _sne = st.text_input("Nombre", value=_s["nombre"])
                            bc1, bc2 = st.columns(2)
                            if bc1.form_submit_button("💾 Guardar"):
                                db.actualizar_subrubro_egreso(_s["id"], _sne, _r["id"])
                                st.rerun()
                            if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                                db.eliminar_subrubro_egreso(_s["id"])
                                st.rerun()

                        _items_e = db.cargar_items_egresos(_s["id"])
                        for _it in _items_e:
                            with st.expander(f"  • {_it['nombre']} {'✅' if _it['activo'] else '❌'}"):
                                with st.form(f"edit_ie_{_it['id']}"):
                                    _itne = st.text_input("Nombre", value=_it["nombre"])
                                    _itae = st.checkbox("Activo", value=_it["activo"])
                                    bc1, bc2 = st.columns(2)
                                    if bc1.form_submit_button("💾 Guardar"):
                                        db.actualizar_item_egreso(_it["id"], _itne, activo=_itae)
                                        st.rerun()
                                    if bc2.form_submit_button("🗑️ Eliminar", type="secondary"):
                                        db.eliminar_item_egreso(_it["id"])
                                        st.rerun()

                        with st.form(f"new_ie_{_s['id']}"):
                            _nitne = st.text_input("Nuevo ítem")
                            if st.form_submit_button("➕ Ítem"):
                                if _nitne.strip():
                                    db.guardar_item_egreso(_nitne, _s["id"])
                                    st.rerun()

                with st.form(f"new_se_{_r['id']}"):
                    _nsne = st.text_input("Nuevo subrubro")
                    if st.form_submit_button("➕ Subrubro"):
                        if _nsne.strip():
                            db.guardar_subrubro_egreso(_nsne, _r["id"])
                            st.rerun()

        with st.form("form_nuevo_re"):
            _nrne = st.text_input("Nuevo rubro de egreso")
            if st.form_submit_button("➕ Rubro", type="primary"):
                if _nrne.strip():
                    db.guardar_rubro_egreso(_nrne)
                    st.rerun()
