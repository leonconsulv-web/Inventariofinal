import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
import os

# ============================================
# CONFIGURACIÓN
# ============================================
st.set_page_config(
    page_title="Inventario roPacheco",
    page_icon="👔",
    layout="centered",
    initial_sidebar_state="collapsed"
)

CONTRASENA = "michiotaku"

# Inicializar estados base
if 'categorias_personalizadas' not in st.session_state:
    st.session_state.categorias_personalizadas = []
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'inventario' not in st.session_state:
    st.session_state.inventario = []
if 'ventas_diarias' not in st.session_state:
    st.session_state.ventas_diarias = []
if 'caja' not in st.session_state:
    st.session_state.caja = 0.0
if 'modo_edicion' not in st.session_state:
    st.session_state.modo_edicion = None
if 'mostrar_gestion_categorias' not in st.session_state:
    st.session_state.mostrar_gestion_categorias = False

# Archivos
INVENTARIO_FILE = "inventario_data.json"
CATEGORIAS_FILE = "categorias_data.json"

# Categorías base
CATEGORIAS_BASE = ['Camisas', 'Playeras', 'Suéteres', 'Chamarras', 'Pantalones', 'Shorts', 'Jeans', 'Niño']

def obtener_todas_categorias():
    todas = CATEGORIAS_BASE.copy()
    todas.extend(st.session_state.categorias_personalizadas)
    return sorted(list(set(todas)))

# ============================================
# FUNCIONES DE DATOS
# ============================================
def cargar_datos():
    try:
        if os.path.exists(INVENTARIO_FILE):
            with open(INVENTARIO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.inventario = data.get('inventario', [])
                st.session_state.ventas_diarias = data.get('ventas_diarias', [])
                st.session_state.caja = data.get('caja', 0.0)
    except:
        pass
    try:
        if os.path.exists(CATEGORIAS_FILE):
            with open(CATEGORIAS_FILE, 'r', encoding='utf-8') as f:
                st.session_state.categorias_personalizadas = json.load(f).get('categorias_personalizadas', [])
    except:
        pass

def guardar_inventario():
    try:
        data = {'inventario': st.session_state.inventario, 'ventas_diarias': st.session_state.ventas_diarias, 'caja': st.session_state.caja}
        with open(INVENTARIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def guardar_categorias():
    try:
        with open(CATEGORIAS_FILE, 'w', encoding='utf-8') as f:
            json.dump({'categorias_personalizadas': st.session_state.categorias_personalizadas}, f, ensure_ascii=False, indent=2)
    except:
        pass

# ============================================
# INTERFAZ PRINCIPAL
# ============================================
def main():
    st.title("👔 Inventario Ropa de Caballero")
    cargar_datos()
    
    tab1, tab2, tab3 = st.tabs(["🛍️ Registrar Ventas", "📊 Reporte y Caja", "⚙️ Gestión Inventario"])
    
    # ================= TAB 1: VENTAS =================
    with tab1:
        st.header("Registrar Ventas")
        
        if 'filtro_ventas_categoria' not in st.session_state:
            st.session_state.filtro_ventas_categoria = "Todas"
        cols = st.columns(min(len(obtener_todas_categorias()) + 1, 6))
        with cols[0]:
            if st.button("🚀 Todas", use_container_width=True): st.session_state.filtro_ventas_categoria = "Todas"; st.rerun()
        for i, cat in enumerate(obtener_todas_categorias()):
            if i+1 < len(cols):
                with cols[i+1]:
                    if st.button(cat, use_container_width=True): st.session_state.filtro_ventas_categoria = cat; st.rerun()
        
        df = pd.DataFrame(st.session_state.inventario)
        if df.empty:
            st.info("No hay productos.")
        else:
            if st.session_state.filtro_ventas_categoria != "Todas":
                df = df[df['Categoria'] == st.session_state.filtro_ventas_categoria]
                
            for _, row in df.iterrows():
                colores_resumen = ", ".join(row['Colores_Data'].keys())
                tallas_resumen = ", ".join(row['Tallas_Lista'])
                
                with st.expander(f"📦 {row['Producto']} | 🎨 {colores_resumen} | 📏 {tallas_resumen}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**📍 {row['Ubicacion']}** | 💰 ${row['Precio_Venta']}")
                        st.write(f"**📦 Bodega:** {row['Stock_Bodega']} | **🛍️ Exhibido:** {row['Stock_Exhibido']}")
                    
                    color_sel = st.selectbox("Color:", list(row['Colores_Data'].keys()), key=f"c_{row['ID']}")
                    if color_sel:
                        tallas_con_stock = [t for t in row['Tallas_Lista'] if row['Colores_Data'][color_sel].get(t, 0) > 0]
                        if not tallas_con_stock:
                            st.warning("Sin stock en este color.")
                        else:
                            talla_sel = st.selectbox("Talla:", tallas_con_stock, key=f"t_{row['ID']}")
                            precio = st.number_input("Precio:", value=row['Precio_Venta'], key=f"p_{row['ID']}")
                            if st.button("✅ Vender 1", key=f"v_{row['ID']}"):
                                row['Colores_Data'][color_sel][talla_sel] -= 1
                                if row['Ubicacion'] == 'Exhibido': row['Stock_Exhibido'] -= 1
                                else: row['Stock_Bodega'] -= 1
                                row['Stock_Total'] -= 1
                                row['Ventas_Total'] += 1
                                st.session_state.caja += precio
                                st.session_state.ventas_diarias.append({"producto": row['Producto'], "precio": precio})
                                guardar_inventario()
                                st.success("Vendido!"); st.rerun()

    # ================= TAB 3: GESTIÓN INVENTARIO (CON EDICIÓN) =================
    with tab3:
        st.header("⚙️ Gestión de Inventario")
        
        if not st.session_state.admin_logged_in:
            password = st.text_input("Contraseña:", type="password")
            if st.button("🔑 Entrar"):
                if password == CONTRASENA: st.session_state.admin_logged_in = True; st.rerun()
                else: st.error("Contraseña incorrecta")
        else:
            st.success("👑 Modo Administrador Activado")
            if st.button("🚪 Cerrar Sesión"): 
                st.session_state.admin_logged_in = False
                st.session_state.modo_edicion = None
                st.rerun()
            
            # Menú de botones del administrador
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            with col_btn1:
                if st.button("➕ Agregar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'agregar' else "secondary"):
                    st.session_state.modo_edicion = 'agregar'
                    st.session_state.num_colores = 1
                    st.rerun()
            with col_btn2:
                if st.button("✏️ Editar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'editar' else "secondary"):
                    st.session_state.modo_edicion = 'editar'
                    st.rerun()
            with col_btn3:
                if st.button("🗑️ Eliminar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'eliminar' else "secondary"):
                    st.session_state.modo_edicion = 'eliminar'
                    st.rerun()
            with col_btn4:
                if st.button("🏷️ Categorías", use_container_width=True):
                    st.session_state.mostrar_gestion_categorias = not st.session_state.mostrar_gestion_categorias
                    st.session_state.modo_edicion = None
                    st.rerun()
                    
            st.markdown("---")

            # --- CATEGORÍAS ---
            if st.session_state.mostrar_gestion_categorias:
                st.subheader("🏷️ Gestión de Categorías")
                nueva_cat = st.text_input("Nueva categoría")
                if st.button("➕ Agregar Categoría") and nueva_cat: 
                    agregar_categoria_personalizada(nueva_cat); st.rerun()

            # --- AGREGAR PRODUCTO ---
            elif st.session_state.modo_edicion == 'agregar':
                st.subheader("📝 Agregar Nuevo Producto")
                with st.form("form_agregar_producto"):
                    col1, col2 = st.columns(2)
                    with col1:
                        categoria = st.selectbox("Categoría:", obtener_todas_categorias())
                        producto = st.text_input("Nombre del Producto*:")
                    with col2:
                        precio_sugerido = st.number_input("Precio Sugerido ($):", min_value=0.0, value=0.0, step=0.5, format="%.2f")
                        precio_venta = st.number_input("Precio Venta ($):", min_value=0.0, value=0.0, step=0.5, format="%.2f")

                    st.divider()
                    st.markdown("### 📏 Definir Tallas")
                    tallas_input = st.text_input("Ejemplo: XS, S, M, G, XG, XXG", key="tallas_input")
                    tallas_lista = [t.strip() for t in tallas_input.split(",") if t.strip()] if tallas_input else []

                    st.divider()
                    st.markdown("### 🎨 Colores y Stock por Talla")
                    if 'num_colores' not in st.session_state: st.session_state.num_colores = 1
                    
                    colores_data = {}
                    if tallas_lista:
                        for i in range(st.session_state.num_colores):
                            with st.container(border=True):
                                st.markdown(f"**Color #{i+1}**")
                                color_nombre = st.text_input(f"Nombre del Color:", key=f"nombre_color_{i}")
                                if color_nombre:
                                    cols = st.columns(min(len(tallas_lista), 4))
                                    tallas_parcial = {}
                                    for j, talla in enumerate(tallas_lista):
                                        with cols[j % 4]:
                                            stock_val = st.number_input(f"Stock {talla}", min_value=0, step=1, key=f"stock_{i}_{talla}")
                                            if stock_val > 0: tallas_parcial[talla] = stock_val
                                    if tallas_parcial: colores_data[color_nombre] = tallas_parcial
                    else:
                        st.info("Escribe las tallas arriba para que aparezcan las casillas.")

                    st.markdown("---")
                    st.markdown("### 📦 Distribución de Stock")
                    col_b1, col_b2 = st.columns(2)
                    with col_b1: stock_bodega = st.number_input("Stock en Bodega:", min_value=0, value=0, step=1)
                    with col_b2: stock_exhibido = st.number_input("Stock en Exhibido:", min_value=0, value=1, step=1)
                        
                    st.divider()
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        if st.form_submit_button("➕ Agregar Otro Color"):
                            st.session_state.num_colores += 1
                            st.rerun()
                    with col_btn2:
                        guardar_btn = st.form_submit_button("✅ Guardar Producto", type="primary")

                    if guardar_btn:
                        if not producto or not tallas_input or not colores_data:
                            st.error("❌ Faltan datos: Producto, Tallas y al menos 1 Color con stock.")
                        elif (stock_bodega + stock_exhibido) <= 0:
                            st.error("❌ Debes distribuir el stock entre Bodega y Exhibido.")
                        else:
                            nuevo_prod = {
                                'ID': f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                'Categoria': categoria,
                                'Producto': producto,
                                'Tallas_Lista': tallas_lista,
                                'Colores_Data': colores_data,
                                'Stock_Bodega': stock_bodega,
                                'Stock_Exhibido': stock_exhibido,
                                'Stock_Total': stock_bodega + stock_exhibido,
                                'Ventas_Total': 0,
                                'Precio_Sugerido': precio_sugerido,
                                'Precio_Venta': precio_venta if precio_venta > 0 else precio_sugerido,
                                'Ubicacion': "Bodega" if stock_bodega > stock_exhibido else "Exhibido" if stock_exhibido > stock_bodega else "Exhibido",
                                'Entrada_Total': stock_bodega + stock_exhibido
                            }
                            st.session_state.inventario.append(nuevo_prod)
                            guardar_inventario()
                            st.success(f"✅ {producto} guardado!")
                            st.session_state.modo_edicion = None
                            st.rerun()

            # --- EDITAR PRODUCTO ---
            elif st.session_state.modo_edicion == 'editar':
                st.subheader("✏️ Editar Producto")
                df = pd.DataFrame(st.session_state.inventario)
                if df.empty:
                    st.info("No hay productos para editar.")
                else:
                    # Crear lista de opciones para el selector
                    opciones = {f"{row['Producto']} - {row['Categoria']}": row['ID'] for _, row in df.iterrows()}
                    seleccion = st.selectbox("Selecciona el producto a editar:", list(opciones.keys()))
                    
                    if seleccion:
                        prod_id = opciones[seleccion]
                        prod_data = next((p for p in st.session_state.inventario if p['ID'] == prod_id), None)
                        
                        if prod_data:
                            with st.form("form_editar_producto"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    nueva_cat = st.selectbox("Categoría:", obtener_todas_categorias(), index=obtener_todas_categorias().index(prod_data['Categoria']) if prod_data['Categoria'] in obtener_todas_categorias() else 0)
                                    nuevo_nombre = st.text_input("Nombre:", value=prod_data['Producto'])
                                with col2:
                                    nuevo_precio_sug = st.number_input("Precio Sugerido:", value=prod_data['Precio_Sugerido'], format="%.2f")
                                    nuevo_precio_venta = st.number_input("Precio Venta:", value=prod_data['Precio_Venta'], format="%.2f")

                                st.markdown("---")
                                st.markdown("🔄 **Stock y Tallas**")
                                st.caption("Para editar tallas o colores, es mejor eliminar y volver a crear.")
                                
                                # Editar distribución
                                col_b1, col_b2 = st.columns(2)
                                with col_b1: nuevo_stock_bodega = st.number_input("Nuevo Stock Bodega:", min_value=0, value=prod_data['Stock_Bodega'], step=1)
                                with col_b2: nuevo_stock_exhibido = st.number_input("Nuevo Stock Exhibido:", min_value=0, value=prod_data['Stock_Exhibido'], step=1)
                                
                                if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                                    prod_data['Categoria'] = nueva_cat
                                    prod_data['Producto'] = nuevo_nombre
                                    prod_data['Precio_Sugerido'] = nuevo_precio_sug
                                    prod_data['Precio_Venta'] = nuevo_precio_venta
                                    prod_data['Stock_Bodega'] = nuevo_stock_bodega
                                    prod_data['Stock_Exhibido'] = nuevo_stock_exhibido
                                    prod_data['Stock_Total'] = nuevo_stock_bodega + nuevo_stock_exhibido
                                    if nuevo_stock_bodega > nuevo_stock_exhibido: prod_data['Ubicacion'] = "Bodega"
                                    elif nuevo_stock_exhibido > nuevo_stock_bodega: prod_data['Ubicacion'] = "Exhibido"
                                    else: prod_data['Ubicacion'] = "Exhibido"
                                    guardar_inventario()
                                    st.success("✅ Producto actualizado.")
                                    st.session_state.modo_edicion = None
                                    st.rerun()

            # --- ELIMINAR PRODUCTO ---
            elif st.session_state.modo_edicion == 'eliminar':
                st.subheader("🗑️ Eliminar Producto")
                df = pd.DataFrame(st.session_state.inventario)
                if df.empty:
                    st.info("No hay productos.")
                else:
                    opciones = {f"{row['Producto']} - {row['Categoria']}": row['ID'] for _, row in df.iterrows()}
                    seleccion = st.selectbox("Selecciona el producto a eliminar:", list(opciones.keys()))
                    if st.button("✅ Sí, Eliminar Permanentemente", type="primary") and seleccion:
                        prod_id = opciones[seleccion]
                        success, msg = eliminar_producto(prod_id)
                        if success: st.success(msg); st.session_state.modo_edicion = None; st.rerun()
                        else: st.error(msg)

if __name__ == "__main__":
    main()