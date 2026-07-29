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
    page_title="Gestión de Inventario - Tienda de Ropa",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# RUTAS DE ARCHIVOS Y PERSISTENCIA DE DATOS
# ==========================================
DATA_DIR = "data"
PRODUCTS_FILE = os.path.join(DATA_DIR, "inventario.json")
SALES_FILE = os.path.join(DATA_DIR, "ventas.json")
CATEGORIES_FILE = os.path.join(DATA_DIR, "categorias.json")
CAJA_FILE = os.path.join(DATA_DIR, "caja.json")

DEFAULT_CATEGORIES = [
    "Camisas", "Playeras", "Suéteres", "Chamarras", 
    "Pantalones", "Shorts", "Jeans", "Niño", "Bermudas", "Sacos", "Trajes"
]

def init_storage():
    """Inicializa la estructura de directorios y archivos si no existen."""
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

init_storage()

# Carga de datos en Session State para rendimiento fluido
if "productos" not in st.session_state:
    st.session_state.productos = load_json(PRODUCTS_FILE)
if "ventas" not in st.session_state:
    st.session_state.ventas = load_json(SALES_FILE)
if "categorias" not in st.session_state:
    st.session_state.categorias = load_json(CATEGORIES_FILE)
if "caja" not in st.session_state:
    st.session_state.caja = load_json(CAJA_FILE)

def sync_data():
    """Guarda el estado actual en los archivos JSON."""
    save_json(PRODUCTS_FILE, st.session_state.productos)
    save_json(SALES_FILE, st.session_state.ventas)
    save_json(CATEGORIES_FILE, st.session_state.categorias)
    save_json(CAJA_FILE, st.session_state.caja)

# ==========================================
# BARRA LATERAL (ROL Y AUTENTICACIÓN)
# ==========================================
st.sidebar.title("Sistema de Gestión")
rol = st.sidebar.radio("Seleccione Rol de Usuario:", ["Trabajadora", "Administradora"])

admin_autenticado = False

if rol == "Administradora":
    password = st.sidebar.text_input("Contraseña de Administradora:", type="password")
    if password == "michiotaku":
        admin_autenticado = True
        st.sidebar.success("Acceso Administradora Concedido")
    elif password != "":
        st.sidebar.error("Contraseña Incorrecta")

st.sidebar.divider()
st.sidebar.caption("Tienda de Ropa para Caballero v1.2")

# ==========================================
# MÓDULO: REGISTRO DE VENTAS (PUNTO DE VENTA)
# ==========================================
def modulo_ventas():
    st.header("Punto de Venta")
    
    if not st.session_state.productos:
        st.info("No hay productos registrados en el inventario.")
        return

    # Botones de filtrado por categoría
    cats = st.session_state.categorias
    col_count = 4
    cols = st.columns(col_count)
    
    if "cat_seleccionada" not in st.session_state:
        st.session_state.cat_seleccionada = cats[0] if cats else "Todas"

    for i, cat in enumerate(cats):
        with cols[i % col_count]:
            if st.button(cat, use_container_width=True, key=f"btn_cat_{cat}"):
                st.session_state.cat_seleccionada = cat

    st.subheader(f"Categoría: {st.session_state.cat_seleccionada}")
    
    # Filtrar productos disponibles
    prods_filtrados = [
        p for p in st.session_state.productos 
        if p["Categoria"] == st.session_state.cat_seleccionada and p["Stock_Total"] > 0
    ]
    
    if not prods_filtrados:
        st.warning("No hay productos disponibles en esta categoría.")
        return

    # Visualización de productos en rejilla
    grid_cols = st.columns(2)
    for index, prod in enumerate(prods_filtrados):
        with grid_cols[index % 2]:
            with st.expander(f"**{prod['Producto']}** | Talla: {prod['Talla']} | Sugg: ${prod['Precio_Sugerido']:.2f}", expanded=True):
                st.write(f"**Stock Exhibido:** {prod['Stock_Exhibido']} | **Stock Bodega:** {prod['Stock_Bodega']}")
                
                # Indicadores de estado de stock
                if prod['Stock_Total'] < 3:
                    st.error("¡Stock Crítico! Quedan menos de 3 unidades en total.")
                elif prod['Stock_Exhibido'] == 0:
                    st.warning("⚠️ Agotado en Exhibición (Queda stock en Bodega).")

                # BOTONES RÁPIDOS PARA MOVER STOCK
                col_mov1, col_mov2 = st.columns(2)
                with col_mov1:
                    if prod['Stock_Bodega'] > 0:
                        if st.button("📦 Mover a Exhibido (+1)", key=f"mov_exh_{prod['ID']}", use_container_width=True):
                            prod['Stock_Bodega'] -= 1
                            prod['Stock_Exhibido'] += 1
                            sync_data()
                            st.success("1 unidad movida a Exhibido.")
                            st.rerun()
                    else:
                        st.button("📦 Mover a Exhibido (+1)", key=f"mov_exh_{prod['ID']}", disabled=True, use_container_width=True)

                with col_mov2:
                    if prod['Stock_Exhibido'] > 0:
                        if st.button("🏷️ Mover a Bodega (+1)", key=f"mov_bod_{prod['ID']}", use_container_width=True):
                            prod['Stock_Exhibido'] -= 1
                            prod['Stock_Bodega'] += 1
                            sync_data()
                            st.success("1 unidad movida a Bodega.")
                            st.rerun()
                    else:
                        st.button("🏷️ Mover a Bodega (+1)", key=f"mov_bod_{prod['ID']}", disabled=True, use_container_width=True)

                st.divider()

                col_a, col_b = st.columns(2)
                
                with col_a:
                    colores_list = prod["Colores"] if isinstance(prod["Colores"], list) else [c.strip() for c in prod["Colores"].split(",")]
                    color_sel = st.selectbox("Color:", colores_list, key=f"col_{prod['ID']}")
                
                with col_b:
                    precio_real = st.number_input(
                        "Precio Final ($):", 
                        value=float(prod["Precio_Sugerido"]), 
                        step=10.0, 
                        key=f"prec_{prod['ID']}"
                    )

                if st.button("Vender 1 Unidad", key=f"sell_{prod['ID']}", type="primary", use_container_width=True):
                    ubicacion_descuento = ""
                    if prod["Stock_Exhibido"] > 0:
                        prod["Stock_Exhibido"] -= 1
                        ubicacion_descuento = "Exhibido"
                    elif prod["Stock_Bodega"] > 0:
                        prod["Stock_Bodega"] -= 1
                        ubicacion_descuento = "Bodega"
                    else:
                        st.error("Sin stock disponible para vender.")
                        st.stop()
                    
                    prod["Stock_Total"] = prod["Stock_Bodega"] + prod["Stock_Exhibido"]
                    prod["Ventas_Total"] = prod.get("Ventas_Total", 0) + 1

                    nueva_venta = {
                        "fecha": datetime.now().isoformat(),
                        "producto_id": prod["ID"],
                        "producto": prod["Producto"],
                        "talla": prod["Talla"],
                        "color": color_sel,
                        "precio_sugerido": prod["Precio_Sugerido"],
                        "precio_venta": precio_real,
                        "categoria": prod["Categoria"],
                        "ubicacion_venta": ubicacion_descuento
                    }
                    
                    st.session_state.ventas.append(nueva_venta)
                    sync_data()
                    st.success(f"¡Venta registrada! Se descontó de {ubicacion_descuento}.")
                    st.rerun()

# ==========================================
# MÓDULO: CONTROL Y MOVIMIENTO DE STOCK
# ==========================================
def modulo_movimiento_stock():
    st.header("Transferencia Masiva de Stock (Bodega ↔ Exhibido)")
    
    if not st.session_state.productos:
        st.info("No hay productos disponibles.")
        return

    df_p = pd.DataFrame(st.session_state.productos)
    prod_options = {f"{r['Producto']} - Talla: {r['Talla']} (ID: {r['ID']})": r['ID'] for _, r in df_p.iterrows()}
    
    selected_label = st.selectbox("Seleccionar Producto:", list(prod_options.keys()))
    prod_id = prod_options[selected_label]
    
    prod = next(p for p in st.session_state.productos if p["ID"] == prod_id)
    
    col1, col2 = st.columns(2)
    col1.metric("Stock en Bodega", prod["Stock_Bodega"])
    col2.metric("Stock en Exhibido", prod["Stock_Exhibido"])
    
    direccion = st.radio("Dirección del movimiento:", ["De Bodega a Exhibido", "De Exhibido a Bodega"])
    cantidad = st.number_input("Cantidad a mover:", min_value=1, value=1, step=1)
    
    if st.button("Ejecutar Transferencia"):
        if direccion == "De Bodega a Exhibido":
            if prod["Stock_Bodega"] >= cantidad:
                prod["Stock_Bodega"] -= cantidad
                prod["Stock_Exhibido"] += cantidad
                sync_data()
                st.success("Stock transferido a Exhibido.")
                st.rerun()
            else:
                st.error("Cantidad insuficiente en Bodega.")
        else:
            if prod["Stock_Exhibido"] >= cantidad:
                prod["Stock_Exhibido"] -= cantidad
                prod["Stock_Bodega"] += cantidad
                sync_data()
                st.success("Stock transferido a Bodega.")
                st.rerun()
            else:
                st.error("Cantidad insuficiente en Exhibido.")

# ==========================================
# MÓDULO: GESTIÓN DE PRODUCTOS (ADMIN)
# ==========================================
def modulo_gestion_productos():
    st.header("Gestión Completa de Productos")
    
    accion = st.radio("Acción:", ["Agregar Producto", "Editar Producto", "Eliminar Producto"], horizontal=True)
    
    if accion == "Agregar Producto":
        st.subheader("Nuevo Producto")
        with st.form("form_add_product"):
            categoria = st.selectbox("Categoría", st.session_state.categorias)
            nombre = st.text_input("Nombre del Producto (Ej: Sacos Slim Fit)")
            talla = st.text_input("Tallas disponibles (Ej: S, M, L o 32, 34, 36)")
            colores_str = st.text_area("Colores (separados por comas)", help="Ej: Azul Marino, Negro, Gris Claro")
            
            c1, c2 = st.columns(2)
            stock_bodega = c1.number_input("Stock Inicial Bodega", min_value=0, value=0)
            stock_exhibido = c2.number_input("Stock Inicial Exhibido", min_value=0, value=0)
            
            c3, c4 = st.columns(2)
            precio_sugerido = c3.number_input("Precio Sugerido ($)", min_value=0.0, value=0.0, step=10.0)
            precio_venta = c4.number_input("Precio Venta Base ($)", min_value=0.0, value=0.0, step=10.0)
            
            submitted = st.form_submit_button("Guardar Producto")
            if submitted:
                if not nombre or not talla or not colores_str:
                    st.error("Por favor completa los campos obligatorios.")
                else:
                    colores_list = [c.strip() for c in colores_str.split(",") if c.strip()]
                    nuevo_id = f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    nuevo_prod = {
                        "ID": nuevo_id,
                        "Categoria": categoria,
                        "Producto": nombre,
                        "Talla": talla,
                        "Colores": colores_list,
                        "Stock_Bodega": stock_bodega,
                        "Stock_Exhibido": stock_exhibido,
                        "Stock_Total": stock_bodega + stock_exhibido,
                        "Ventas_Total": 0,
                        "Precio_Sugerido": precio_sugerido,
                        "Precio_Venta": precio_venta
                    }
                    
                    st.session_state.productos.append(nuevo_prod)
                    sync_data()
                    st.success("Producto creado con éxito.")
                    st.rerun()

    elif accion == "Editar Producto":
        st.subheader("Editar Producto Existente")
        if not st.session_state.productos:
            st.info("Sin productos registrados.")
            return

        prod_dict = {f"{p['Producto']} - {p['Talla']} ({p['ID']})": p for p in st.session_state.productos}
        selected_prod_key = st.selectbox("Seleccione Producto a Editar:", list(prod_dict.keys()))
        prod = prod_dict[selected_prod_key]
        
        with st.form("form_edit_product"):
            categoria = st.selectbox("Categoría", st.session_state.categorias, index=st.session_state.categorias.index(prod["Categoria"]) if prod["Categoria"] in st.session_state.categorias else 0)
            nombre = st.text_input("Nombre del Producto", value=prod["Producto"])
            talla = st.text_input("Talla", value=prod["Talla"])
            colores_curr = ", ".join(prod["Colores"]) if isinstance(prod["Colores"], list) else prod["Colores"]
            colores_str = st.text_area("Colores (separados por comas)", value=colores_curr)
            
            c1, c2 = st.columns(2)
            stock_bodega = c1.number_input("Stock Bodega", min_value=0, value=int(prod["Stock_Bodega"]))
            stock_exhibido = c2.number_input("Stock Exhibido", min_value=0, value=int(prod["Stock_Exhibido"]))
            
            c3, c4 = st.columns(2)
            precio_sugerido = c3.number_input("Precio Sugerido ($)", min_value=0.0, value=float(prod["Precio_Sugerido"]))
            precio_venta = c4.number_input("Precio Venta ($)", min_value=0.0, value=float(prod["Precio_Venta"]))
            
            submitted = st.form_submit_button("Actualizar Producto")
            if submitted:
                colores_list = [c.strip() for c in colores_str.split(",") if c.strip()]
                prod["Categoria"] = categoria
                prod["Producto"] = nombre
                prod["Talla"] = talla
                prod["Colores"] = colores_list
                prod["Stock_Bodega"] = stock_bodega
                prod["Stock_Exhibido"] = stock_exhibido
                prod["Stock_Total"] = stock_bodega + stock_exhibido
                prod["Precio_Sugerido"] = precio_sugerido
                prod["Precio_Venta"] = precio_venta
                
                sync_data()
                st.success("Producto actualizado correctamente.")
                st.rerun()

    elif accion == "Eliminar Producto":
        st.subheader("Eliminar Producto")
        if not st.session_state.productos:
            st.info("Sin productos registrados.")
            return

        prod_dict = {f"{p['Producto']} - {p['Talla']} ({p['ID']})": p for p in st.session_state.productos}
        selected_prod_key = st.selectbox("Seleccione Producto a Eliminar:", list(prod_dict.keys()))
        prod = prod_dict[selected_prod_key]

        ventas_asociadas = [v for v in st.session_state.ventas if v.get("producto_id") == prod["ID"]]
        if ventas_asociadas:
            st.warning(f"Atención: Este producto cuenta con {len(ventas_asociadas)} ventas registradas en el historial.")

        if st.checkbox("Confirmo que deseo eliminar este producto permanentemente"):
            if st.button("Eliminar Definitivamente", type="primary"):
                st.session_state.productos = [p for p in st.session_state.productos if p["ID"] != prod["ID"]]
                sync_data()
                st.success("Producto eliminado.")
                st.rerun()

# ==========================================
# MÓDULO: GESTIÓN DE CATEGORÍAS
# ==========================================
def modulo_categorias():
    st.header("Gestión de Categorías")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Categorías Actuales")
        for cat in st.session_state.categorias:
            st.write(f"- {cat}")
            
    with c2:
        st.subheader("Agregar Categoría")
        nueva_cat = st.text_input("Nombre de la nueva categoría:")
        if st.button("Agregar"):
            if nueva_cat and nueva_cat not in st.session_state.categorias:
                st.session_state.categorias.append(nueva_cat)
                sync_data()
                st.success("Categoría agregada.")
                st.rerun()
            elif nueva_cat in st.session_state.categorias:
                st.error("La categoría ya existe.")

        st.divider()
        st.subheader("Eliminar Categoría")
        cat_eliminar = st.selectbox("Seleccionar categoría a eliminar:", st.session_state.categorias)
        if st.button("Eliminar Categoría"):
            prods_en_cat = [p for p in st.session_state.productos if p["Categoria"] == cat_eliminar]
            if prods_en_cat:
                st.error(f"No se puede eliminar: Hay {len(prods_en_cat)} productos asociados a esta categoría.")
            else:
                st.session_state.categorias.remove(cat_eliminar)
                sync_data()
                st.success("Categoría eliminada.")
                st.rerun()

# ==========================================
# MÓDULO: CORTE DE CAJA E HISTORIAL
# ==========================================
def modulo_corte_caja():
    st.header("Corte de Caja e Historial de Ventas")

    with st.expander("Configurar / Modificar Fondo de Caja Inicial", expanded=True):
        col_f1, col_f2 = st.columns([3, 1])
        with col_f1:
            nuevo_fondo = st.number_input(
                "Monto de Fondo de Caja ($):", 
                value=float(st.session_state.caja.get("fondo_caja", 0.0)),
                step=50.0,
                min_value=0.0
            )
        with col_f2:
            st.write("")
            st.write("")
            if st.button("Actualizar Fondo"):
                st.session_state.caja["fondo_caja"] = nuevo_fondo
                sync_data()
                st.success("Fondo de caja guardado.")
                st.rerun()

    fondo_actual = st.session_state.caja.get("fondo_caja", 0.0)

    if st.session_state.ventas:
        df_ventas = pd.DataFrame(st.session_state.ventas)
        df_ventas['fecha_dt'] = pd.to_datetime(df_ventas['fecha'])
        hoy = datetime.now().date()
        ventas_hoy = df_ventas[df_ventas['fecha_dt'].dt.date == hoy]
        
        total_ventas_hoy = ventas_hoy['precio_venta'].sum() if not ventas_hoy.empty else 0.0
        total_sugerido_hoy = ventas_hoy['precio_sugerido'].sum() if not ventas_hoy.empty else 0.0
        descuentos_aplicados = total_sugerido_hoy - total_ventas_hoy
        num_transacciones = len(ventas_hoy)
    else:
        df_ventas = pd.DataFrame()
        total_ventas_hoy = 0.0
        total_sugerido_hoy = 0.0
        descuentos_aplicados = 0.0
        num_transacciones = 0

    total_esperado_caja = fondo_actual + total_ventas_hoy

    st.subheader("Resumen General de Caja")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Fondo de Caja Inicial", f"${fondo_actual:,.2f}")
    kpi2.metric("Ventas del Día", f"${total_ventas_hoy:,.2f}")
    kpi3.metric("Total Esperado en Caja", f"${total_esperado_caja:,.2f}")
    kpi4.metric("Diferencia por Regateo", f"-${descuentos_aplicados:,.2f}")

    st.caption(f"Transacciones realizadas hoy: **{num_transacciones}**")

    st.divider()
    st.subheader("Historial Completo de Ventas")
    if not df_ventas.empty:
        st.dataframe(
            df_ventas[['fecha', 'producto', 'talla', 'color', 'categoria', 'precio_sugerido', 'precio_venta', 'ubicacion_venta']], 
            use_container_width=True
        )
    else:
        st.info("Aún no se han registrado ventas.")

    if admin_autenticado:
        st.divider()
        st.subheader("Acciones de Administración")
        if st.checkbox("Habilitar reinicio de caja"):
            if st.button("Reiniciar Caja (Borrar Ventas)", type="primary"):
                st.session_state.ventas = []
                sync_data()
                st.success("Historial de caja borrado correctamente.")
                st.rerun()

# ==========================================
# MÓDULO: REPORTES Y EXPORTACIÓN
# ==========================================
def modulo_reportes():
    st.header("Reportes y Exportación")
    
    if not st.session_state.productos:
        st.info("Sin datos para generar reportes.")
        return

    df_prod = pd.DataFrame(st.session_state.productos)
    df_ventas = pd.DataFrame(st.session_state.ventas) if st.session_state.ventas else pd.DataFrame()

    st.subheader("Métricas Generales de Inventario")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Productos Distintos", len(df_prod))
    kpi2.metric("Stock Total Unidades", df_prod['Stock_Total'].sum())
    kpi3.metric("Total Categorías", len(st.session_state.categorias))
    kpi4.metric("Bajo Stock (< 3 unidades)", len(df_prod[df_prod['Stock_Total'] < 3]))

    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("Distribución de Stock por Ubicación")
        total_bodega = df_prod['Stock_Bodega'].sum()
        total_exhibido = df_prod['Stock_Exhibido'].sum()
        df_ubic = pd.DataFrame({
            'Ubicacion': ['Bodega', 'Exhibido'],
            'Stock': [total_bodega, total_exhibido]
        })
        fig_bar = px.bar(df_ubic, x='Ubicacion', y='Stock', color='Ubicacion', text='Stock', color_discrete_sequence=['#1E293B', '#475569'])
        st.plotly_chart(fig_bar, use_container_width=True)

    with g2:
        st.subheader("Ventas por Categoría")
        if not df_ventas.empty:
            fig_pie = px.pie(df_ventas, names='categoria', values='precio_venta', hole=0.4, color_discrete_sequence=px.colors.qualitative.Dark24)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Aún no se registran ventas para generar el gráfico.")

    st.divider()
    st.subheader("Exportación de Datos")

    ex1, ex2 = st.columns(2)
    
    buffer_inv = io.BytesIO()
    with pd.ExcelWriter(buffer_inv, engine='openpyxl') as writer:
        df_prod.to_excel(writer, sheet_name='Inventario', index=False)
        
    ex1.download_button(
        label="Descargar Inventario Completo (Excel)",
        data=buffer_inv.getvalue(),
        file_name=f"Inventario_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if not df_ventas.empty:
        buffer_ven = io.BytesIO()
        with pd.ExcelWriter(buffer_ven, engine='openpyxl') as writer:
            df_ventas.to_excel(writer, sheet_name='Ventas', index=False)
            
        ex2.download_button(
            label="Descargar Historial de Ventas (Excel)",
            data=buffer_ven.getvalue(),
            file_name=f"Ventas_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==========================================
# RUTEO DE NAVEGACIÓN
# ==========================================
if rol == "Trabajadora":
    opcion = st.sidebar.selectbox("Navegación:", ["Ventas", "Transferir Stock", "Corte de Caja"])
    if opcion == "Ventas":
        modulo_ventas()
    elif opcion == "Transferir Stock":
        modulo_movimiento_stock()
    elif opcion == "Corte de Caja":
        modulo_corte_caja()

elif rol == "Administradora":
    if not admin_autenticado:
        st.warning("Ingrese la contraseña de administradora en el panel lateral para acceder.")
        modulo_ventas()
    else:
        opcion = st.sidebar.selectbox(
            "Navegación:", 
            ["Ventas", "Gestión Inventario", "Movimientos de Stock", "Categorías", "Corte de Caja", "Reportes y Exportación"]
        )
        if opcion == "Ventas":
            modulo_ventas()
        elif opcion == "Gestión Inventario":
            modulo_gestion_productos()
        elif opcion == "Movimientos de Stock":
            modulo_movimiento_stock()
        elif opcion == "Categorías":
            modulo_categorias()
        elif opcion == "Corte de Caja":
            modulo_corte_caja()
        elif opcion == "Reportes y Exportación":
            modulo_reportes()
