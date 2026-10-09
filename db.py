import streamlit as st
from supabase import create_client, Client

# ── Cliente ───────────────────────────────────────────────────────────────────

@st.cache_resource
def get_client() -> Client:
    cfg = st.secrets["supabase"]
    return create_client(cfg["url"], cfg["key"])


def _exec(query):
    return query.execute()


# ── CAJAS ─────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def cargar_cajas():
    return _exec(get_client().table("cajas").select("*").order("nombre")).data or []


def guardar_caja(nombre, moneda="ARS"):
    get_client().table("cajas").insert({"nombre": nombre.strip(), "activa": True, "moneda": moneda}).execute()
    cargar_cajas.clear()


def actualizar_caja(id, nombre, activa, moneda="ARS"):
    get_client().table("cajas").update({"nombre": nombre.strip(), "activa": activa, "moneda": moneda}).eq("id", id).execute()
    cargar_cajas.clear()


def eliminar_caja(id):
    get_client().table("cajas").delete().eq("id", id).execute()
    cargar_cajas.clear()


# ── RUBROS INGRESOS ───────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def cargar_rubros_ingresos():
    return _exec(get_client().table("rubros_ingresos").select("*").order("nombre")).data or []


def guardar_rubro_ingreso(nombre):
    get_client().table("rubros_ingresos").insert({"nombre": nombre.strip()}).execute()
    cargar_rubros_ingresos.clear()


def actualizar_rubro_ingreso(id, nombre):
    get_client().table("rubros_ingresos").update({"nombre": nombre.strip()}).eq("id", id).execute()
    cargar_rubros_ingresos.clear()


def eliminar_rubro_ingreso(id):
    get_client().table("rubros_ingresos").delete().eq("id", id).execute()
    cargar_rubros_ingresos.clear()


@st.cache_data(ttl=120)
def cargar_subrubros_ingresos(rubro_id=None):
    q = get_client().table("subrubros_ingresos").select("*").order("nombre")
    if rubro_id is not None:
        q = q.eq("rubro_id", rubro_id)
    return q.execute().data or []


def guardar_subrubro_ingreso(nombre, rubro_id):
    get_client().table("subrubros_ingresos").insert({"nombre": nombre.strip(), "rubro_id": rubro_id}).execute()
    cargar_subrubros_ingresos.clear()


def actualizar_subrubro_ingreso(id, nombre, rubro_id):
    get_client().table("subrubros_ingresos").update({"nombre": nombre.strip(), "rubro_id": rubro_id}).eq("id", id).execute()
    cargar_subrubros_ingresos.clear()


def eliminar_subrubro_ingreso(id):
    get_client().table("subrubros_ingresos").delete().eq("id", id).execute()
    cargar_subrubros_ingresos.clear()


@st.cache_data(ttl=120)
def cargar_items_ingresos(subrubro_id=None):
    q = get_client().table("items_ingresos").select("*").order("nombre")
    if subrubro_id is not None:
        q = q.eq("subrubro_id", subrubro_id)
    return q.execute().data or []


def guardar_item_ingreso(nombre, subrubro_id):
    get_client().table("items_ingresos").insert({"nombre": nombre.strip(), "subrubro_id": subrubro_id, "activo": True}).execute()
    cargar_items_ingresos.clear()


def actualizar_item_ingreso(id, nombre, subrubro_id=None, activo=None):
    data = {"nombre": nombre.strip()}
    if subrubro_id is not None:
        data["subrubro_id"] = subrubro_id
    if activo is not None:
        data["activo"] = activo
    get_client().table("items_ingresos").update(data).eq("id", id).execute()
    cargar_items_ingresos.clear()


def eliminar_item_ingreso(id):
    get_client().table("items_ingresos").delete().eq("id", id).execute()
    cargar_items_ingresos.clear()


def item_ingreso_tiene_transacciones(item_id) -> bool:
    return bool(get_client().table("ingresos").select("id").eq("item_id", item_id).limit(1).execute().data)


# ── RUBROS EGRESOS ────────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def cargar_rubros_egresos():
    return _exec(get_client().table("rubros_egresos").select("*").order("nombre")).data or []


def guardar_rubro_egreso(nombre):
    get_client().table("rubros_egresos").insert({"nombre": nombre.strip()}).execute()
    cargar_rubros_egresos.clear()


def actualizar_rubro_egreso(id, nombre):
    get_client().table("rubros_egresos").update({"nombre": nombre.strip()}).eq("id", id).execute()
    cargar_rubros_egresos.clear()


def eliminar_rubro_egreso(id):
    get_client().table("rubros_egresos").delete().eq("id", id).execute()
    cargar_rubros_egresos.clear()


@st.cache_data(ttl=120)
def cargar_subrubros_egresos(rubro_id=None):
    q = get_client().table("subrubros_egresos").select("*").order("nombre")
    if rubro_id is not None:
        q = q.eq("rubro_id", rubro_id)
    return q.execute().data or []


def guardar_subrubro_egreso(nombre, rubro_id):
    get_client().table("subrubros_egresos").insert({"nombre": nombre.strip(), "rubro_id": rubro_id}).execute()
    cargar_subrubros_egresos.clear()


def actualizar_subrubro_egreso(id, nombre, rubro_id):
    get_client().table("subrubros_egresos").update({"nombre": nombre.strip(), "rubro_id": rubro_id}).eq("id", id).execute()
    cargar_subrubros_egresos.clear()


def eliminar_subrubro_egreso(id):
    get_client().table("subrubros_egresos").delete().eq("id", id).execute()
    cargar_subrubros_egresos.clear()


@st.cache_data(ttl=120)
def cargar_items_egresos(subrubro_id=None):
    q = get_client().table("items_egresos").select("*").order("nombre")
    if subrubro_id is not None:
        q = q.eq("subrubro_id", subrubro_id)
    return q.execute().data or []


def guardar_item_egreso(nombre, subrubro_id):
    get_client().table("items_egresos").insert({"nombre": nombre.strip(), "subrubro_id": subrubro_id, "activo": True}).execute()
    cargar_items_egresos.clear()


def actualizar_item_egreso(id, nombre, subrubro_id=None, activo=None):
    data = {"nombre": nombre.strip()}
    if subrubro_id is not None:
        data["subrubro_id"] = subrubro_id
    if activo is not None:
        data["activo"] = activo
    get_client().table("items_egresos").update(data).eq("id", id).execute()
    cargar_items_egresos.clear()


def eliminar_item_egreso(id):
    get_client().table("items_egresos").delete().eq("id", id).execute()
    cargar_items_egresos.clear()


def item_egreso_tiene_transacciones(item_id) -> bool:
    return bool(get_client().table("egresos").select("id").eq("item_id", item_id).limit(1).execute().data)


# ── INGRESOS ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def cargar_ingresos(desde=None, hasta=None):
    q = get_client().table("ingresos").select(
        "*, rubros_ingresos(nombre), subrubros_ingresos(nombre), items_ingresos(nombre), cajas(nombre)"
    ).order("fecha", desc=True)
    if desde:
        q = q.gte("fecha", str(desde))
    if hasta:
        q = q.lte("fecha", str(hasta))
    return q.execute().data or []


def guardar_ingreso(fecha, rubro_id, subrubro_id, item_id, caja_id, monto, descripcion=""):
    get_client().table("ingresos").insert({
        "fecha":       str(fecha),
        "rubro_id":    rubro_id or None,
        "subrubro_id": subrubro_id or None,
        "item_id":     item_id or None,
        "caja_id":     caja_id or None,
        "monto":       float(monto),
        "descripcion": descripcion or None,
    }).execute()
    cargar_ingresos.clear()


def actualizar_ingreso(id, fecha, rubro_id, subrubro_id, item_id, caja_id, monto, descripcion=""):
    get_client().table("ingresos").update({
        "fecha":       str(fecha),
        "rubro_id":    rubro_id or None,
        "subrubro_id": subrubro_id or None,
        "item_id":     item_id or None,
        "caja_id":     caja_id or None,
        "monto":       float(monto),
        "descripcion": descripcion or None,
    }).eq("id", id).execute()
    cargar_ingresos.clear()


def eliminar_ingreso(id):
    get_client().table("ingresos").delete().eq("id", id).execute()
    cargar_ingresos.clear()


# ── EGRESOS ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def cargar_egresos(desde=None, hasta=None):
    q = get_client().table("egresos").select(
        "*, rubros_egresos(nombre), subrubros_egresos(nombre), items_egresos(nombre), cajas(nombre)"
    ).order("fecha", desc=True)
    if desde:
        q = q.gte("fecha", str(desde))
    if hasta:
        q = q.lte("fecha", str(hasta))
    return q.execute().data or []


def guardar_egreso(fecha, rubro_id, subrubro_id, item_id, caja_id, monto, descripcion="", tipo="gasto"):
    get_client().table("egresos").insert({
        "fecha":       str(fecha),
        "rubro_id":    rubro_id or None,
        "subrubro_id": subrubro_id or None,
        "item_id":     item_id or None,
        "caja_id":     caja_id or None,
        "monto":       float(monto),
        "descripcion": descripcion or None,
        "tipo":        tipo,
    }).execute()
    cargar_egresos.clear()


def actualizar_egreso(id, fecha, rubro_id, subrubro_id, item_id, caja_id, monto, descripcion="", tipo="gasto"):
    get_client().table("egresos").update({
        "fecha":       str(fecha),
        "rubro_id":    rubro_id or None,
        "subrubro_id": subrubro_id or None,
        "item_id":     item_id or None,
        "caja_id":     caja_id or None,
        "monto":       float(monto),
        "descripcion": descripcion or None,
        "tipo":        tipo,
    }).eq("id", id).execute()
    cargar_egresos.clear()


def eliminar_egreso(id):
    get_client().table("egresos").delete().eq("id", id).execute()
    cargar_egresos.clear()


# ── TRANSFERENCIAS ────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def cargar_transferencias(desde=None, hasta=None):
    q = get_client().table("transferencias").select(
        "*, origen:origen_id(nombre), destino:destino_id(nombre)"
    ).order("fecha", desc=True)
    if desde:
        q = q.gte("fecha", str(desde))
    if hasta:
        q = q.lte("fecha", str(hasta))
    return q.execute().data or []


def guardar_transferencia(fecha, origen_id, destino_id, monto, concepto=""):
    get_client().table("transferencias").insert({
        "fecha":      str(fecha),
        "origen_id":  origen_id,
        "destino_id": destino_id,
        "monto":      float(monto),
        "concepto":   concepto or None,
    }).execute()
    cargar_transferencias.clear()


def actualizar_transferencia(id, fecha, origen_id, destino_id, monto, concepto=""):
    get_client().table("transferencias").update({
        "fecha":      str(fecha),
        "origen_id":  origen_id,
        "destino_id": destino_id,
        "monto":      float(monto),
        "concepto":   concepto or None,
    }).eq("id", id).execute()
    cargar_transferencias.clear()


def eliminar_transferencia(id):
    get_client().table("transferencias").delete().eq("id", id).execute()
    cargar_transferencias.clear()


# ── AJUSTES DE CAJA ───────────────────────────────────────────────────────────

@st.cache_data(ttl=120)
def cargar_ajustes():
    return get_client().table("ajustes").select(
        "*, cajas(nombre)"
    ).order("fecha", desc=True).execute().data or []


def guardar_ajuste(caja_id, fecha, monto, nota="", tipo="ajuste"):
    client = get_client()
    if tipo == "inicial":
        existing = client.table("ajustes").select("id").eq("caja_id", caja_id).eq("tipo", "inicial").execute()
        if existing.data:
            client.table("ajustes").update({
                "fecha": str(fecha), "monto": float(monto), "nota": nota or None,
            }).eq("id", existing.data[0]["id"]).execute()
            cargar_ajustes.clear()
            return
    client.table("ajustes").insert({
        "caja_id": caja_id,
        "fecha":   str(fecha),
        "monto":   float(monto),
        "nota":    nota or None,
        "tipo":    tipo,
    }).execute()
    cargar_ajustes.clear()


def actualizar_ajuste(id, caja_id, fecha, monto, nota=""):
    get_client().table("ajustes").update({
        "caja_id": caja_id,
        "fecha":   str(fecha),
        "monto":   float(monto),
        "nota":    nota or None,
    }).eq("id", id).execute()
    cargar_ajustes.clear()


def eliminar_ajuste(id):
    get_client().table("ajustes").delete().eq("id", id).execute()
    cargar_ajustes.clear()
