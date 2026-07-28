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
                        tallas_con_stock = [t for t in row['Tallas_Lista'] if row['Colores_Data'][color_sel]['vitrina'].get(t, 0) > 0]
                        if not tallas_con_stock:
                            st.warning("Sin stock en vitrina para este color.")
                        else:
                            talla_sel = st.selectbox("Talla:", tallas_con_stock, key=f"t_{row['ID']}")
                            precio = st.number_input("Precio:", value=row['Precio_Venta'], key=f"p_{row['ID']}")
                            if st.button("✅ Vender 1", key=f"v_{row['ID']}"):
                                row['Colores_Data'][color_sel]['vitrina'][talla_sel] -= 1
                                row['Stock_Exhibido'] -= 1
                                row['Stock_Total'] -= 1
                                row['Ventas_Total'] += 1
                                st.session_state.caja += precio
                                st.session_state.ventas_diarias.append({"producto": row['Producto'], "precio": precio})
                                guardar_inventario()
                                st.success("Vendido!"); st.rerun()

    # ================= TAB 3: GESTIÓN INVENTARIO =================
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
            
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("➕ Agregar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'agregar' else "secondary"):
                    st.session_state.modo_edicion = 'agregar'
                    st.session_state.num_colores = 1 # Solo empieza con 1 color
                    st.rerun()
            with col_btn2:
                if st.button("✏️ Editar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'editar' else "secondary"):
                    st.session_state.modo_edicion = 'editar'
                    st.rerun()
            with col_btn3:
                if st.button("🗑️ Eliminar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'eliminar' else "secondary"):
                    st.session_state.modo_edicion = 'eliminar'
                    st.rerun()
                    
            st.markdown("---")

            # --- AGREGAR PRODUCTO (COLORES DINÁMICOS CON BOTÓN) ---
            if st.session_state.modo_edicion == 'agregar':
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
                    st.caption("Separa las tallas por comas (Ej: XS, S, M, G, XG)")
                    tallas_input = st.text_input("Tallas:", value="XS, S, M, G, XG, XXG")
                    tallas_lista = [t.strip() for t in tallas_input.split(",") if t.strip()] if tallas_input else []

                    st.divider()
                    st.markdown("### 🎨 Colores, Vitrina y Bodega")
                    st.caption("Por cada color, llena el stock de Vitrina y Bodega.")
                    
                    # Inicializar contador de colores
                    if 'num_colores' not in st.session_state: 
                        st.session_state.num_colores = 1
                    
                    colores_data = {}
                    if tallas_lista:
                        # Generar recuadros según el número actual
                        for i in range(st.session_state.num_colores):
                            with st.container(border=True):
                                st.markdown(f"**🎨 Color #{i+1}**")
                                color_nombre = st.text_input(f"Nombre del Color:", key=f"nombre_color_{i}")
                                
                                if color_nombre:
                                    st.markdown(f"**🟦 Stock en Vitrina (para {color_nombre})**")
                                    cols_vitrina = st.columns(min(len(tallas_lista), 4))
                                    vitrina_parcial = {}
                                    for j, talla in enumerate(tallas_lista):
                                        with cols_vitrina[j % 4]:
                                            stock_val = st.number_input(f"V {talla}", min_value=0, step=1, key=f"vitrina_{i}_{talla}")
                                            if stock_val > 0: vitrina_parcial[talla] = stock_val

                                    st.markdown(f"**🟫 Stock en Bodega (para {color_nombre})**")
                                    cols_bodega = st.columns(min(len(tallas_lista), 4))
                                    bodega_parcial = {}
                                    for j, talla in enumerate(tallas_lista):
                                        with cols_bodega[j % 4]:
                                            stock_val = st.number_input(f"B {talla}", min_value=0, step=1, key=f"bodega_{i}_{talla}")
                                            if stock_val > 0: bodega_parcial[talla] = stock_val
                                    
                                    if vitrina_parcial or bodega_parcial:
                                        colores_data[color_nombre] = {
                                            'vitrina': vitrina_parcial,
                                            'bodega': bodega_parcial
                                        }
                    else:
                        st.info("Escribe las tallas arriba para que aparezcan las casillas.")
                        
                    st.divider()
                    
                    # BOTONES DE ACCIÓN
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        # BOTÓN PARA AGREGAR UN COLOR MÁS (Dinámico)
                        if st.form_submit_button("➕ Agregar otro color"):
                            st.session_state.num_colores += 1
                            st.rerun()
                    with col_btn2:
                        guardar_btn = st.form_submit_button("✅ Guardar Producto", type="primary")

                    if guardar_btn:
                        if not producto or not tallas_input or not colores_data:
                            st.error("❌ Faltan datos: Producto, Tallas y al menos 1 Color.")
                        else:
                            # ----- ESTA ES LA PARTE QUE ARREGLÉ -----
                            total_vitrina = 0
                            total_bodega = 0
                            
                            # Sumar cada talla dentro de cada color
                            for color in colores_data.values():
                                total_vitrina += sum(color['vitrina'].values())
                                total_bodega += sum(color['bodega'].values())
                            
                            nuevo_prod = {
                                'ID': f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                'Categoria': categoria,
                                'Producto': producto,
                                'Tallas_Lista': tallas_lista,
                                'Colores_Data': colores_data,
                                'Stock_Bodega': total_bodega,
                                'Stock_Exhibido': total_vitrina,
                                'Stock_Total': total_vitrina + total_bodega,
                                'Ventas_Total': 0,
                                'Precio_Sugerido': precio_sugerido,
                                'Precio_Venta': precio_venta if precio_venta > 0 else precio_sugerido,
                                'Ubicacion': "Bodega" if total_bodega > total_vitrina else "Exhibido" if total_vitrina > total_bodega else "Exhibido",
                                'Entrada_Total': total_vitrina + total_bodega
                            }
                            st.session_state.inventario.append(nuevo_prod)
                            guardar_inventario()
                            st.success(f"✅ {producto} guardado con éxito!")
                            # Resumen extra para confirmar
                            st.info(f"📊 Resumen: {total_vitrina} unidades a Vitrina | {total_bodega} unidades a Bodega")
                            st.session_state.modo_edicion = None
                            st.rerun()

            # --- EDITAR Y ELIMINAR ---
            elif st.session_state.modo_edicion == 'editar':
                st.info("Para editar la configuración de colores y tallas, elimina y vuelve a crear el producto. Aquí solo puedes editar los precios.")
                
            elif st.session_state.modo_edicion == 'eliminar':
                st.subheader("🗑️ Eliminar Producto")
                df = pd.DataFrame(st.session_state.inventario)
                if not df.empty:
                    opciones = {f"{row['Producto']} - {row['Categoria']}": row['ID'] for _, row in df.iterrows()}
                    seleccion = st.selectbox("Selecciona el producto a eliminar:", list(opciones.keys()))
                    if st.button("✅ Sí, Eliminar") and seleccion:
                        prod_id = opciones[seleccion]
                        for i, item in enumerate(st.session_state.inventario):
                            if item['ID'] == prod_id:
                                st.session_state.inventario.pop(i)
                                guardar_inventario()
                                st.success("Eliminado!"); st.session_state.modo_edicion = None; st.rerun()
                                break

if __name__ == "__main__":
    main()