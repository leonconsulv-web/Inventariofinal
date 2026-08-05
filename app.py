import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import io
import base64
import requests

try:
    import zoneinfo
except ImportError:
    zoneinfo = None

def obtener_hora_local():
    """Obtiene la fecha y hora actual en la zona horaria de México (America/Mexico_City / UTC-6)."""
    if zoneinfo:
        try:
            return datetime.now(zoneinfo.ZoneInfo("America/Mexico_City"))
        except Exception:
            pass
    return datetime.utcnow() - timedelta(hours=6)

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Inventario de Ropa - Tienda Caballero",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CREDENCIALES Y CONEXIÓN A GITHUB
# ==========================================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = st.secrets.get("REPO_NAME", "")

def github_headers():
    tok = GITHUB_TOKEN.strip() if GITHUB_TOKEN else ""
    if not tok.startswith("Bearer ") and not tok.startswith("token "):
        auth_header = f"Bearer {tok}"
    else:
        auth_header = tok
        
    return {
        "Authorization": auth_header,
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Streamlit-Inventario-App"
    }

# ==========================================
# RUTAS Y ARCHIVOS DE PERSISTENCIA
# ==========================================
DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "inventario.json")
SALES_FILE = os.path.join(DATA_DIR, "ventas.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categorias.json")
CAJA_FILE = os.path.join(DATA_DIR, "caja.json")
APARTADOS_FILE = os.path.join(DATA_DIR, "apartados.json")
CAMBIOS_FILE = os.path.join(DATA_DIR, "cambios.json")

DEFAULT_CATEGORIES = [
    "Chamarras", "Jeans", "Playeras", "Camisas", 
    "Suéteres", "Shorts", "Niño", "Bermudas", "Sacos", "Trajes"
]

def load_json(filepath):
    """Carga datos desde GitHub API si existe; de lo contrario, desde archivo local."""
    gh_path = filepath.replace("\\", "/")
    
    if GITHUB_TOKEN and REPO_NAME:
        try:
            url = f"https://api.github.com/repos/{REPO_NAME.strip()}/contents/{gh_path}"
            res = requests.get(url, headers=github_headers(), timeout=5)
            if res.status_code == 200:
                content = res.json().get("content", "")
                decoded = base64.b64decode(content).decode('utf-8')
                return json.loads(decoded)
        except Exception:
            pass

    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if "categorias" in filepath:
        return DEFAULT_CATEGORIES
    elif "caja" in filepath:
        return {"fondo_caja": 0.0, "ultima_fecha_corte": "2000-01-01 00:00:00"}
    else:
        return []

def save_json(filepath, data):
    """Guarda en disco local y sube a GitHub reportando el estado exacto."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not GITHUB_TOKEN or not REPO_NAME:
        return False, "Sin configurar GITHUB_TOKEN o REPO_NAME en Secrets."

    try:
        gh_path = filepath.replace("\\", "/")
        url = f"https://api.github.com/repos/{REPO_NAME.strip()}/contents/{gh_path}"
        
        get_res = requests.get(url, headers=github_headers(), timeout=5)
        sha = None
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")

        content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        content_b64 = base64.b64encode(content_bytes).decode('utf-8')

        payload = {
            "message": f"Auto-sync {os.path.basename(filepath)} via App",
            "content": content_b64,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        put_res = requests.put(url, headers=github_headers(), json=payload, timeout=8)
        
        if put_res.status_code in [200, 201]:
            return True, "OK"
        else:
            try:
                err_detail = put_res.json().get("message", put_res.text)
            except Exception:
                err_detail = put_res.text
            return False, f"GitHub [{put_res.status_code}] en {os.path.basename(filepath)}: {err_detail}"
    except Exception as e:
        return False, f"Excepción al conectar con GitHub: {str(e)}"

def sync_data():
    """Sincroniza todos los archivos y detecta errores de red."""
    r1 = save_json(PRODUCTS_FILE, st.session_state.productos)
    r2 = save_json(SALES_FILE, st.session_state.ventas)
    r3 = save_json(CATEGORIES_FILE, st.session_state.categorias)
    r4 = save_json(CAJA_FILE, st.session_state.caja)
    r5 = save_json(APARTADOS_FILE, st.session_state.apartados)
    r6 = save_json(CAMBIOS_FILE, st.session_state.cambios)

    errores = [msg for status, msg in [r1, r2, r3, r4, r5, r6] if not status]
    if errores:
        st.session_state["github_last_error"] = " | ".join(list(set(errores)))
    else:
        st.session_state["github_last_error"] = None

def init_storage():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(CATEGORIES_FILE):
        save_json(CATEGORIES_FILE, DEFAULT_CATEGORIES)
    if not os.path.exists(PRODUCTS_FILE):
        save_json(PRODUCTS_FILE, [])
    if not os.path.exists(SALES_FILE):
        save_json(SALES_FILE, [])
    if not os.path.exists(CAJA_FILE):
        save_json(CAJA_FILE, {"fondo_caja": 0.0, "ultima_fecha_corte": "2000-01-01 00:00:00"})
    if not os.path.exists(APARTADOS_FILE):
        save_json(APARTADOS_FILE, [])
    if not os.path.exists(CAMBIOS_FILE):
        save_json(CAMBIOS_FILE, [])

def normalize_product(prod):
    """Garantiza compatibilidad absoluta con datos previos y pruebas."""
    if not isinstance(prod, dict):
        return None

    if "Variantes" in prod and isinstance(prod["Variantes"], list):
        return prod

    tallas_raw = prod.get("Talla") or prod.get("Tallas") or prod.get("talla") or "M"
    if isinstance(tallas_raw, list):
        tallas = [str(t).strip().upper() for t in tallas_raw if str(t).strip()]
    elif isinstance(tallas_raw, str):
        tallas = [t.strip().upper() for t in tallas_raw.split(",") if t.strip()]
    else:
        tallas = ["M"]

    if not tallas:
        tallas = ["M"]

    colores_raw = prod.get("Colores") or prod.get("Color") or prod.get("color") or ["Único"]
    if isinstance(colores_raw, str):
        colores = [c.strip() for c in colores_raw.split(",") if c.strip()]
    elif isinstance(colores_raw, list):
        colores = [str(c).strip() for c in colores_raw if str(c).strip()]
    else:
        colores = ["Único"]

    if not colores:
        colores = ["Único"]

    variantes = []
    for color in colores:
        stock_dict = {}
        for t in tallas:
            stock_dict[t] = {
                "exhibido": int(prod.get("Stock_Exhibido") or prod.get("stock_vitrina") or 0),
                "bodega": int(prod.get("Stock_Bodega") or prod.get("stock_bodega") or 0)
            }
        variantes.append({"color": color, "stock": stock_dict})

    nombre = prod.get("Producto") or prod.get("nombre") or "Sin Nombre"
    categoria = prod.get("Categoria") or prod.get("categoria") or "General"
    precio_sug = float(prod.get("Precio_Sugerido") or prod.get("precio") or 0.0)
    precio_ven = float(prod.get("Precio_Venta") or prod.get("precio") or 0.0)

    return {
        "ID": str(prod.get("ID", f"PROD_{obtener_hora_local().strftime('%Y%m%d_%H%M%S_%f')}")),
        "Categoria": str(categoria),
        "Producto": str(nombre),
        "Precio_Sugerido": precio_sug,
        "Precio_Venta": precio_ven,
        "Tallas": tallas,
        "Variantes": variantes
    }

def generar_excel_seguro(df, nombre_hoja="Datos"):
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
        return buffer.getvalue(), "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    except Exception:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        return csv_data, "csv", "text/csv"

init_storage()

# Carga en Session State
if "productos" not in st.session_state:
    raw_prods = load_json(PRODUCTS_FILE)
    if not isinstance(raw_prods, list):
        raw_prods = []
    prods_normalizados = []
    for p in raw_prods:
        p_norm = normalize_product(p)
        if p_norm:
            prods_normalizados.append(p_norm)
    st.session_state.productos = prods_normalizados

if "ventas" not in st.session_state:
    st.session_state.ventas = load_json(SALES_FILE)
if "categorias" not in st.session_state:
    st.session_state.categorias = load_json(CATEGORIES_FILE)
if "caja" not in st.session_state:
    st.session_state.caja = load_json(CAJA_FILE)
if "apartados" not in st.session_state:
    st.session_state.apartados = load_json(APARTADOS_FILE)
if "cambios" not in st.session_state:
    st.session_state.cambios = load_json(CAMBIOS_FILE)
if "vista" not in st.session_state:
    st.session_state.vista = "ventas"
if "admin_tab" not in st.session_state:
    st.session_state.admin_tab = "add_product"
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

def notificar(mensaje, tipo="success"):
    st.session_state["flash_msg"] = mensaje
    st.session_state["flash_type"] = tipo

# BANNER DE ERROR DE GITHUB SI OCURRE ALGO
if st.session_state.get("github_last_error"):
    st.error(f"⚠️ **Atención al sincronizar con GitHub:** {st.session_state['github_last_error']}")

# Mostrar mensajes persistentes
if "flash_msg" in st.session_state and st.session_state["flash_msg"]:
    if st.session_state.get("flash_type") == "error":
        st.error(st.session_state["flash_msg"])
    else:
        st.success(st.session_state["flash_msg"])
    st.session_state["flash_msg"] = None
    st.session_state["flash_type"] = None

# ==========================================
# NAVEGACIÓN PRINCIPAL
# ==========================================
st.title("Inventario de Ropa")

nav_c1, nav_c2, nav_c3, nav_c4, nav_c5, nav_c6 = st.columns(6)

with nav_c1:
    btn_type = "primary" if st.session_state.vista == "ventas" else "secondary"
    if st.button("🛒 Registrar Venta", use_container_width=True, type=btn_type):
        st.session_state.vista = "ventas"
        st.rerun()

with nav_c2:
    btn_type = "primary" if st.session_state.vista == "cambios" else "secondary"
    if st.button("🔄 Cambios / Devolución", use_container_width=True, type=btn_type):
        st.session_state.vista = "cambios"
        st.rerun()

with nav_c3:
    btn_type = "primary" if st.session_state.vista == "apartados" else "secondary"
    if st.button("📑 Apartados", use_container_width=True, type=btn_type):
        st.session_state.vista = "apartados"
        st.rerun()

with nav_c4:
    btn_type = "primary" if st.session_state.vista == "ver_inventario" else "secondary"
    if st.button("📋 Ver Inventario", use_container_width=True, type=btn_type):
        st.session_state.vista = "ver_inventario"
        st.rerun()

with nav_c5:
    btn_type = "primary" if st.session_state.vista == "caja" else "secondary"
    if st.button("💰 Corte de Caja", use_container_width=True, type=btn_type):
        st.session_state.vista = "caja"
        st.rerun()

with nav_c6:
    btn_type = "primary" if st.session_state.vista == "admin" else "secondary"
    if st.button("🔐 Modo Administrador", use_container_width=True, type=btn_type):
        st.session_state.vista = "admin"
        st.rerun()

st.divider()

# ==========================================
# VISTA 1: REGISTRAR VENTAS
# ==========================================
if st.session_state.vista == "ventas":
    st.subheader("Registrar Ventas")
    
    if not st.session_state.categorias:
        st.info("No hay categorías creadas.")
    else:
        cat_cols = st.columns(min(len(st.session_state.categorias), 5))
        if "cat_activa" not in st.session_state:
            st.session_state.cat_activa = st.session_state.categorias[0]

        for idx, cat in enumerate(st.session_state.categorias):
            with cat_cols[idx % len(cat_cols)]:
                b_type = "primary" if st.session_state.cat_activa == cat else "secondary"
                if st.button(cat, key=f"btn_cat_{cat}_{idx}", use_container_width=True, type=b_type):
                    st.session_state.cat_activa = cat
                    st.rerun()

        st.caption(f"Categoría seleccionada: **{st.session_state.cat_activa}**")

        prods_cat = [p for p in st.session_state.productos if p["Categoria"] == st.session_state.cat_activa]
        
        if not prods_cat:
            st.warning("No hay productos registrados en esta categoría.")
        else:
            for idx_p, prod in enumerate(prods_cat):
                with st.expander(f"📦 **{prod['Producto']}** | Precio Sugerido: ${prod['Precio_Sugerido']:.2f}", expanded=True):
                    c_col1, c_col2 = st.columns(2)
                    
                    nombres_colores = [v["color"] for v in prod.get("Variantes", [])] if prod.get("Variantes") else ["Único"]
                    with c_col1:
                        color_sel = st.selectbox("Color:", nombres_colores, key=f"sel_col_{prod['ID']}_{idx_p}")
                    
                    with c_col2:
                        talla_sel = st.selectbox("Talla:", prod.get("Tallas", ["M"]), key=f"sel_tal_{prod['ID']}_{idx_p}")

                    variante_actual = next((v for v in prod.get("Variantes", []) if v["color"] == color_sel), None)
                    stock_exh = 0
                    stock_bod = 0
                    if variante_actual and talla_sel in variante_actual.get("stock", {}):
                        stock_exh = variante_actual["stock"][talla_sel].get("exhibido", 0)
                        stock_bod = variante_actual["stock"][talla_sel].get("bodega", 0)

                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Stock en Vitrina", stock_exh)
                    s_col2.metric("Stock en Bodega", stock_bod)
                    total_disp = stock_exh + stock_bod
                    s_col3.metric("Stock Total Disponible", total_disp)

                    st.markdown("---")
                    st.markdown("##### 🛒 Sección de Venta")
                    col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
                    
                    with col_p1:
                        cant_vender = st.number_input(
                            "Piezas a vender:", 
                            min_value=1, 
                            max_value=max(1, total_disp), 
                            value=1, 
                            key=f"cant_v_{prod['ID']}_{idx_p}"
                        )

                    with col_p2:
                        precio_unitario = st.number_input(
                            "Precio unitario final ($):", 
                            value=float(prod["Precio_Sugerido"]), 
                            step=10.0, 
                            key=f"p_real_{prod['ID']}_{idx_p}"
                        )
                    
                    with col_p3:
                        st.write("")
                        st.write("")
                        if total_disp >= cant_vender:
                            if st.button(f"Vender {cant_vender} pieza(s)", key=f"vender_{prod['ID']}_{idx_p}", type="primary", use_container_width=True):
                                restante = cant_vender
                                desc_exh = min(stock_exh, restante)
                                variante_actual["stock"][talla_sel]["exhibido"] -= desc_exh
                                restante -= desc_exh

                                desc_bod = min(stock_bod, restante)
                                variante_actual["stock"][talla_sel]["bodega"] -= desc_bod
                                restante -= desc_bod

                                ubic_str = f"Vitrina: {desc_exh}, Bodega: {desc_bod}" if desc_exh > 0 and desc_bod > 0 else ("Vitrina" if desc_exh > 0 else "Bodega")

                                nueva_venta = {
                                    "fecha": obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S"),
                                    "producto_id": prod["ID"],
                                    "producto": prod["Producto"],
                                    "talla": talla_sel,
                                    "color": color_sel,
                                    "cantidad": cant_vender,
                                    "precio_sugerido": prod["Precio_Sugerido"] * cant_vender,
                                    "precio_venta": precio_unitario * cant_vender,
                                    "categoria": prod["Categoria"],
                                    "ubicacion_venta": ubic_str
                                }
                                st.session_state.ventas.append(nueva_venta)
                                sync_data()
                                notificar(f"¡Venta registrada! ({cant_vender} pieza(s) de {prod['Producto']} - {color_sel} - Talla {talla_sel})")
                                st.rerun()
                        else:
                            st.button("Stock insuficiente", disabled=True, use_container_width=True, key=f"dis_{prod['ID']}_{idx_p}")

                    if st.session_state.get("admin_authenticated", False):
                        st.markdown("##### 🔄 Mover Stock entre Ubicaciones (Solo Administradora)")
                        mov_c1, mov_c2, mov_c3 = st.columns([2, 2, 2])
                        with mov_c1:
                            cant_mover = st.number_input("Piezas a mover:", min_value=1, value=1, key=f"cant_m_{prod['ID']}_{idx_p}")
                        
                        with mov_c2:
                            if stock_bod >= cant_mover:
                                if st.button(f"📦 Bodega ➔ Vitrina ({cant_mover})", key=f"pass_bv_{prod['ID']}_{idx_p}", use_container_width=True):
                                    variante_actual["stock"][talla_sel]["bodega"] -= cant_mover
                                    variante_actual["stock"][talla_sel]["exhibido"] += cant_mover
                                    sync_data()
                                    notificar(f"Se movieron {cant_mover} pieza(s) a Vitrina.")
                                    st.rerun()
                            else:
                                st.button("Bodega ➔ Vitrina", disabled=True, use_container_width=True, key=f"dis_bv_{prod['ID']}_{idx_p}")

                        with mov_c3:
                            if stock_exh >= cant_mover:
                                if st.button(f"🏷️ Vitrina ➔ Bodega ({cant_mover})", key=f"pass_vb_{prod['ID']}_{idx_p}", use_container_width=True):
                                    variante_actual["stock"][talla_sel]["exhibido"] -= cant_mover
                                    variante_actual["stock"][talla_sel]["bodega"] += cant_mover
                                    sync_data()
                                    notificar(f"Se movieron {cant_mover} pieza(s) a Bodega.")
                                    st.rerun()
                            else:
                                st.button("Vitrina ➔ Bodega", disabled=True, use_container_width=True, key=f"dis_vb_{prod['ID']}_{idx_p}")

# ==========================================
# VISTA 2: REGISTRAR CAMBIOS Y DEVOLUCIONES
# ==========================================
elif st.session_state.vista == "cambios":
    st.subheader("🔄 Registrar Cambios o Devoluciones con Selección de Inventario")

    col_dev, col_ent = st.columns(2)

    with col_dev:
        st.markdown("### 📥 1. Producto Devuelto por el Cliente")
        
        dev_manual = st.checkbox("¿El producto devuelto no está en catálogo?", key="cb_dev_manual")
        
        if dev_manual:
            prod_dev_str = st.text_input("Escribe el producto devuelto:", placeholder="Ej: Chamarra roja antigua Talla L")
            dest_dev_stock = "Vitrina"
            cant_dev = 1
            precio_dev_ref = 0.0
            p_dev_obj = None
            col_dev_sel = "-"
            talla_dev_sel = "-"
        else:
            cat_dev_sel = st.selectbox("Categoría devuelta:", st.session_state.categorias, key="sb_cat_dev")
            prods_dev_cat = [p for p in st.session_state.productos if p["Categoria"] == cat_dev_sel]
            
            if not prods_dev_cat:
                st.info("Sin productos en esta categoría.")
                prod_dev_str = ""
                precio_dev_ref = 0.0
                p_dev_obj = None
                col_dev_sel = "-"
                talla_dev_sel = "-"
            else:
                opts_dev = {f"{p['Producto']} (${p['Precio_Sugerido']:.2f})": p for p in prods_dev_cat}
                p_dev_label = st.selectbox("Producto devuelto:", list(opts_dev.keys()), key="sb_prod_dev")
                p_dev_obj = opts_dev[p_dev_label]
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    nombres_col_dev = [v["color"] for v in p_dev_obj.get("Variantes", [])] if p_dev_obj.get("Variantes") else ["Único"]
                    col_dev_sel = st.selectbox("Color devuelto:", nombres_col_dev, key="sb_col_dev")
                with col_d2:
                    talla_dev_sel = st.selectbox("Talla devuelta:", p_dev_obj.get("Tallas", ["M"]), key="sb_tal_dev")
                
                dest_dev_stock = st.radio("Regresar producto a:", ["Vitrina", "Bodega"], horizontal=True, key="rad_dest_dev")
                cant_dev = st.number_input("Cantidad devuelta:", min_value=1, value=1, key="num_cant_dev")
                
                prod_dev_str = f"{p_dev_obj['Producto']} ({col_dev_sel} / Talla {talla_dev_sel})"
                precio_dev_ref = float(p_dev_obj["Precio_Sugerido"]) * cant_dev

    with col_ent:
        st.markdown("### 📤 2. Producto Entregado a Cambio")
        
        cat_ent_sel = st.selectbox("Categoría a entregar:", st.session_state.categorias, key="sb_cat_ent")
        prods_ent_cat = [p for p in st.session_state.productos if p["Categoria"] == cat_ent_sel]
        
        if not prods_ent_cat:
            st.info("Sin productos en esta categoría.")
            prod_ent_str = ""
            precio_ent_ref = 0.0
            stock_ent_avail = 0
            p_ent_obj = None
            col_ent_sel = "-"
            talla_ent_sel = "-"
        else:
            opts_ent = {f"{p['Producto']} (${p['Precio_Sugerido']:.2f})": p for p in prods_ent_cat}
            p_ent_label = st.selectbox("Producto a entregar:", list(opts_ent.keys()), key="sb_prod_ent")
            p_ent_obj = opts_ent[p_ent_label]
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                nombres_col_ent = [v["color"] for v in p_ent_obj.get("Variantes", [])] if p_ent_obj.get("Variantes") else ["Único"]
                col_ent_sel = st.selectbox("Color a entregar:", nombres_col_ent, key="sb_col_ent")
            with col_e2:
                talla_ent_sel = st.selectbox("Talla a entregar:", p_ent_obj.get("Tallas", ["M"]), key="sb_tal_ent")

            var_ent = next((v for v in p_ent_obj.get("Variantes", []) if v["color"] == col_ent_sel), None)
            s_exh_e = var_ent["stock"][talla_ent_sel].get("exhibido", 0) if var_ent and talla_ent_sel in var_ent.get("stock", {}) else 0
            s_bod_e = var_ent["stock"][talla_ent_sel].get("bodega", 0) if var_ent and talla_ent_sel in var_ent.get("stock", {}) else 0
            
            orig_ent_stock = st.radio("Descontar producto entregado de:", ["Vitrina", "Bodega"], horizontal=True, key="rad_orig_ent")
            stock_ent_avail = s_exh_e if orig_ent_stock == "Vitrina" else s_bod_e
            st.caption(f"Stock disponible en {orig_ent_stock}: **{stock_ent_avail} pieza(s)**")
            
            cant_ent = st.number_input("Cantidad a entregar:", min_value=1, value=1, key="num_cant_ent")
            prod_ent_str = f"{p_ent_obj['Producto']} ({col_ent_sel} / Talla {talla_ent_sel})"
            precio_ent_ref = float(p_ent_obj["Precio_Sugerido"]) * cant_ent

    st.divider()

    st.markdown("### 💵 3. Ajuste de Cobro y Confirmación")
    dif_estimada = max(0.0, precio_ent_ref - precio_dev_ref)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        diferencia_cobrada = st.number_input("Diferencia cobrada al cliente ($):", value=float(dif_estimada), step=10.0)
    with col_f2:
        motivo = st.text_input("Motivo del cambio:", placeholder="Ej: Cambio de talla por ajuste")

    if st.button("💾 Confirmar Cambio y Actualizar Inventario", type="primary"):
        if not prod_dev_str or not prod_ent_str:
            st.warning("Asegúrate de haber seleccionado ambos productos.")
        elif not dev_manual and p_ent_obj and stock_ent_avail < cant_ent:
            st.error("No hay stock suficiente del producto a entregar.")
        else:
            if not dev_manual and p_dev_obj:
                var_dev = next((v for v in p_dev_obj.get("Variantes", []) if v["color"] == col_dev_sel), None)
                if var_dev and talla_dev_sel in var_dev.get("stock", {}):
                    key_s_dev = "exhibido" if dest_dev_stock == "Vitrina" else "bodega"
                    var_dev["stock"][talla_dev_sel][key_s_dev] += cant_dev

            if p_ent_obj:
                var_ent = next((v for v in p_ent_obj.get("Variantes", []) if v["color"] == col_ent_sel), None)
                if var_ent and talla_ent_sel in var_ent.get("stock", {}):
                    key_s_ent = "exhibido" if orig_ent_stock == "Vitrina" else "bodega"
                    var_ent["stock"][talla_ent_sel][key_s_ent] -= cant_ent

            if not dev_manual and p_dev_obj and p_ent_obj and p_dev_obj.get("ID") == p_ent_obj.get("ID"):
                if talla_dev_sel != talla_ent_sel and col_dev_sel == col_ent_sel:
                    tipo_label = "🔄 Cambio de Talla"
                elif col_dev_sel != col_ent_sel and talla_dev_sel == talla_ent_sel:
                    tipo_label = "🔄 Cambio de Color"
                else:
                    tipo_label = "🔄 Cambio de Talla/Color"
            else:
                tipo_label = "🔄 Cambio de Producto"

            registro_cambio = {
                "fecha": obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S"),
                "devuelto": prod_dev_str,
                "entregado": prod_ent_str,
                "diferencia": diferencia_cobrada,
                "motivo": motivo
            }
            st.session_state.cambios.append(registro_cambio)

            desc_dif = f"Diferencia: ${diferencia_cobrada:,.2f}" if diferencia_cobrada > 0 else "Cambio sin costo ($0.00)"
            cat_bitacora = p_ent_obj["Categoria"] if p_ent_obj else "Cambios"
            
            registro_venta_cambio = {
                "fecha": obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S"),
                "producto_id": p_ent_obj["ID"] if p_ent_obj else "CAMBIO",
                "producto": f"{tipo_label}: Entregado ({prod_ent_str}) ➔ Devuelto ({prod_dev_str})",
                "talla": talla_ent_sel if p_ent_obj else "-",
                "color": col_ent_sel if p_ent_obj else "-",
                "cantidad": cant_ent,
                "precio_sugerido": dif_estimada,
                "precio_venta": diferencia_cobrada,
                "categoria": cat_bitacora,
                "ubicacion_venta": desc_dif
            }
            st.session_state.ventas.append(registro_venta_cambio)

            sync_data()
            notificar(f"¡{tipo_label} registrado! ({prod_dev_str} ➔ {prod_ent_str}) - Inventario y Bitácora actualizados.")
            st.rerun()

    st.divider()
    st.markdown("### 📜 Historial de Cambios")
    if st.session_state.cambios:
        df_cambios = pd.DataFrame(st.session_state.cambios)
        st.dataframe(df_cambios, use_container_width=True)
    else:
        st.info("No hay registros de cambios realizados.")

# ==========================================
# VISTA 3: GESTIÓN DE APARTADOS
# ==========================================
elif st.session_state.vista == "apartados":
    st.subheader("📑 Gestión de Apartados de Prenda con Selección de Inventario")

    tab_nuevo_ap, tab_lista_ap = st.tabs(["➕ Crear Nuevo Apartado", "📋 Lista de Apartados Activos"])

    with tab_nuevo_ap:
        st.markdown("### 📦 Seleccionar Producto a Apartar del Inventario")
        
        cat_ap_sel = st.selectbox("Categoría:", st.session_state.categorias, key="sb_cat_ap")
        prods_ap_cat = [p for p in st.session_state.productos if p["Categoria"] == cat_ap_sel]
        
        if not prods_ap_cat:
            st.info("Sin productos en esta categoría.")
        else:
            opts_ap = {f"{p['Producto']} (${p['Precio_Sugerido']:.2f})": p for p in prods_ap_cat}
            p_ap_label = st.selectbox("Producto a apartar:", list(opts_ap.keys()), key="sb_prod_ap")
            p_ap_obj = opts_ap[p_ap_label]

            c_ap1, c_ap2 = st.columns(2)
            with c_ap1:
                nombres_col_ap = [v["color"] for v in p_ap_obj.get("Variantes", [])] if p_ap_obj.get("Variantes") else ["Único"]
                col_ap_sel = st.selectbox("Color:", nombres_col_ap, key="sb_col_ap")
            with c_ap2:
                talla_ap_sel = st.selectbox("Talla:", p_ap_obj.get("Tallas", ["M"]), key="sb_tal_ap")

            var_ap = next((v for v in p_ap_obj.get("Variantes", []) if v["color"] == col_ap_sel), None)
            s_exh_a = var_ap["stock"][talla_ap_sel].get("exhibido", 0) if var_ap and talla_ap_sel in var_ap.get("stock", {}) else 0
            s_bod_a = var_ap["stock"][talla_ap_sel].get("bodega", 0) if var_ap and talla_ap_sel in var_ap.get("stock", {}) else 0

            orig_ap_stock = st.radio("Reservar y descontar stock de:", ["Vitrina", "Bodega"], horizontal=True, key="rad_orig_ap")
            stock_ap_avail = s_exh_a if orig_ap_stock == "Vitrina" else s_bod_a
            st.caption(f"Stock disponible en {orig_ap_stock}: **{stock_ap_avail} pieza(s)**")

            cant_ap = st.number_input("Cantidad a apartar:", min_value=1, value=1, key="num_cant_ap")

            st.divider()
            st.markdown("### 👤 Datos del Cliente y Pago")

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                nom_cliente = st.text_input("Nombre del Cliente:", placeholder="Ej: Juan Pérez")
                precio_sug_calc = float(p_ap_obj["Precio_Sugerido"]) * cant_ap
                precio_tot = st.number_input("Precio Total ($):", min_value=0.0, value=float(precio_sug_calc), step=10.0)
            with col_a2:
                anticipo_ap = st.number_input("Anticipo / Abono Inicial ($):", min_value=0.0, value=0.0, step=10.0)
                restante_calc = max(0.0, precio_tot - anticipo_ap)
                st.write(f"**Monto Restante por Pagar:** `${restante_calc:,.2f}`")

            if st.button("💾 Crear Apartado y Reservar Stock", type="primary"):
                if not nom_cliente:
                    st.warning("Ingresa el nombre del cliente.")
                elif stock_ap_avail < cant_ap:
                    st.error("Stock insuficiente en el inventario para apartar esta prenda.")
                else:
                    key_s_ap = "exhibido" if orig_ap_stock == "Vitrina" else "bodega"
                    var_ap["stock"][talla_ap_sel][key_s_ap] -= cant_ap

                    concepto_full = f"{p_ap_obj['Producto']} ({cant_ap} pza) - {col_ap_sel} - Talla {talla_ap_sel}"
                    
                    nuevo_ap = {
                        "id": f"AP_{obtener_hora_local().strftime('%Y%m%d_%H%M%S')}",
                        "fecha": obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S"),
                        "cliente": nom_cliente,
                        "concepto": concepto_full,
                        "total": precio_tot,
                        "abonado": anticipo_ap,
                        "restante": restante_calc,
                        "estado": "Pendiente" if restante_calc > 0 else "Liquidado"
                    }
                    st.session_state.apartados.append(nuevo_ap)

                    if anticipo_ap > 0:
                        registro_venta_ap = {
                            "fecha": obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S"),
                            "producto_id": nuevo_ap["id"],
                            "producto": f"📑 Anticipo Apartado: {concepto_full} ({nom_cliente})",
                            "talla": talla_ap_sel,
                            "color": col_ap_sel,
                            "cantidad": cant_ap,
                            "precio_sugerido": anticipo_ap,
                            "precio_venta": anticipo_ap,
                            "categoria": "Apartados",
                            "ubicacion_venta": f"Anticipo (Restan ${restante_calc:,.2f})"
                        }
                        st.session_state.ventas.append(registro_venta_ap)

                    sync_data()
                    notificar(f"¡Apartado creado y stock reservado para {nom_cliente}!")
                    st.rerun()

    with tab_lista_ap:
        if st.session_state.apartados:
            for idx_ap, ap in enumerate(st.session_state.apartados):
                estado_emoji = "🟢 Liquidado" if ap.get("restante", 0) <= 0 else "🟡 Pendiente"
                with st.expander(f"👤 **{ap.get('cliente')}** | {ap.get('concepto')} | {estado_emoji}"):
                    st.write(f"**Fecha:** {ap.get('fecha')}")
                    st.write(f"**Total:** ${ap.get('total',0):,.2f} | **Abonado:** ${ap.get('abonado',0):,.2f} | **Restante:** ${ap.get('restante',0):,.2f}")
                    
                    if ap.get("restante", 0) > 0:
                        st.markdown("---")
                        c_ab1, c_ab2 = st.columns([2, 2])
                        with c_ab1:
                            nuevo_abono = st.number_input("Añadir nuevo abono ($):", min_value=0.0, max_value=float(ap.get("restante", 0)), step=10.0, key=f"ab_{ap.get('id')}_{idx_ap}")
                        with c_ab2:
                            st.write("")
                            st.write("")
                            if st.button("💵 Registrar Abono", key=f"btn_ab_{ap.get('id')}_{idx_ap}", type="primary"):
                                if nuevo_abono > 0:
                                    ap["abonado"] += nuevo_abono
                                    ap["restante"] -= nuevo_abono
                                    if ap["restante"] <= 0:
                                        ap["estado"] = "Liquidado"
                                    
                                    registro_venta_abono = {
                                        "fecha": obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S"),
                                        "producto_id": ap.get("id", "ABONO"),
                                        "producto": f"💵 Abono Apartado: {ap.get('concepto')} ({ap.get('cliente')})",
                                        "talla": "-",
                                        "color": "-",
                                        "cantidad": 1,
                                        "precio_sugerido": nuevo_abono,
                                        "precio_venta": nuevo_abono,
                                        "categoria": "Apartados",
                                        "ubicacion_venta": f"Abono (Restan ${ap['restante']:,.2f})"
                                    }
                                    st.session_state.ventas.append(registro_venta_abono)

                                    sync_data()
                                    notificar(f"Abono de ${nuevo_abono:,.2f} registrado para {ap.get('cliente')}.")
                                    st.rerun()
                                else:
                                    st.warning("El abono debe ser mayor a $0.")
        else:
            st.info("No hay prendas en apartado actualmente.")

# ==========================================
# VISTA 4: VER INVENTARIO EN PANTALLA
# ==========================================
elif st.session_state.vista == "ver_inventario":
    st.subheader("Consulta General de Inventario")

    if not st.session_state.productos:
        st.info("No hay productos en el inventario.")
    else:
        filas = []
        for p in st.session_state.productos:
            for v in p.get("Variantes", []):
                col_nombre = v.get("color", "Único")
                for t, s in v.get("stock", {}).items():
                    exh = s.get("exhibido", 0)
                    bod = s.get("bodega", 0)
                    filas.append({
                        "Categoría": p.get("Categoria", ""),
                        "Producto": p.get("Producto", ""),
                        "Color": col_nombre,
                        "Talla": t,
                        "Precio Sugerido ($)": p.get("Precio_Sugerido", 0.0),
                        "Precio Venta Base ($)": p.get("Precio_Venta", 0.0),
                        "Vitrina": exh,
                        "Bodega": bod,
                        "Stock Total": exh + bod
                    })

        df_inv = pd.DataFrame(filas)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Variedad de Productos", len(st.session_state.productos))
        k2.metric("Piezas en Vitrina", df_inv["Vitrina"].sum())
        k3.metric("Piezas en Bodega", df_inv["Bodega"].sum())
        k4.metric("Stock Total Tienda", df_inv["Stock Total"].sum())

        st.divider()

        busqueda = st.text_input("🔍 Buscar por Producto, Categoría, Color o Talla:", placeholder="Ej: Café, Chamarras, M...")
        
        if busqueda:
            term = busqueda.lower()
            df_mostrar = df_inv[
                df_inv["Producto"].str.lower().str.contains(term) |
                df_inv["Categoría"].str.lower().str.contains(term) |
                df_inv["Color"].str.lower().str.contains(term) |
                df_inv["Talla"].str.lower().str.contains(term)
            ]
        else:
            df_mostrar = df_inv

        st.dataframe(df_mostrar, use_container_width=True, height=450)

# ==========================================
# VISTA 5: CORTE DE CAJA Y VENTAS DIARIAS
# ==========================================
elif st.session_state.vista == "caja":
    st.subheader("💰 Corte de Caja y Ventas del Turno Actual")
    
    fondo = st.session_state.caja.get("fondo_caja", 0.0)
    ultima_corte_str = st.session_state.caja.get("ultima_fecha_corte", "2000-01-01 00:00:00")
    
    if st.session_state.ventas:
        df_v = pd.DataFrame(st.session_state.ventas)
        if 'fecha' in df_v.columns and not df_v.empty:
            fechas_limpias = df_v['fecha'].astype(str).str.replace('T', ' ').str.split('.').str[0]
            df_v['fecha_dt'] = pd.to_datetime(fechas_limpias, errors='coerce')
            
            corte_limpio = str(ultima_corte_str).replace('T', ' ').split('.')[0]
            ultima_corte_dt = pd.to_datetime(corte_limpio, errors='coerce')
                
            ventas_hoy = df_v[df_v['fecha_dt'] > ultima_corte_dt]
        else:
            ventas_hoy = pd.DataFrame()
        
        total_ventas_hoy = ventas_hoy['precio_venta'].sum() if not ventas_hoy.empty and 'precio_venta' in ventas_hoy.columns else 0.0
        total_sugerido_hoy = ventas_hoy['precio_sugerido'].sum() if not ventas_hoy.empty and 'precio_sugerido' in ventas_hoy.columns else 0.0
        regateo_hoy = total_sugerido_hoy - total_ventas_hoy
        cant_piezas_hoy = ventas_hoy['cantidad'].sum() if not ventas_hoy.empty and 'cantidad' in ventas_hoy.columns else len(ventas_hoy)
    else:
        df_v = pd.DataFrame()
        ventas_hoy = pd.DataFrame()
        total_ventas_hoy = 0.0
        total_sugerido_hoy = 0.0
        regateo_hoy = 0.0
        cant_piezas_hoy = 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Fondo Inicial", f"${fondo:,.2f}")
    k2.metric("Ventas / Ingresos del Turno", f"${total_ventas_hoy:,.2f}")
    k3.metric("Total Esperado en Caja", f"${(fondo + total_ventas_hoy):,.2f}")
    k4.metric("Descuentos / Regateo", f"-${regateo_hoy:,.2f}")

    if ultima_corte_str != "2000-01-01 00:00:00":
        st.caption(f"⏱️ Último corte registrado el: **{ultima_corte_str}** | Movimientos acumulados desde ese corte: **{cant_piezas_hoy}**")

    st.divider()

    st.markdown("### 🌅 Cierre de Turno / Realizar Corte de Caja")
    
    if st.session_state.get("admin_authenticated", False):
        with st.expander("🔑 Realizar Corte de Caja y Reiniciar Ventas del Turno", expanded=True):
            st.info("Al presionar este botón se guardará la hora del corte, la consola de ventas se reiniciará a **$0.00** y todo el historial quedará archivado de forma segura.")
            nuevo_fondo_input = st.number_input(
                "Monto de Fondo de Caja para el siguiente turno/día ($):", 
                value=float(fondo),
                step=50.0,
                key="cierre_nuevo_fondo"
            )
            confirmar_cierre = st.checkbox("Confirmo que deseo realizar el corte de caja y reiniciar la consola a $0.00.")
            
            if st.button("🔒 Realizar Corte de Caja y Reiniciar Turno", type="primary"):
                if confirmar_cierre:
                    ahora_str = obtener_hora_local().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.caja["fondo_caja"] = nuevo_fondo_input
                    st.session_state.caja["ultima_fecha_corte"] = ahora_str
                    sync_data()
                    notificar(f"¡Corte de caja realizado! Consola reiniciada a $0.00. Nuevo fondo: ${nuevo_fondo_input:,.2f}.")
                    st.rerun()
                else:
                    st.error("Por favor marca la casilla de confirmación antes de continuar.")
    else:
        st.info("🔒 *La modificación del fondo de caja y la realización del corte están reservadas exclusivamente para la Administradora con contraseña.*")

    st.divider()

    st.markdown("### 📊 Historial de Ventas / Bitácora y Descarga en Excel")

    tab_hoy, tab_hist = st.tabs(["📅 Ventas del Turno Actual", "📜 Historial Completo (Todos los Turnos)"])

    with tab_hoy:
        if not ventas_hoy.empty:
            cols_m = [c for c in ['fecha', 'producto', 'categoria', 'talla', 'color', 'cantidad', 'precio_sugerido', 'precio_venta', 'ubicacion_venta'] if c in ventas_hoy.columns]
            st.dataframe(
                ventas_hoy[cols_m], 
                use_container_width=True
            )
            bytes_data_hoy, ext_h, mime_h = generar_excel_seguro(ventas_hoy, "Ventas_Turno")
            st.download_button(
                label=f"📥 Descargar Ventas del Turno en Excel ({ext_h.upper()})",
                data=bytes_data_hoy,
                file_name=f"Ventas_Turno_{obtener_hora_local().strftime('%Y%m%d_%H%M%S')}.{ext_h}",
                mime=mime_h
            )
        else:
            st.info("Consola en $0.00. Aún no hay ventas o movimientos registrados desde el último corte.")

    with tab_hist:
        if not df_v.empty and 'fecha_dt' in df_v.columns:
            st.markdown("##### Filtrar Registros por Fecha")
            fechas_disponibles = sorted(df_v['fecha_dt'].dt.date.dropna().unique(), reverse=True)
            
            filtro_fecha = st.multiselect(
                "Selecciona día(s) específico(s) (deja vacío para ver todo el historial acumulado):",
                options=fechas_disponibles,
                format_func=lambda d: d.strftime("%d/%m/%Y")
            )

            if filtro_fecha:
                df_filtrado = df_v[df_v['fecha_dt'].dt.date.isin(filtro_fecha)]
            else:
                df_filtrado = df_v

            cols_m_h = [c for c in ['fecha', 'producto', 'categoria', 'talla', 'color', 'cantidad', 'precio_sugerido', 'precio_venta', 'ubicacion_venta'] if c in df_filtrado.columns]
            st.dataframe(
                df_filtrado[cols_m_h], 
                use_container_width=True
            )

            bytes_data_hist, ext_hist, mime_hist = generar_excel_seguro(df_filtrado, "Historial_Ventas")
            st.download_button(
                label=f"📥 Descargar Ventas Filtradas/Histórico Completo ({ext_hist.upper()})",
                data=bytes_data_hist,
                file_name=f"Ventas_Historico_{obtener_hora_local().strftime('%Y%m%d')}.{ext_hist}",
                mime=mime_hist
            )
        else:
            st.info("No hay historial de ventas previo.")

# ==========================================
# VISTA 6: MODO ADMINISTRADOR Y GESTIÓN
# ==========================================
elif st.session_state.vista == "admin":
    st.subheader("Modo Administrador y Gestión")

    if not st.session_state.admin_authenticated:
        pwd = st.text_input("Ingrese Contraseña de Administradora:", type="password")
        if st.button("Ingresar"):
            if pwd == "michiotaku":
                st.session_state.admin_authenticated = True
                notificar("Acceso concedido al panel de administradora.")
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    else:
        ad_col1, ad_col2, ad_col3, ad_col4, ad_col5 = st.columns(5)
        
        with ad_col1:
            if st.button("🏷️ Categorías", use_container_width=True):
                st.session_state.admin_tab = "categorias"
        with ad_col2:
            if st.button("➕ Añadir Producto", use_container_width=True):
                st.session_state.admin_tab = "add_product"
        with ad_col3:
            if st.button("✏️ Editar / Resurtir", use_container_width=True):
                st.session_state.admin_tab = "edit_product"
        with ad_col4:
            if st.button("🗑️ Eliminar Producto", use_container_width=True):
                st.session_state.admin_tab = "delete_product"
        with ad_col5:
            if st.button("📥 Descargar Inventario", use_container_width=True):
                st.session_state.admin_tab = "export"

        st.divider()

        # TAB 1: EDITAR CATEGORÍAS
        if st.session_state.admin_tab == "categorias":
            st.markdown("### Gestión de Categorías")
            c_add, c_del = st.columns(2)
            with c_add:
                nueva_cat = st.text_input("Nueva Categoría:")
                if st.button("Agregar Categoría"):
                    if nueva_cat and nueva_cat not in st.session_state.categorias:
                        st.session_state.categorias.append(nueva_cat)
                        sync_data()
                        notificar(f"Categoría '{nueva_cat}' agregada.")
                        st.rerun()
            with c_del:
                cat_del = st.selectbox("Eliminar Categoría:", st.session_state.categorias)
                if st.button("Eliminar"):
                    st.session_state.categorias.remove(cat_del)
                    sync_data()
                    notificar(f"Categoría '{cat_del}' eliminada.")
                    st.rerun()

        # TAB 2: AÑADIR PRODUCTO
        elif st.session_state.admin_tab == "add_product":
            st.markdown("### AÑADIR PRODUCTO")
            
            v = st.session_state.form_version
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                cat_sel = st.selectbox("Categoría", st.session_state.categorias, key=f"add_cat_{v}")
            with f_col2:
                nombre_prod = st.text_input("Nombre producto", placeholder="Ej: Café repelente", key=f"add_name_{v}")

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                p_sugerido = st.number_input("Precio Sugerido ($)", min_value=0.0, value=0.0, step=10.0, key=f"add_sug_{v}")
            with p_col2:
                p_venta = st.number_input("Precio Venta Base ($)", min_value=0.0, value=0.0, step=10.0, key=f"add_ven_{v}")

            tallas_input = st.text_input(
                "Tallas disponibles (separadas por coma):", 
                value="S, M, G, XG",
                key=f"add_tal_{v}"
            )
            st.caption("🔴 * Depende de las que ponga se habilitan esos por color.")

            lista_tallas = [t.strip().upper() for t in tallas_input.split(",") if t.strip()]

            if "num_colores" not in st.session_state:
                st.session_state.num_colores = 1

            variantes_capturadas = []

            st.divider()
            st.markdown("#### Configuración de Colores e Inventario")

            for i in range(st.session_state.num_colores):
                st.markdown(f"🎨 **Color #{i+1}**")
                color_name = st.text_input(f"Nombre del Color #{i+1}:", key=f"c_name_{i}_{v}")
                
                st.write("🟦 **Stock en Vitrina / Exhibición**")
                cols_v = st.columns(len(lista_tallas) if lista_tallas else 1)
                vitrina_stock = {}
                for idx, t in enumerate(lista_tallas):
                    with cols_v[idx]:
                        val_v = st.number_input(f"V {t}", min_value=0, value=0, key=f"v_{i}_{t}_{v}")
                        vitrina_stock[t] = val_v

                st.write("🟫 **Stock en Bodega**")
                cols_b = st.columns(len(lista_tallas) if lista_tallas else 1)
                bodega_stock = {}
                for idx, t in enumerate(lista_tallas):
                    with cols_b[idx]:
                        val_b = st.number_input(f"B {t}", min_value=0, value=0, key=f"b_{i}_{t}_{v}")
                        bodega_stock[t] = val_b

                stock_combinado = {}
                for t in lista_tallas:
                    stock_combinado[t] = {
                        "exhibido": vitrina_stock[t],
                        "bodega": bodega_stock[t]
                    }
                
                variantes_capturadas.append({
                    "color": color_name if color_name else f"Color #{i+1}",
                    "stock": stock_combinado
                })
                st.divider()

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("➕ Agregar Otro Color"):
                    st.session_state.num_colores += 1
                    st.rerun()

            with btn_col2:
                if st.button("💾 Guardar Producto", type="primary"):
                    if not nombre_prod or not lista_tallas:
                        notificar("Ingresa el nombre del producto y al menos una talla.", tipo="error")
                        st.rerun()
                    else:
                        nuevo_p = {
                            "ID": f"PROD_{obtener_hora_local().strftime('%Y%m%d_%H%M%S_%f')}",
                            "Categoria": cat_sel,
                            "Producto": nombre_prod,
                            "Precio_Sugerido": float(p_sugerido),
                            "Precio_Venta": float(p_venta),
                            "Tallas": lista_tallas,
                            "Variantes": variantes_capturadas
                        }
                        
                        st.session_state.productos.append(nuevo_p)
                        sync_data()
                        
                        st.session_state.num_colores = 1
                        st.session_state.form_version += 1
                        
                        notificar(f"¡Producto '{nombre_prod}' guardado con éxito! Ya aparece en '{cat_sel}'.")
                        st.rerun()

        # TAB 3: EDITAR Y RESURTIR PRODUCTOS
        elif st.session_state.admin_tab == "edit_product":
            st.markdown("### Editar y Resurtir Productos")
            if not st.session_state.productos:
                st.info("Sin productos registrados.")
            else:
                prod_opts = {f"{p['Producto']} ({p['Categoria']})": p["ID"] for p in st.session_state.productos}
                p_sel_name = st.selectbox("Seleccione Producto a Editar / Resurtir:", list(prod_opts.keys()))
                prod_obj = next(p for p in st.session_state.productos if p["ID"] == prod_opts[p_sel_name])

                st.divider()
                st.markdown("#### Datos Generales")
                prod_obj["Producto"] = st.text_input("Nombre del Producto:", value=prod_obj["Producto"])
                
                cat_idx = st.session_state.categorias.index(prod_obj["Categoria"]) if prod_obj["Categoria"] in st.session_state.categorias else 0
                prod_obj["Categoria"] = st.selectbox("Categoría:", st.session_state.categorias, index=cat_idx)

                c_e1, c_e2 = st.columns(2)
                prod_obj["Precio_Sugerido"] = c_e1.number_input("Precio Sugerido ($)", value=float(prod_obj["Precio_Sugerido"]))
                prod_obj["Precio_Venta"] = c_e2.number_input("Precio Venta Base ($)", value=float(prod_obj["Precio_Venta"]))

                tallas_str = ", ".join(prod_obj.get("Tallas", []))
                nuevas_tallas_str = st.text_input("Tallas disponibles (separadas por coma):", value=tallas_str)
                nuevas_tallas = [t.strip().upper() for t in nuevas_tallas_str.split(",") if t.strip()]
                prod_obj["Tallas"] = nuevas_tallas

                st.divider()
                st.markdown("#### 📦 Inventario y Resurtido por Color")

                for idx_v, var in enumerate(prod_obj.get("Variantes", [])):
                    st.markdown(f"🎨 **Color #{idx_v + 1}**")
                    var["color"] = st.text_input(f"Nombre del Color:", value=var["color"], key=f"e_col_n_{prod_obj['ID']}_{idx_v}")

                    if "stock" not in var:
                        var["stock"] = {}

                    for t in nuevas_tallas:
                        if t not in var["stock"]:
                            var["stock"][t] = {"exhibido": 0, "bodega": 0}

                    st.write("🟦 **Stock en Vitrina**")
                    cols_v = st.columns(len(nuevas_tallas) if nuevas_tallas else 1)
                    for idx_t, t in enumerate(nuevas_tallas):
                        with cols_v[idx_t]:
                            var["stock"][t]["exhibido"] = st.number_input(
                                f"V {t}", 
                                min_value=0, 
                                value=int(var["stock"][t].get("exhibido", 0)),
                                key=f"e_v_{prod_obj['ID']}_{idx_v}_{t}"
                            )

                    st.write("🟫 **Stock en Bodega**")
                    cols_b = st.columns(len(nuevas_tallas) if nuevas_tallas else 1)
                    for idx_t, t in enumerate(nuevas_tallas):
                        with cols_b[idx_t]:
                            var["stock"][t]["bodega"] = st.number_input(
                                f"B {t}", 
                                min_value=0, 
                                value=int(var["stock"][t].get("bodega", 0)),
                                key=f"e_b_{prod_obj['ID']}_{idx_v}_{t}"
                            )
                    st.divider()

                e_b1, e_b2 = st.columns(2)
                with e_b1:
                    if st.button("➕ Agregar Nuevo Color a este Producto"):
                        nuevo_col_struct = {
                            "color": f"Color #{len(prod_obj['Variantes']) + 1}",
                            "stock": {t: {"exhibido": 0, "bodega": 0} for t in nuevas_tallas}
                        }
                        prod_obj["Variantes"].append(nuevo_col_struct)
                        sync_data()
                        st.rerun()

                with e_b2:
                    if st.button("💾 Guardar Cambios y Resurtido", type="primary"):
                        sync_data()
                        notificar(f"¡Producto '{prod_obj['Producto']}' actualizado y resurtido correctamente!")
                        st.rerun()

        # TAB 4: ELIMINAR PRODUCTO
        elif st.session_state.admin_tab == "delete_product":
            st.markdown("### Eliminar Producto")
            if not st.session_state.productos:
                st.info("Sin productos registrados.")
            else:
                prod_opts = {f"{p['Producto']} ({p['ID']})": p["ID"] for p in st.session_state.productos}
                p_del_name = st.selectbox("Seleccione Producto a Eliminar:", list(prod_opts.keys()))
                if st.button("Confirmar Eliminar", type="primary"):
                    st.session_state.productos = [p for p in st.session_state.productos if p["ID"] != prod_opts[p_del_name]]
                    sync_data()
                    notificar("Producto eliminado del inventario.")
                    st.rerun()

        # TAB 5: DESCARGAR INVENTARIO
        elif st.session_state.admin_tab == "export":
            st.markdown("### Descargar Inventario")
            if st.session_state.productos:
                filas_export = []
                for p in st.session_state.productos:
                    for v in p.get("Variantes", []):
                        col_nombre = v.get("color", "Único")
                        for t, s in v.get("stock", {}).items():
                            filas_export.append({
                                "Categoría": p.get("Categoria", ""),
                                "Producto": p.get("Producto", ""),
                                "Color": col_nombre,
                                "Talla": t,
                                "Precio Sugerido": p.get("Precio_Sugerido", 0.0),
                                "Precio Venta": p.get("Precio_Venta", 0.0),
                                "Vitrina": s.get("exhibido", 0),
                                "Bodega": s.get("bodega", 0),
                                "Stock Total": s.get("exhibido", 0) + s.get("bodega", 0)
                            })
                
                df_exp = pd.DataFrame(filas_export)
                bytes_data, ext, mime = generar_excel_seguro(df_exp, "Inventario")

                st.download_button(
                    label=f"📥 Descargar Inventario ({ext.upper()})",
                    data=bytes_data,
                    file_name=f"Inventario_{obtener_hora_local().strftime('%Y%m%d')}.{ext}",
                    mime=mime
                )
            else:
                st.info("No hay datos en el inventario para descargar.")