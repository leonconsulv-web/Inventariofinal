import streamlit as st
import pandas as pd
import json
import os
import base64
import urllib.request
from datetime import datetime
import io

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
# RUTAS Y ARCHIVOS DE PERSISTENCIA
# ==========================================
DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "inventario.json")
SALES_FILE = os.path.join(DATA_DIR, "ventas.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categorias.json")
CAJA_FILE = os.path.join(DATA_DIR, "caja.json")
APARTADOS_FILE = os.path.join(DATA_DIR, "apartados.json")

DEFAULT_CATEGORIES = [
    "Chamarras", "Jeans", "Playeras", "Camisas", 
    "Suéteres", "Shorts", "Niño", "Bermudas", "Sacos", "Trajes"
]

def save_to_github(filepath, data):
    """Guarda localmente y sincroniza permanentemente con GitHub API."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            token = st.secrets["GITHUB_TOKEN"]
            repo = st.secrets["REPO_NAME"]
            filename = os.path.basename(filepath)
            path_in_repo = f"data/{filename}"
            
            url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "StreamlitApp"
            }
            
            sha = None
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode())
                    sha = res_data.get("sha")
            except Exception:
                pass
            
            content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            content_b64 = base64.b64encode(content_bytes).decode("utf-8")
            
            payload = {
                "message": f"Auto-sync {filename} via App",
                "content": content_b64
            }
            if sha:
                payload["sha"] = sha
                
            req_put = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode("utf-8"), 
                headers=headers, 
                method="PUT"
            )
            with urllib.request.urlopen(req_put) as response:
                pass
        except Exception as e:
            print(f"Error sincronizando {filepath} con GitHub: {e}")

def init_storage():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(CATEGORIES_FILE):
        save_to_github(CATEGORIES_FILE, DEFAULT_CATEGORIES)
    if not os.path.exists(PRODUCTS_FILE):
        save_to_github(PRODUCTS_FILE, [])
    if not os.path.exists(SALES_FILE):
        save_to_github(SALES_FILE, [])
    if not os.path.exists(CAJA_FILE):
        save_to_github(CAJA_FILE, {"fondo_caja": 0.0})
    if not os.path.exists(APARTADOS_FILE):
        save_to_github(APARTADOS_FILE, [])

def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        if "caja" in filepath:
            return {"fondo_caja": 0.0}
        return []

def normalize_product(prod):
    if "Variantes" in prod and isinstance(prod["Variantes"], list):
        return prod
    
    tallas = prod.get("Talla", "M").split(",")
    tallas = [t.strip().upper() for t in tallas if t.strip()]
    colores = prod.get("Colores", ["Único"])
    if isinstance(colores, str):
        colores = [c.strip() for c in colores.split(",") if c.strip()]
        
    variantes = []
    for color in colores:
        stock_dict = {}
        for t in tallas:
            stock_dict[t] = {
                "exhibido": int(prod.get("Stock_Exhibido", 0)),
                "bodega": int(prod.get("Stock_Bodega", 0))
            }
        variantes.append({"color": color, "stock": stock_dict})
        
    return {
        "ID": prod.get("ID", f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        "Categoria": prod.get("Categoria", "General"),
        "Producto": prod.get("Producto", "Sin Nombre"),
        "Precio_Sugerido": float(prod.get("Precio_Sugerido", 0.0)),
        "Precio_Venta": float(prod.get("Precio_Venta", 0.0)),
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

# Carga inicial en Session State
if "productos" not in st.session_state:
    raw_prods = load_json(PRODUCTS_FILE)
    st.session_state.productos = [normalize_product(p) for p in raw_prods]
if "ventas" not in st.session_state:
    st.session_state.ventas = load_json(SALES_FILE)
if "categorias" not in st.session_state:
    st.session_state.categorias = load_json(CATEGORIES_FILE)
if "caja" not in st.session_state:
    st.session_state.caja = load_json(CAJA_FILE)
if "apartados" not in st.session_state:
    st.session_state.apartados = load_json(APARTADOS_FILE)
if "vista" not in st.session_state:
    st.session_state.vista = "ventas"
if "admin_tab" not in st.session_state:
    st.session_state.admin_tab = "add_product"
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

def sync_data():
    save_to_github(PRODUCTS_FILE, st.session_state.productos)
    save_to_github(SALES_FILE, st.session_state.ventas)
    save_to_github(CATEGORIES_FILE, st.session_state.categorias)
    save_to_github(CAJA_FILE, st.session_state.caja)
    save_to_github(APARTADOS_FILE, st.session_state.apartados)

def notificar(mensaje, tipo="success"):
    st.session_state["flash_msg"] = mensaje
    st.session_state["flash_type"] = tipo

# Mostrar mensajes persistentes tras rerun
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
    if st.button("🛒 Venta", use_container_width=True, type=btn_type):
        st.session_state.vista = "ventas"
        st.rerun()

with nav_c2:
    btn_type = "primary" if st.session_state.vista == "cambios" else "secondary"
    if st.button("🔄 Cambios", use_container_width=True, type=btn_type):
        st.session_state.vista = "cambios"
        st.rerun()

with nav_c3:
    btn_type = "primary" if st.session_state.vista == "apartados" else "secondary"
    if st.button("📑 Apartados", use_container_width=True, type=btn_type):
        st.session_state.vista = "apartados"
        st.rerun()

with nav_c4:
    btn_type = "primary" if st.session_state.vista == "ver_inventario" else "secondary"
    if st.button("📋 Inventario", use_container_width=True, type=btn_type):
        st.session_state.vista = "ver_inventario"
        st.rerun()

with nav_c5:
    btn_type = "primary" if st.session_state.vista == "caja" else "secondary"
    if st.button("💰 Caja", use_container_width=True, type=btn_type):
        st.session_state.vista = "caja"
        st.rerun()

with nav_c6:
    btn_type = "primary" if st.session_state.vista == "admin" else "secondary"
    if st.button("🔐 Admin", use_container_width=True, type=btn_type):
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
                                    "fecha": datetime.now().isoformat(),
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
# VISTA 2: CAMBIOS DE PRODUCTO / TALLA
# ==========================================
elif st.session_state.vista == "cambios":
    st.subheader("🔄 Devoluciones y Cambios de Prenda / Talla")

    if not st.session_state.productos:
        st.info("No hay productos registrados para realizar cambios.")
    else:
        st.markdown("#### 1. Prenda que Regresa el Cliente (Entrada al Inventario)")
        c_in1, c_in2, c_in3, c_in4, c_in5 = st.columns(5)
        
        prod_dict = {f"{p['Producto']} ({p['Categoria']})": p for p in st.session_state.productos}
        with c_in1:
            p_ret_name = st.selectbox("Producto devuelto:", list(prod_dict.keys()), key="ret_p")
            p_ret = prod_dict[p_ret_name]
        
        cols_ret = [v["color"] for v in p_ret.get("Variantes", [])] if p_ret.get("Variantes") else ["Único"]
        with c_in2:
            c_ret = st.selectbox("Color devuelto:", cols_ret, key="ret_c")
        with c_in3:
            t_ret = st.selectbox("Talla devuelta:", p_ret.get("Tallas", ["M"]), key="ret_t")
        with c_in4:
            cant_ret = st.number_input("Cantidad devuelta:", min_value=1, value=1, key="ret_cant")
        with c_in5:
            precio_ret = st.number_input("Valor pagado devuelto ($):", value=float(p_ret["Precio_Sugerido"]) * cant_ret, step=10.0, key="ret_prec")

        st.divider()

        st.markdown("#### 2. Prenda Nueva que se Lleva el Cliente (Salida del Inventario)")
        c_out1, c_out2, c_out3, c_out4, c_out5 = st.columns(5)
        with c_out1:
            p_new_name = st.selectbox("Producto nuevo:", list(prod_dict.keys()), key="new_p")
            p_new = prod_dict[p_new_name]
        
        cols_new = [v["color"] for v in p_new.get("Variantes", [])] if p_new.get("Variantes") else ["Único"]
        with c_out2:
            c_new = st.selectbox("Color nuevo:", cols_new, key="new_c")
        with c_out3:
            t_new = st.selectbox("Talla nueva:", p_new.get("Tallas", ["M"]), key="new_t")
        with c_out4:
            cant_new = st.number_input("Cantidad nueva:", min_value=1, value=1, key="new_cant")
        with c_out5:
            precio_new = st.number_input("Precio prenda nueva ($):", value=float(p_new["Precio_Sugerido"]) * cant_new, step=10.0, key="new_prec")

        var_new = next((v for v in p_new.get("Variantes", []) if v["color"] == c_new), None)
        stock_new_exh = var_new["stock"][t_new].get("exhibido", 0) if var_new and t_new in var_new.get("stock", {}) else 0
        stock_new_bod = var_new["stock"][t_new].get("bodega", 0) if var_new and t_new in var_new.get("stock", {}) else 0
        total_disp_new = stock_new_exh + stock_new_bod

        st.divider()
        st.markdown("#### 3. Ajuste de Dinero en Caja")

        diferencia = precio_new - precio_ret

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.write(f" Valor Devuelto: **${precio_ret:,.2f}**")
            st.write(f" Valor Nuevo: **${precio_new:,.2f}**")
            if diferencia > 0:
                st.success(f"🔴 **El cliente debe pagar una diferencia de: ${diferencia:,.2f}**")
            elif diferencia == 0:
                st.info("🟢 **Cambio exacto. No hay diferencia de dinero.**")
            else:
                st.warning(f"🟡 **Diferencia a favor del cliente: ${abs(diferencia):,.2f}**")

        with res_col2:
            if total_disp_new >= cant_new:
                if st.button("🔄 Procesar Cambio y Actualizar Inventario", type="primary", use_container_width=True):
                    var_ret = next((v for v in p_ret.get("Variantes", []) if v["color"] == c_ret), None)
                    if var_ret and t_ret in var_ret.get("stock", {}):
                        var_ret["stock"][t_ret]["exhibido"] += cant_ret

                    restante = cant_new
                    desc_e = min(stock_new_exh, restante)
                    var_new["stock"][t_new]["exhibido"] -= desc_e
                    restante -= desc_e
                    desc_b = min(stock_new_bod, restante)
                    var_new["stock"][t_new]["bodega"] -= desc_b

                    registro_cambio = {
                        "fecha": datetime.now().isoformat(),
                        "producto_id": p_new["ID"],
                        "producto": f"CAMBIO: Devuelve {p_ret['Producto']} ({c_ret}-{t_ret}) x Lleva {p_new['Producto']} ({c_new}-{t_new})",
                        "talla": t_new,
                        "color": c_new,
                        "cantidad": cant_new,
                        "precio_sugerido": precio_new,
                        "precio_venta": diferencia,
                        "categoria": p_new["Categoria"],
                        "ubicacion_venta": "Cambio de Prenda"
                    }
                    st.session_state.ventas.append(registro_cambio)
                    sync_data()
                    notificar("¡Cambio procesado con éxito! El inventario y la caja han sido actualizados.")
                    st.rerun()
            else:
                st.button("Stock insuficiente para prenda nueva", disabled=True, use_container_width=True)

# ==========================================
# VISTA 3: APARTADOS (LAYAWAY)
# ==========================================
elif st.session_state.vista == "apartados":
    st.subheader("📑 Gestión de Apartados")

    tab_ap1, tab_ap2 = st.tabs(["➕ Crear Nuevo Apartado", "📋 Lista de Apartados y Abonos"])

    with tab_ap1:
        st.markdown("#### Nuevo Registro de Apartado")
        
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            cliente_nombre = st.text_input("Nombre completo del cliente:", key="ap_nom")
        with c_a2:
            cliente_tel = st.text_input("Teléfono de contacto:", key="ap_tel")

        if st.session_state.productos:
            prod_dict_ap = {f"{p['Producto']} ({p['Categoria']})": p for p in st.session_state.productos}
            c_p1, c_p2, c_p3, c_p4 = st.columns(4)
            
            with c_p1:
                p_ap_name = st.selectbox("Producto a apartar:", list(prod_dict_ap.keys()), key="ap_p_sel")
                p_ap = prod_dict_ap[p_ap_name]
            
            cols_ap = [v["color"] for v in p_ap.get("Variantes", [])] if p_ap.get("Variantes") else ["Único"]
            with c_p2:
                c_ap_sel = st.selectbox("Color:", cols_ap, key="ap_c_sel")
            with c_p3:
                t_ap_sel = st.selectbox("Talla:", p_ap.get("Tallas", ["M"]), key="ap_t_sel")
            with c_p4:
                cant_ap = st.number_input("Cantidad de piezas:", min_value=1, value=1, key="ap_cant")

            var_ap = next((v for v in p_ap.get("Variantes", []) if v["color"] == c_ap_sel), None)
            s_e_ap = var_ap["stock"][t_ap_sel].get("exhibido", 0) if var_ap and t_ap_sel in var_ap.get("stock", {}) else 0
            s_b_ap = var_ap["stock"][t_ap_sel].get("bodega", 0) if var_ap and t_ap_sel in var_ap.get("stock", {}) else 0
            tot_disp_ap = s_e_ap + s_b_ap

            m_ap1, m_ap2 = st.columns(2)
            with m_ap1:
                precio_tot_ap = st.number_input("Precio Total del Apartado ($):", value=float(p_ap["Precio_Sugerido"]) * cant_ap, step=10.0, key="ap_prec_tot")
            with m_ap2:
                abono_ini = st.number_input("Abono Inicial recibido ($):", min_value=0.0, max_value=float(precio_tot_ap), value=min(100.0, float(precio_tot_ap)), step=10.0, key="ap_ab_ini")

            saldo_pend = precio_tot_ap - abono_ini
            st.info(f"Saldo Pendiente que resta pagar: **${saldo_pend:,.2f}** | Stock disponible: **{tot_disp_ap} pieza(s)**")

            if tot_disp_ap >= cant_ap:
                if st.button("💾 Guardar Apartado y Descontar Stock", type="primary"):
                    if not cliente_nombre:
                        st.error("Ingresa el nombre del cliente.")
                    else:
                        restante = cant_ap
                        desc_e = min(s_e_ap, restante)
                        var_ap["stock"][t_ap_sel]["exhibido"] -= desc_e
                        restante -= desc_e
                        desc_b = min(s_b_ap, restante)
                        var_ap["stock"][t_ap_sel]["bodega"] -= desc_b

                        nuevo_apartado = {
                            "id": f"AP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            "fecha": datetime.now().isoformat(),
                            "cliente": cliente_nombre,
                            "telefono": cliente_tel,
                            "producto": p_ap["Producto"],
                            "color": c_ap_sel,
                            "talla": t_ap_sel,
                            "cantidad": cant_ap,
                            "precio_total": precio_tot_ap,
                            "abono_inicial": abono_ini,
                            "saldo_pendiente": saldo_pend,
                            "estado": "Pendiente" if saldo_pend > 0 else "Entregado",
                            "historial_abonos": [{"fecha": datetime.now().isoformat(), "monto": abono_ini}]
                        }
                        st.session_state.apartados.append(nuevo_apartado)

                        if abono_ini > 0:
                            ingreso_caja = {
                                "fecha": datetime.now().isoformat(),
                                "producto_id": p_ap["ID"],
                                "producto": f"ABONO APARTADO: {cliente_nombre} ({p_ap['Producto']})",
                                "talla": t_ap_sel,
                                "color": c_ap_sel,
                                "cantidad": cant_ap,
                                "precio_sugerido": abono_ini,
                                "precio_venta": abono_ini,
                                "categoria": p_ap["Categoria"],
                                "ubicacion_venta": "Apartado"
                            }
                            st.session_state.ventas.append(ingreso_caja)

                        sync_data()
                        notificar(f"¡Apartado de {cliente_nombre} registrado correctamente!")
                        st.rerun()
            else:
                st.button("Stock insuficiente para apartar", disabled=True)

    with tab_ap2:
        st.markdown("#### Lista de Apartados")
        if not st.session_state.apartados:
            st.info("No hay apartados registrados.")
        else:
            df_ap = pd.DataFrame(st.session_state.apartados)
            busq_ap = st.text_input("🔍 Buscar apartado por Cliente o Teléfono:", placeholder="Ej: María...")
            
            if busq_ap:
                df_ap_show = df_ap[df_ap['cliente'].str.lower().str.contains(busq_ap.lower()) | df_ap['telefono'].str.contains(busq_ap)]
            else:
                df_ap_show = df_ap

            for idx, item in df_ap_show.iterrows():
                estado_color = "🟢 Entregado" if item["estado"] == "Entregado" else "🔴 Pendiente"
                with st.expander(f"👤 **{item['cliente']}** | {item['producto']} ({item['color']}-{item['talla']}) | {estado_color}", expanded=True):
                    ap_c1, ap_c2, ap_c3, ap_c4 = st.columns(4)
                    ap_c1.write(f"**Teléfono:** {item['telefono']}")
                    ap_c2.write(f"**Total:** ${item['precio_total']:,.2f}")
                    ap_c3.write(f"**Abonado:** ${(item['precio_total'] - item['saldo_pendiente']):,.2f}")
                    ap_c4.write(f"**Saldo Restante:** ${item['saldo_pendiente']:,.2f}")

                    if item["saldo_pendiente"] > 0:
                        st.markdown("##### 💵 Registrar Nuevo Abono")
                        ab_col1, ab_col2 = st.columns([2, 2])
                        with ab_col1:
                            monto_abono = st.number_input(
                                "Monto a abonar ($):", 
                                min_value=1.0, 
                                max_value=float(item['saldo_pendiente']), 
                                value=float(item['saldo_pendiente']), 
                                key=f"ab_input_{item['id']}"
                            )
                        with ab_col2:
                            st.write("")
                            st.write("")
                            if st.button("Abonar", key=f"btn_ab_{item['id']}", type="primary"):
                                item["saldo_pendiente"] -= monto_abono
                                item["historial_abonos"].append({"fecha": datetime.now().isoformat(), "monto": monto_abono})
                                if item["saldo_pendiente"] <= 0:
                                    item["estado"] = "Entregado"

                                venta_abono = {
                                    "fecha": datetime.now().isoformat(),
                                    "producto_id": item['id'],
                                    "producto": f"ABONO APARTADO: {item['cliente']} ({item['producto']})",
                                    "talla": item['talla'],
                                    "color": item['color'],
                                    "cantidad": 1,
                                    "precio_sugerido": monto_abono,
                                    "precio_venta": monto_abono,
                                    "categoria": "Apartados",
                                    "ubicacion_venta": "Abono"
                                }
                                st.session_state.ventas.append(venta_abono)
                                sync_data()
                                notificar(f"Abono de ${monto_abono:,.2f} registrado para {item['cliente']}.")
                                st.rerun()

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
    st.subheader("💰 Corte de Caja y Ventas Diarias")
    
    fondo = st.session_state.caja.get("fondo_caja", 0.0)
    
    if st.session_state.ventas:
        df_v = pd.DataFrame(st.session_state.ventas)
        df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'])
        hoy = datetime.now().date()
        ventas_hoy = df_v[df_v['fecha_dt'].dt.date == hoy]
        
        total_ventas_hoy = ventas_hoy['precio_venta'].sum() if not ventas_hoy.empty else 0.0
        total_sugerido_hoy = ventas_hoy['precio_sugerido'].sum() if not ventas_hoy.empty else 0.0
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
    k2.metric("Ventas / Entradas de Hoy", f"${total_ventas_hoy:,.2f}")
    k3.metric("Total Esperado en Caja", f"${(fondo + total_ventas_hoy):,.2f}")
    k4.metric("Descuentos / Regateo", f"-${regateo_hoy:,.2f}")

    st.caption(f"Piezas vendidas / Movimientos hoy: **{cant_piezas_hoy}**")

    st.divider()

    st.markdown("### 🌅 Cierre de Caja / Preparar Día Siguiente")
    
    if st.session_state.get("admin_authenticated", False):
        with st.expander("🔑 Realizar Corte de Caja y Ajustar Fondo de Mañana", expanded=False):
            st.info("Esta acción conserva **todo** el historial de ventas anteriores intacto para tus consultas y exportaciones a Excel.")
            nuevo_fondo_input = st.number_input(
                "Monto de Fondo de Caja para el día siguiente ($):", 
                value=float(fondo),
                step=50.0,
                key="cierre_nuevo_fondo"
            )
            confirmar_cierre = st.checkbox("Confirmo que deseo realizar el corte de caja y fijar el nuevo fondo inicial.")
            
            if st.button("🔒 Realizar Corte de Caja y Reiniciar Día", type="primary"):
                if confirmar_cierre:
                    st.session_state.caja["fondo_caja"] = nuevo_fondo_input
                    sync_data()
                    notificar(f"¡Corte de caja realizado con éxito! Fondo fijado en ${nuevo_fondo_input:,.2f}. El historial de días anteriores sigue guardado.")
                    st.rerun()
                else:
                    st.error("Por favor marca la casilla de confirmación antes de continuar.")
    else:
        st.info("🔒 *La modificación del fondo de caja y la realización del corte diario están reservadas exclusivamente para la Administradora con contraseña.*")

    st.divider()

    st.markdown("### 📊 Historial de Ventas y Descarga en Excel")

    tab_hoy, tab_hist = st.tabs(["📅 Ventas del Día de Hoy", "📜 Historial de Días Anteriores / Completo"])

    with tab_hoy:
        if not ventas_hoy.empty:
            st.dataframe(
                ventas_hoy[['fecha', 'producto', 'categoria', 'talla', 'color', 'cantidad', 'precio_sugerido', 'precio_venta', 'ubicacion_venta']], 
                use_container_width=True
            )
            bytes_data_hoy, ext_h, mime_h = generar_excel_seguro(ventas_hoy, "Ventas_Hoy")
            st.download_button(
                label=f"📥 Descargar Ventas del Día en Excel ({ext_h.upper()})",
                data=bytes_data_hoy,
                file_name=f"Ventas_Hoy_{datetime.now().strftime('%Y%m%d')}.{ext_h}",
                mime=mime_h
            )
        else:
            st.info("Aún no hay ventas registradas el día de hoy.")

    with tab_hist:
        if not df_v.empty:
            st.markdown("##### Filtrar Registros")
            fechas_disponibles = sorted(df_v['fecha_dt'].dt.date.unique(), reverse=True)
            
            filtro_fecha = st.multiselect(
                "Selecciona día(s) específico(s) (deja vacío para ver todo el historial acumulado):",
                options=fechas_disponibles,
                format_func=lambda d: d.strftime("%d/%m/%Y")
            )

            if filtro_fecha:
                df_filtrado = df_v[df_v['fecha_dt'].dt.date.isin(filtro_fecha)]
            else:
                df_filtrado = df_v

            st.dataframe(
                df_filtrado[['fecha', 'producto', 'categoria', 'talla', 'color', 'cantidad', 'precio_sugerido', 'precio_venta', 'ubicacion_venta']], 
                use_container_width=True
            )

            bytes_data_hist, ext_hist, mime_hist = generar_excel_seguro(df_filtrado, "Historial_Ventas")
            st.download_button(
                label=f"📥 Descargar Ventas Filtradas/Histórico Completo ({ext_hist.upper()})",
                data=bytes_data_hist,
                file_name=f"Ventas_Historico_{datetime.now().strftime('%Y%m%d')}.{ext_hist}",
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
                            "ID": f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
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
                    file_name=f"Inventario_{datetime.now().strftime('%Y%m%d')}.{ext}",
                    mime=mime
                )
            else:
                st.info("No hay datos en el inventario para descargar.")
