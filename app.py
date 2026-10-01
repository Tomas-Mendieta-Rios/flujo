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

with tab_percibido:
    st.subheader("Resumen del período")

    _d1, _d2 = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde = c1.date_input("Desde", value=_d1, format="DD/MM/YYYY", key="p_desde")
    _hasta = c2.date_input("Hasta", value=_d2, format="DD/MM/YYYY", key="p_hasta")

    _ing_all  = db.cargar_ingresos(_desde, _hasta)
    _egr_all  = db.cargar_egresos(_desde, _hasta)
    _trf_all  = db.cargar_transferencias()
    _aj_all   = db.cargar_ajustes()
    _cajas_all = db.cargar_cajas()
    _cajas_mon = {c["id"]: c.get("moneda", "ARS") for c in _cajas_all}

    def _render_percibido(moneda):
        _cajas_m = [c for c in _cajas_all if c.get("moneda", "ARS") == moneda]
        _ids_m   = {c["id"] for c in _cajas_m}

        _ing  = [r for r in _ing_all  if r.get("caja_id") in _ids_m]
        _egr  = [r for r in _egr_all  if r.get("caja_id") in _ids_m]

        # Saldos actuales
        _ing_todo = db.cargar_ingresos()
        _egr_todo = db.cargar_egresos()
        st.markdown("**Saldo actual por caja**")
        _saldo_cols = st.columns(max(len(_cajas_m), 1))
        for i, c in enumerate(_cajas_m):
            _s = _calcular_saldo_caja(c["id"], _aj_all, _ing_todo, _egr_todo, _trf_all)
            _saldo_cols[i].metric(c["nombre"], fmt(_s, moneda))

        st.divider()

        _ing_rows = [{"Rubro": _nombre_rubro(r, "ingreso"), "Monto": float(r.get("monto") or 0)} for r in _ing]
        _egr_rows = [{"Rubro": _nombre_rubro(r, "egreso"),  "Monto": float(r.get("monto") or 0)} for r in _egr]

        _total_ing = sum(r["Monto"] for r in _ing_rows)
        _total_egr = sum(r["Monto"] for r in _egr_rows)
        _neto      = _total_ing - _total_egr

        col_i, col_e, col_n = st.columns(3)
        col_i.metric("Ingresos del período", fmt(_total_ing, moneda))
        col_e.metric("Egresos del período",  fmt(_total_egr, moneda))
        col_n.metric("Neto",                 fmt(_neto, moneda))

        st.divider()
        ci, ce = st.columns(2)
        with ci:
            st.markdown("**Ingresos por rubro**")
            if _ing_rows:
                _df_i = (pd.DataFrame(_ing_rows).groupby("Rubro", as_index=False)["Monto"].sum()
                           .sort_values("Monto", ascending=False))
                _df_i["Monto"] = _df_i["Monto"].apply(lambda v: fmt(v, moneda))
                st.dataframe(_df_i, hide_index=True, use_container_width=True)
            else:
                st.info("Sin ingresos en el período.")
        with ce:
            st.markdown("**Egresos por rubro**")
            if _egr_rows:
                _df_e = (pd.DataFrame(_egr_rows).groupby("Rubro", as_index=False)["Monto"].sum()
                           .sort_values("Monto", ascending=False))
                _df_e["Monto"] = _df_e["Monto"].apply(lambda v: fmt(v, moneda))
                st.dataframe(_df_e, hide_index=True, use_container_width=True)
            else:
                st.info("Sin egresos en el período.")

    _ptab_ars, _ptab_usd = st.tabs(["🇦🇷 Pesos (ARS)", "🇺🇸 Dólares (USD)"])
    with _ptab_ars:
        _render_percibido("ARS")
    with _ptab_usd:
        _render_percibido("USD")


# ═══════════════════════════════════════════════════════════════════════════════
# MOVIMIENTOS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_movimientos:
    st.subheader("Movimientos")

    _d1m, _d2m = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde_m = c1.date_input("Desde", value=_d1m, format="DD/MM/YYYY", key="m_desde")
    _hasta_m = c2.date_input("Hasta", value=_d2m, format="DD/MM/YYYY", key="m_hasta")

    _ing_m_all  = db.cargar_ingresos(_desde_m, _hasta_m)
    _egr_m_all  = db.cargar_egresos(_desde_m, _hasta_m)
    _trf_m_all  = db.cargar_transferencias(_desde_m, _hasta_m)
    _cajas_m_all = db.cargar_cajas()
    _cajas_m_mon = {c["id"]: c.get("moneda", "ARS") for c in _cajas_m_all}

    def _render_movimientos(moneda):
        _ids_mon = {c["id"] for c in _cajas_m_all if c.get("moneda", "ARS") == moneda}
        _rows_m = []
        for r in _ing_m_all:
            if r.get("caja_id") in _ids_mon:
                _rows_m.append({"Fecha": r["fecha"], "Tipo": "Ingreso",
                    "Rubro": _nombre_rubro(r, "ingreso"), "Subrubro": _nombre_subrubro(r, "ingreso"),
                    "Item": _nombre_item(r, "ingreso"), "Caja": _nombre_caja(r),
                    "Descripción": r.get("descripcion") or "", "Monto": float(r.get("monto") or 0)})
        for r in _egr_m_all:
            if r.get("caja_id") in _ids_mon:
                _rows_m.append({"Fecha": r["fecha"], "Tipo": "Egreso",
                    "Rubro": _nombre_rubro(r, "egreso"), "Subrubro": _nombre_subrubro(r, "egreso"),
                    "Item": _nombre_item(r, "egreso"), "Caja": _nombre_caja(r),
                    "Descripción": r.get("descripcion") or "", "Monto": -float(r.get("monto") or 0)})
        for r in _trf_m_all:
            if r.get("origen_id") in _ids_mon or r.get("destino_id") in _ids_mon:
                _orig = (r.get("origen") or {}).get("nombre") or "—"
                _dest = (r.get("destino") or {}).get("nombre") or "—"
                _rows_m.append({"Fecha": r["fecha"], "Tipo": "Transferencia",
                    "Rubro": f"{_orig} → {_dest}", "Subrubro": "", "Item": "",
                    "Caja": f"{_orig} → {_dest}", "Descripción": r.get("concepto") or "", "Monto": 0.0})
        if _rows_m:
            _df_m = pd.DataFrame(_rows_m).sort_values("Fecha", ascending=False)
            _df_m["Monto"] = _df_m["Monto"].apply(lambda v: fmt(v, moneda))
            st.dataframe(_df_m[["Fecha", "Tipo", "Rubro", "Subrubro", "Item", "Caja", "Descripción", "Monto"]],
                hide_index=True, use_container_width=True)
        else:
            st.info("Sin movimientos en el período.")

    _mtab_ars, _mtab_usd = st.tabs(["🇦🇷 Pesos (ARS)", "🇺🇸 Dólares (USD)"])
    with _mtab_ars:
        _render_movimientos("ARS")
    with _mtab_usd:
        _render_movimientos("USD")


# ═══════════════════════════════════════════════════════════════════════════════
# INGRESOS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_ingresos:
    st.subheader("Ingresos")

    with st.expander("➕ Nuevo ingreso", expanded=False):
        ci1, ci2 = st.columns(2)
        _fi = ci1.date_input("Fecha", value=date.today(), format="DD/MM/YYYY", key="ni_fecha")
        _mi = ci2.number_input("Monto", min_value=0.0, step=100.0, format="%.2f", key="ni_monto")

        _rubros_i = db.cargar_rubros_ingresos()
        _rmap_i   = {r["nombre"]: r["id"] for r in _rubros_i}
        _ri_sel   = st.selectbox("Rubro", ["— sin rubro —"] + list(_rmap_i.keys()), key="ni_rubro")
        _ri_id    = _rmap_i.get(_ri_sel)

        _sub_i_opts = db.cargar_subrubros_ingresos(_ri_id) if _ri_id else []
        _smap_i     = {s["nombre"]: s["id"] for s in _sub_i_opts}
        _si_sel     = st.selectbox("Subrubro", ["— sin subrubro —"] + list(_smap_i.keys()), key="ni_sub")
        _si_id      = _smap_i.get(_si_sel)

        _item_i_opts = db.cargar_items_ingresos(_si_id) if _si_id else []
        _imap_i      = {it["nombre"]: it["id"] for it in _item_i_opts}
        _ii_sel      = st.selectbox("Ítem", ["— sin ítem —"] + list(_imap_i.keys()), key="ni_item")
        _ii_id       = _imap_i.get(_ii_sel)

        _cajas_i = db.cargar_cajas()
        _cmap_i  = {c["nombre"]: c["id"] for c in _cajas_i}
        _ci_sel  = st.selectbox("Caja", ["— sin caja —"] + list(_cmap_i.keys()), key="ni_caja")
        _ci_id   = _cmap_i.get(_ci_sel)

        _desc_i = st.text_input("Descripción (opcional)", key="ni_desc")
        if st.button("💾 Guardar ingreso", type="primary", key="ni_save"):
            if _mi <= 0:
                st.error("El monto debe ser mayor a 0.")
            else:
                db.guardar_ingreso(_fi, _ri_id, _si_id, _ii_id, _ci_id, _mi, _desc_i)
                st.success("✅ Ingreso guardado.")
                st.rerun()

    # Listado
    _d1i, _d2i = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde_i = c1.date_input("Desde", value=_d1i, format="DD/MM/YYYY", key="i_desde")
    _hasta_i = c2.date_input("Hasta", value=_d2i, format="DD/MM/YYYY", key="i_hasta")

    _lista_i = db.cargar_ingresos(_desde_i, _hasta_i)
    if _lista_i:
        for _row in _lista_i:
            with st.expander(f"{_row['fecha']}  |  {_nombre_rubro(_row, 'ingreso')}  |  {fmt(_row['monto'])}"):
                ce1, ce2 = st.columns(2)
                ce1.write(f"**Subrubro:** {_nombre_subrubro(_row, 'ingreso')}")
                ce1.write(f"**Ítem:** {_nombre_item(_row, 'ingreso')}")
                ce2.write(f"**Caja:** {_nombre_caja(_row)}")
                ce2.write(f"**Descripción:** {_row.get('descripcion') or '—'}")

                _rid = _row["id"]
                ec1, ec2 = st.columns(2)
                _ef = ec1.date_input("Fecha", value=date.fromisoformat(_row["fecha"]), format="DD/MM/YYYY", key=f"ei_{_rid}_f")
                _em = ec2.number_input("Monto", value=float(_row["monto"]), step=100.0, format="%.2f", key=f"ei_{_rid}_m")

                _rubros_e = db.cargar_rubros_ingresos()
                _rmap_e   = {r["nombre"]: r["id"] for r in _rubros_e}
                _er_opts  = ["— sin rubro —"] + list(_rmap_e.keys())
                _er_actual = _nombre_rubro(_row, "ingreso") if _nombre_rubro(_row, "ingreso") != "—" else "— sin rubro —"
                _er_sel   = st.selectbox("Rubro", _er_opts, index=_er_opts.index(_er_actual) if _er_actual in _er_opts else 0, key=f"ei_{_rid}_r")
                _er_id    = _rmap_e.get(_er_sel)

                _sub_e_opts = db.cargar_subrubros_ingresos(_er_id) if _er_id else []
                _smap_e     = {s["nombre"]: s["id"] for s in _sub_e_opts}
                _es_opts    = ["— sin subrubro —"] + list(_smap_e.keys())
                _es_actual  = _nombre_subrubro(_row, "ingreso") if _nombre_subrubro(_row, "ingreso") != "—" else "— sin subrubro —"
                _es_sel     = st.selectbox("Subrubro", _es_opts, index=_es_opts.index(_es_actual) if _es_actual in _es_opts else 0, key=f"ei_{_rid}_s")
                _es_id      = _smap_e.get(_es_sel)

                _item_e_opts = db.cargar_items_ingresos(_es_id) if _es_id else []
                _imap_e      = {it["nombre"]: it["id"] for it in _item_e_opts}
                _ei_opts     = ["— sin ítem —"] + list(_imap_e.keys())
                _ei_actual   = _nombre_item(_row, "ingreso") if _nombre_item(_row, "ingreso") != "—" else "— sin ítem —"
                _ei_sel      = st.selectbox("Ítem", _ei_opts, index=_ei_opts.index(_ei_actual) if _ei_actual in _ei_opts else 0, key=f"ei_{_rid}_i")
                _ei_id       = _imap_e.get(_ei_sel)

                _cajas_e = db.cargar_cajas()
                _cmap_e  = {c["nombre"]: c["id"] for c in _cajas_e}
                _ec_opts = ["— sin caja —"] + list(_cmap_e.keys())
                _ec_actual = _nombre_caja(_row) if _nombre_caja(_row) != "—" else "— sin caja —"
                _ec_sel   = st.selectbox("Caja", _ec_opts, index=_ec_opts.index(_ec_actual) if _ec_actual in _ec_opts else 0, key=f"ei_{_rid}_c")
                _ec_id    = _cmap_e.get(_ec_sel)

                _ed = st.text_input("Descripción", value=_row.get("descripcion") or "", key=f"ei_{_rid}_d")

                bc1, bc2 = st.columns(2)
                if bc1.button("💾 Guardar", key=f"ei_{_rid}_upd"):
                    db.actualizar_ingreso(_row["id"], _ef, _er_id, _es_id, _ei_id, _ec_id, _em, _ed)
                    st.success("✅ Actualizado.")
                    st.rerun()
                if bc2.button("🗑️ Eliminar", key=f"ei_{_rid}_del"):
                    db.eliminar_ingreso(_row["id"])
                    st.rerun()
    else:
        st.info("Sin ingresos en el período.")


# ═══════════════════════════════════════════════════════════════════════════════
# EGRESOS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_egresos:
    st.subheader("Egresos")

    with st.expander("➕ Nuevo egreso", expanded=False):
        ce1, ce2 = st.columns(2)
        _fe = ce1.date_input("Fecha", value=date.today(), format="DD/MM/YYYY", key="ne_fecha")
        _me = ce2.number_input("Monto", min_value=0.0, step=100.0, format="%.2f", key="ne_monto")

        _rubros_eg = db.cargar_rubros_egresos()
        _rmap_eg   = {r["nombre"]: r["id"] for r in _rubros_eg}
        _re_sel    = st.selectbox("Rubro", ["— sin rubro —"] + list(_rmap_eg.keys()), key="ne_rubro")
        _re_id     = _rmap_eg.get(_re_sel)

        _sub_eg_opts = db.cargar_subrubros_egresos(_re_id) if _re_id else []
        _smap_eg     = {s["nombre"]: s["id"] for s in _sub_eg_opts}
        _se_sel      = st.selectbox("Subrubro", ["— sin subrubro —"] + list(_smap_eg.keys()), key="ne_sub")
        _se_id       = _smap_eg.get(_se_sel)

        _item_eg_opts = db.cargar_items_egresos(_se_id) if _se_id else []
        _imap_eg      = {it["nombre"]: it["id"] for it in _item_eg_opts}
        _ie_sel       = st.selectbox("Ítem", ["— sin ítem —"] + list(_imap_eg.keys()), key="ne_item")
        _ie_id        = _imap_eg.get(_ie_sel)

        _cajas_eg = db.cargar_cajas()
        _cmap_eg  = {c["nombre"]: c["id"] for c in _cajas_eg}
        _ce_sel   = st.selectbox("Caja", ["— sin caja —"] + list(_cmap_eg.keys()), key="ne_caja")
        _ce_id    = _cmap_eg.get(_ce_sel)

        _desc_e = st.text_input("Descripción (opcional)", key="ne_desc")
        if st.button("💾 Guardar egreso", type="primary", key="ne_save"):
            if _me <= 0:
                st.error("El monto debe ser mayor a 0.")
            else:
                db.guardar_egreso(_fe, _re_id, _se_id, _ie_id, _ce_id, _me, _desc_e)
                st.success("✅ Egreso guardado.")
                st.rerun()

    # Listado
    _d1e, _d2e = _mes_actual()
    c1, c2, _ = st.columns([1, 1, 3])
    _desde_e = c1.date_input("Desde", value=_d1e, format="DD/MM/YYYY", key="e_desde")
    _hasta_e = c2.date_input("Hasta", value=_d2e, format="DD/MM/YYYY", key="e_hasta")

    _lista_e = db.cargar_egresos(_desde_e, _hasta_e)
    if _lista_e:
        for _row in _lista_e:
            with st.expander(f"{_row['fecha']}  |  {_nombre_rubro(_row, 'egreso')}  |  {fmt(_row['monto'])}"):
                ce1, ce2 = st.columns(2)
                ce1.write(f"**Subrubro:** {_nombre_subrubro(_row, 'egreso')}")
                ce1.write(f"**Ítem:** {_nombre_item(_row, 'egreso')}")
                ce2.write(f"**Caja:** {_nombre_caja(_row)}")
                ce2.write(f"**Descripción:** {_row.get('descripcion') or '—'}")

                _eid = _row["id"]
                ec1, ec2 = st.columns(2)
                _ef2 = ec1.date_input("Fecha", value=date.fromisoformat(_row["fecha"]), format="DD/MM/YYYY", key=f"ee_{_eid}_f")
                _em2 = ec2.number_input("Monto", value=float(_row["monto"]), step=100.0, format="%.2f", key=f"ee_{_eid}_m")

                _rubros_ee = db.cargar_rubros_egresos()
                _rmap_ee   = {r["nombre"]: r["id"] for r in _rubros_ee}
                _er2_opts  = ["— sin rubro —"] + list(_rmap_ee.keys())
                _er2_actual = _nombre_rubro(_row, "egreso") if _nombre_rubro(_row, "egreso") != "—" else "— sin rubro —"
                _er2_sel   = st.selectbox("Rubro", _er2_opts, index=_er2_opts.index(_er2_actual) if _er2_actual in _er2_opts else 0, key=f"ee_{_eid}_r")
                _er2_id    = _rmap_ee.get(_er2_sel)

                _sub_ee_opts = db.cargar_subrubros_egresos(_er2_id) if _er2_id else []
                _smap_ee     = {s["nombre"]: s["id"] for s in _sub_ee_opts}
                _es2_opts    = ["— sin subrubro —"] + list(_smap_ee.keys())
                _es2_actual  = _nombre_subrubro(_row, "egreso") if _nombre_subrubro(_row, "egreso") != "—" else "— sin subrubro —"
                _es2_sel     = st.selectbox("Subrubro", _es2_opts, index=_es2_opts.index(_es2_actual) if _es2_actual in _es2_opts else 0, key=f"ee_{_eid}_s")
                _es2_id      = _smap_ee.get(_es2_sel)

                _item_ee_opts = db.cargar_items_egresos(_es2_id) if _es2_id else []
                _imap_ee      = {it["nombre"]: it["id"] for it in _item_ee_opts}
                _ei2_opts     = ["— sin ítem —"] + list(_imap_ee.keys())
                _ei2_actual   = _nombre_item(_row, "egreso") if _nombre_item(_row, "egreso") != "—" else "— sin ítem —"
                _ei2_sel      = st.selectbox("Ítem", _ei2_opts, index=_ei2_opts.index(_ei2_actual) if _ei2_actual in _ei2_opts else 0, key=f"ee_{_eid}_i")
                _ei2_id       = _imap_ee.get(_ei2_sel)

                _cajas_ee = db.cargar_cajas()
                _cmap_ee  = {c["nombre"]: c["id"] for c in _cajas_ee}
                _ec2_opts = ["— sin caja —"] + list(_cmap_ee.keys())
                _ec2_actual = _nombre_caja(_row) if _nombre_caja(_row) != "—" else "— sin caja —"
                _ec2_sel   = st.selectbox("Caja", _ec2_opts, index=_ec2_opts.index(_ec2_actual) if _ec2_actual in _ec2_opts else 0, key=f"ee_{_eid}_c")
                _ec2_id    = _cmap_ee.get(_ec2_sel)

                _ed2 = st.text_input("Descripción", value=_row.get("descripcion") or "", key=f"ee_{_eid}_d")

                bc1, bc2 = st.columns(2)
                if bc1.button("💾 Guardar", key=f"ee_{_eid}_upd"):
                    db.actualizar_egreso(_row["id"], _ef2, _er2_id, _es2_id, _ei2_id, _ec2_id, _em2, _ed2)
                    st.success("✅ Actualizado.")
                    st.rerun()
                if bc2.button("🗑️ Eliminar", key=f"ee_{_eid}_del"):
                    db.eliminar_egreso(_row["id"])
                    st.rerun()
    else:
        st.info("Sin egresos en el período.")


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
