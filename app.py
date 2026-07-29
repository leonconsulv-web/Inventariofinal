import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px
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

DEFAULT_CATEGORIES = [
    "Chamarras", "Jeans", "Playeras", "Camisas", 
    "Suéteres", "Shorts", "Niño", "Bermudas", "Sacos", "Trajes"
]

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
        save_json(CAJA_FILE, {"fondo_caja": 0.0})

def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [] if "caja" not in filepath else {"fondo_caja": 0.0}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_product(prod):
    """Garantiza compatibilidad con esquemas anteriores."""
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

init_storage()

# Carga en Session State
if "productos" not in st.session_state:
    raw_prods = load_json(PRODUCTS_FILE)
    st.session_state.productos = [normalize_product(p) for p in raw_prods]
if "ventas" not in st.session_state:
    st.session_state.ventas = load_json(SALES_FILE)
if "categorias" not in st.session_state:
    st.session_state.categorias = load_json(CATEGORIES_FILE)
if "caja" not in st.session_state:
    st.session_state.caja = load_json(CAJA_FILE)
if "vista" not in st.session_state:
    st.session_state.vista = "ventas"
if "admin_tab" not in st.session_state:
    st.session_state.admin_tab = "add_product"
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

def sync_data():
    save_json(PRODUCTS_FILE, st.session_state.productos)
    save_json(SALES_FILE, st.session_state.ventas)
    save_json(CATEGORIES_FILE, st.session_state.categorias)
    save_json(CAJA_FILE, st.session_state.caja)

# ==========================================
# NAVEGACIÓN PRINCIPAL (BOCETO 1)
# ==========================================
st.title("Inventario de Ropa")

nav_c1, nav_c2, nav_c3 = st.columns(3)
with nav_c1:
    btn_type = "primary" if st.session_state.vista == "ventas" else "secondary"
    if st.button("🛒 Registrar Venta", use_container_width=True, type=btn_type):
        st.session_state.vista = "ventas"
        st.rerun()

with nav_c2:
    btn_type = "primary" if st.session_state.vista == "caja" else "secondary"
    if st.button("💰 Corte de Caja y Ventas Diarias", use_container_width=True, type=btn_type):
        st.session_state.vista = "caja"
        st.rerun()

with nav_c3:
    btn_type = "primary" if st.session_state.vista == "admin" else "secondary"
    if st.button("🔐 Modo Administrador", use_container_width=True, type=btn_type):
        st.session_state.vista = "admin"
        st.rerun()

st.divider()

# ==========================================
# VISTA 1: REGISTRAR VENTAS (BOCETO 2)
# ==========================================
if st.session_state.vista == "ventas":
    st.subheader("Registrar Ventas")
    
    if not st.session_state.categorias:
        st.info("No hay categorías creadas.")
    else:
        # Botones por categoría
        cat_cols = st.columns(min(len(st.session_state.categorias), 5))
        if "cat_activa" not in st.session_state:
            st.session_state.cat_activa = st.session_state.categorias[0]

        for idx, cat in enumerate(st.session_state.categorias):
            with cat_cols[idx % len(cat_cols)]:
                b_type = "primary" if st.session_state.cat_activa == cat else "secondary"
                if st.button(cat, key=f"btn_cat_{cat}", use_container_width=True, type=b_type):
                    st.session_state.cat_activa = cat
                    st.rerun()

        st.caption(f"Productos en categoría: **{st.session_state.cat_activa}**")

        prods_cat = [p for p in st.session_state.productos if p["Categoria"] == st.session_state.cat_activa]
        
        if not prods_cat:
            st.warning("No hay productos registrados en esta categoría.")
        else:
            for prod in prods_cat:
                with st.expander(f"📦 **{prod['Producto']}** | Precio Sugerido: ${prod['Precio_Sugerido']:.2f}", expanded=True):
                    c_col1, c_col2 = st.columns(2)
                    
                    # Selección de variante/color
                    nombres_colores = [v["color"] for v in prod["Variantes"]]
                    with c_col1:
                        color_sel = st.selectbox("Color:", nombres_colores, key=f"sel_col_{prod['ID']}")
                    
                    # Selección de talla
                    with c_col2:
                        talla_sel = st.selectbox("Talla:", prod["Tallas"], key=f"sel_tal_{prod['ID']}")

                    # Buscar inventario de esa variante y talla
                    variante_actual = next((v for v in prod["Variantes"] if v["color"] == color_sel), None)
                    stock_exh = 0
                    stock_bod = 0
                    if variante_actual and talla_sel in variante_actual["stock"]:
                        stock_exh = variante_actual["stock"][talla_sel].get("exhibido", 0)
                        stock_bod = variante_actual["stock"][talla_sel].get("bodega", 0)

                    # Mostrar stock
                    s_col1, s_col2 = st.columns(2)
                    s_col1.metric("Stock en Vitrina / Exhibición", stock_exh)
                    s_col2.metric("Stock en Bodega", stock_bod)

                    # Formulario de venta
                    col_p1, col_p2, col_p3 = st.columns([2, 2, 2])
                    with col_p1:
                        precio_real = st.number_input(
                            "Precio de Venta Real ($):", 
                            value=float(prod["Precio_Sugerido"]), 
                            step=10.0, 
                            key=f"p_real_{prod['ID']}"
                        )
                    
                    with col_p2:
                        if stock_exh > 0 or stock_bod > 0:
                            if st.button("🛒 Vender 1 Unidad", key=f"vender_{prod['ID']}", type="primary", use_container_width=True):
                                # Descontar primero de exhibición
                                ubic_venta = ""
                                if stock_exh > 0:
                                    variante_actual["stock"][talla_sel]["exhibido"] -= 1
                                    ubic_venta = "Vitrina"
                                else:
                                    variante_actual["stock"][talla_sel]["bodega"] -= 1
                                    ubic_venta = "Bodega"

                                # Registrar la venta
                                nueva_venta = {
                                    "fecha": datetime.now().isoformat(),
                                    "producto_id": prod["ID"],
                                    "producto": prod["Producto"],
                                    "talla": talla_sel,
                                    "color": color_sel,
                                    "precio_sugerido": prod["Precio_Sugerido"],
                                    "precio_venta": precio_real,
                                    "categoria": prod["Categoria"],
                                    "ubicacion_venta": ubic_venta
                                }
                                st.session_state.ventas.append(nueva_venta)
                                sync_data()
                                st.success(f"¡Venta realizada ({color_sel} - Talla {talla_sel})! Descontado de {ubic_venta}.")
                                st.rerun()
                        else:
                            st.button("Agotado", disabled=True, use_container_width=True, key=f"dis_{prod['ID']}")

                    with col_p3:
                        if stock_bod > 0:
                            if st.button("📦 Pasante de Bodega ➔ Vitrina", key=f"pass_{prod['ID']}", use_container_width=True):
                                variante_actual["stock"][talla_sel]["bodega"] -= 1
                                variante_actual["stock"][talla_sel]["exhibido"] += 1
                                sync_data()
                                st.success("Stock movido a Vitrina.")
                                st.rerun()

# ==========================================
# VISTA 2: CORTE DE CAJA Y VENTAS DIARIAS
# ==========================================
elif st.session_state.vista == "caja":
    st.subheader("Corte de Caja y Ventas Diarias")
    
    with st.expander("💵 Configurar Fondo de Caja Inicial", expanded=False):
        c_f1, c_f2 = st.columns([3, 1])
        with c_f1:
            nuevo_fondo = st.number_input(
                "Fondo Inicial de Caja ($):", 
                value=float(st.session_state.caja.get("fondo_caja", 0.0)),
                step=50.0
            )
        with c_f2:
            st.write("")
            st.write("")
            if st.button("Guardar Fondo"):
                st.session_state.caja["fondo_caja"] = nuevo_fondo
                sync_data()
                st.success("Fondo actualizado.")
                st.rerun()

    fondo = st.session_state.caja.get("fondo_caja", 0.0)
    
    if st.session_state.ventas:
        df_v = pd.DataFrame(st.session_state.ventas)
        df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'])
        hoy = datetime.now().date()
        ventas_hoy = df_v[df_v['fecha_dt'].dt.date == hoy]
        
        total_ventas = ventas_hoy['precio_venta'].sum() if not ventas_hoy.empty else 0.0
        total_sugerido = ventas_hoy['precio_sugerido'].sum() if not ventas_hoy.empty else 0.0
        regateo = total_sugerido - total_ventas
    else:
        df_v = pd.DataFrame()
        total_ventas = 0.0
        regateo = 0.0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Fondo Inicial", f"${fondo:,.2f}")
    k2.metric("Ventas de Hoy", f"${total_ventas:,.2f}")
    k3.metric("Total en Caja Esperado", f"${(fondo + total_ventas):,.2f}")
    k4.metric("Diferencia por Regateo", f"-${regateo:,.2f}")

    st.divider()
    st.subheader("Historial de Ventas")
    if not df_v.empty:
        st.dataframe(
            df_v[['fecha', 'producto', 'categoria', 'talla', 'color', 'precio_sugerido', 'precio_venta', 'ubicacion_venta']], 
            use_container_width=True
        )
    else:
        st.info("Sin registros de ventas.")

# ==========================================
# VISTA 3: MODO ADMINISTRADOR (BOCETOS 3 Y 4)
# ==========================================
elif st.session_state.vista == "admin":
    st.subheader("Modo Administrador y Gestión")

    # Autenticación de contraseña
    if not st.session_state.admin_authenticated:
        pwd = st.text_input("Ingrese Contraseña de Administradora:", type="password")
        if st.button("Ingresar"):
            if pwd == "michiotaku":
                st.session_state.admin_authenticated = True
                st.success("Acceso concedido.")
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    else:
        # Sub-menú navegación administrador (Boceto 3)
        ad_col1, ad_col2, ad_col3, ad_col4, ad_col5 = st.columns(5)
        
        with ad_col1:
            if st.button("🏷️ Editar Categorías", use_container_width=True):
                st.session_state.admin_tab = "categorias"
        with ad_col2:
            if st.button("➕ Añadir Producto", use_container_width=True):
                st.session_state.admin_tab = "add_product"
        with ad_col3:
            if st.button("✏️ Editar Productos", use_container_width=True):
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
                        st.success("Categoría agregada.")
                        st.rerun()
            with c_del:
                cat_del = st.selectbox("Eliminar Categoría:", st.session_state.categorias)
                if st.button("Eliminar"):
                    st.session_state.categorias.remove(cat_del)
                    sync_data()
                    st.success("Categoría eliminada.")
                    st.rerun()

        # TAB 2: AÑADIR PRODUCTO (BOCETO 4 EXACTO)
        elif st.session_state.admin_tab == "add_product":
            st.markdown("### AÑADIR PRODUCTO")
            
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                cat_sel = st.selectbox("Categoría", st.session_state.categorias)
            with f_col2:
                nombre_prod = st.text_input("Nombre producto", placeholder="Ej: Café repelente / Sacos Slim")

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                p_sugerido = st.number_input("Precio Sugerido ($)", min_value=0.0, value=0.0, step=10.0)
            with p_col2:
                p_venta = st.number_input("Precio Venta Base ($)", min_value=0.0, value=0.0, step=10.0)

            # Tallas disponibles
            tallas_input = st.text_input(
                "Tallas disponibles (separadas por coma):", 
                value="CH, M, G, XG", 
                help="Escribe las tallas separadas por comas."
            )
            st.caption("🔴 * Depende de las que ponga se habilitan esos por color.")

            # Lista de tallas parseada
            lista_tallas = [t.strip().upper() for t in tallas_input.split(",") if t.strip()]

            if "num_colores" not in st.session_state:
                st.session_state.num_colores = 1

            variantes_capturadas = []

            st.divider()
            st.markdown("#### Configuración de Colores e Inventario")

            for i in range(st.session_state.num_colores):
                st.markdown(f"🎨 **Color #{i+1}**")
                color_name = st.text_input(f"Nombre del Color #{i+1}:", key=f"c_name_{i}")
                
                # Stock Vitrina
                st.write("🟦 **Stock en Vitrina / Exhibición**")
                cols_v = st.columns(len(lista_tallas) if lista_tallas else 1)
                vitrina_stock = {}
                for idx, t in enumerate(lista_tallas):
                    with cols_v[idx]:
                        val_v = st.number_input(f"V {t}", min_value=0, value=0, key=f"v_{i}_{t}")
                        vitrina_stock[t] = val_v

                # Stock Bodega
                st.write("🟫 **Stock en Bodega**")
                cols_b = st.columns(len(lista_tallas) if lista_tallas else 1)
                bodega_stock = {}
                for idx, t in enumerate(lista_tallas):
                    with cols_b[idx]:
                        val_b = st.number_input(f"B {t}", min_value=0, value=0, key=f"b_{i}_{t}")
                        bodega_stock[t] = val_b

                # Empaquetar variante
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
                if st.button("➕ Agregar Color"):
                    st.session_state.num_colores += 1
                    st.rerun()

            with btn_col2:
                if st.button("💾 Guardar Producto", type="primary"):
                    if not nombre_prod or not lista_tallas:
                        st.error("Por favor ingresa el nombre del producto y al menos una talla.")
                    else:
                        nuevo_p = {
                            "ID": f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            "Categoria": cat_sel,
                            "Producto": nombre_prod,
                            "Precio_Sugerido": p_sugerido,
                            "Precio_Venta": p_venta,
                            "Tallas": lista_tallas,
                            "Variantes": variantes_capturadas
                        }
                        st.session_state.productos.append(nuevo_p)
                        sync_data()
                        st.session_state.num_colores = 1
                        st.success("¡Producto registrado con éxito!")
                        st.rerun()

        # TAB 3: EDITAR PRODUCTOS
        elif st.session_state.admin_tab == "edit_product":
            st.markdown("### Editar Productos")
            if not st.session_state.productos:
                st.info("Sin productos registrados.")
            else:
                prod_opts = {p["Producto"]: p["ID"] for p in st.session_state.productos}
                p_sel_name = st.selectbox("Seleccione Producto a Editar:", list(prod_opts.keys()))
                prod_obj = next(p for p in st.session_state.productos if p["ID"] == prod_opts[p_sel_name])

                with st.form("form_edit"):
                    n_nombre = st.text_input("Nombre Producto", value=prod_obj["Producto"])
                    n_sug = st.number_input("Precio Sugerido", value=float(prod_obj["Precio_Sugerido"]))
                    n_ven = st.number_input("Precio Venta Base", value=float(prod_obj["Precio_Venta"]))
                    
                    if st.form_submit_button("Actualizar"):
                        prod_obj["Producto"] = n_nombre
                        prod_obj["Precio_Sugerido"] = n_sug
                        prod_obj["Precio_Venta"] = n_ven
                        sync_data()
                        st.success("Producto actualizado.")
                        st.rerun()

        # TAB 4: ELIMINAR PRODUCTO
        elif st.session_state.admin_tab == "delete_product":
            st.markdown("### Eliminar Producto")
            if not st.session_state.productos:
                st.info("Sin productos registrados.")
            else:
                prod_opts = {p["Producto"]: p["ID"] for p in st.session_state.productos}
                p_del_name = st.selectbox("Seleccione Producto a Eliminar:", list(prod_opts.keys()))
                if st.button("Confirmar Eliminar", type="primary"):
                    st.session_state.productos = [p for p in st.session_state.productos if p["ID"] != prod_opts[p_del_name]]
                    sync_data()
                    st.success("Producto eliminado.")
                    st.rerun()

        # TAB 5: DESCARGAR INVENTARIO
        elif st.session_state.admin_tab == "export":
            st.markdown("### Descargar Inventario")
            if st.session_state.productos:
                buffer = io.BytesIO()
                df_export = pd.DataFrame(st.session_state.productos)
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_export.to_excel(writer, sheet_name='Inventario', index=False)
                
                st.download_button(
                    label="📥 Descargar Inventario en Excel",
                    data=buffer.getvalue(),
                    file_name=f"Inventario_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
