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

# Contraseña
CONTRASENA = "michiotaku"

# Configuración inicial
if 'categorias_personalizadas' not in st.session_state:
    st.session_state.categorias_personalizadas = []

if 'reset_graficas_fecha' not in st.session_state:
    st.session_state.reset_graficas_fecha = datetime.now().strftime('%Y-%m-%d')

# Categorías base
CATEGORIAS_BASE = [
    'Camisas', 'Playeras', 'Suéteres', 'Chamarras',
    'Pantalones', 'Shorts', 'Jeans', 'Niño'
]

# Obtener todas las categorías disponibles
def obtener_todas_categorias():
    todas = CATEGORIAS_BASE.copy()
    todas.extend(st.session_state.categorias_personalizadas)
    return sorted(list(set(todas)))

# Inicializar estados
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
if 'producto_editar' not in st.session_state:
    st.session_state.producto_editar = None
if 'mostrar_gestion_categorias' not in st.session_state:
    st.session_state.mostrar_gestion_categorias = False
if 'modo_mover_stock' not in st.session_state:
    st.session_state.modo_mover_stock = None
if 'producto_mover' not in st.session_state:
    st.session_state.producto_mover = None

# Archivo para guardar datos
INVENTARIO_FILE = "inventario_data.json"
CATEGORIAS_FILE = "categorias_data.json"

# ============================================
# FUNCIONES DE DATOS
# ============================================
def crear_nuevo_producto(producto, categoria, colores_data, stock_bodega, stock_exhibido, precio_sugerido, precio_venta):
    """Crear un nuevo producto con diccionario de colores y tallas"""
    nuevo_id = f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    entrada_total = stock_bodega + stock_exhibido
    stock_total = entrada_total
    
    if stock_bodega > stock_exhibido:
        ubicacion_principal = "Bodega"
    elif stock_exhibido > stock_bodega:
        ubicacion_principal = "Exhibido"
    else:
        ubicacion_principal = "Exhibido"
    
    return {
        'ID': nuevo_id,
        'Categoria': categoria,
        'Producto': producto,
        'Colores_Data': colores_data, # Diccionario: {'Rojo': {'S':2, 'M':1}, 'Azul': {'L':5}}
        'Ubicacion': ubicacion_principal,
        'Entrada_Total': entrada_total,
        'Stock_Bodega': stock_bodega,
        'Stock_Exhibido': stock_exhibido,
        'Stock_Total': stock_total,
        'Ventas_Total': 0,
        'Precio_Sugerido': float(precio_sugerido),
        'Precio_Venta': float(precio_venta) if precio_venta > 0 else float(precio_sugerido)
    }

def cargar_datos():
    try:
        if os.path.exists(INVENTARIO_FILE):
            with open(INVENTARIO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.inventario = data.get('inventario', [])
                st.session_state.ventas_diarias = data.get('ventas_diarias', [])
                st.session_state.caja = data.get('caja', 0.0)
    except Exception as e:
        st.error(f"Error al cargar inventario: {str(e)}")
    
    try:
        if os.path.exists(CATEGORIAS_FILE):
            with open(CATEGORIAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.categorias_personalizadas = data.get('categorias_personalizadas', [])
    except:
        st.session_state.categorias_personalizadas = []

def guardar_inventario():
    try:
        data = {
            'inventario': st.session_state.inventario,
            'ventas_diarias': st.session_state.ventas_diarias,
            'caja': st.session_state.caja,
            'ultima_actualizacion': datetime.now().isoformat()
        }
        with open(INVENTARIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error al guardar inventario: {str(e)}")

def guardar_categorias():
    try:
        data = {'categorias_personalizadas': st.session_state.categorias_personalizadas}
        with open(CATEGORIAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error al guardar categorías: {str(e)}")

def agregar_categoria_personalizada(nueva_categoria):
    if nueva_categoria and nueva_categoria not in obtener_todas_categorias():
        st.session_state.categorias_personalizadas.append(nueva_categoria)
        guardar_categorias()
        return True
    return False

def eliminar_categoria_personalizada(categoria):
    if categoria in st.session_state.categorias_personalizadas:
        productos_en_categoria = [p for p in st.session_state.inventario if p['Categoria'] == categoria]
        if productos_en_categoria:
            return False, f"No se puede eliminar. Hay {len(productos_en_categoria)} productos usando esta categoría."
        st.session_state.categorias_personalizadas.remove(categoria)
        guardar_categorias()
        return True, f"Categoría '{categoria}' eliminada correctamente"
    return False, "Categoría no encontrada"

def registrar_venta(producto_id, color_seleccionado, talla_seleccionada, precio_venta_real=None):
    for item in st.session_state.inventario:
        if item['ID'] == producto_id:
            # Validar stock del color y talla específico
            if color_seleccionado in item['Colores_Data']:
                if talla_seleccionada in item['Colores_Data'][color_seleccionado]:
                    if item['Colores_Data'][color_seleccionado][talla_seleccionada] > 0:
                        
                        # Descontar del stock del color y talla
                        item['Colores_Data'][color_seleccionado][talla_seleccionada] -= 1
                        
                        # Actualizar lógica de ubicación
                        if item['Ubicacion'] == 'Exhibido':
                            item['Stock_Exhibido'] -= 1
                        else:
                            item['Stock_Bodega'] -= 1
                        
                        item['Ventas_Total'] += 1
                        item['Stock_Total'] -= 1
                        
                        precio_final = float(precio_venta_real) if precio_venta_real else item['Precio_Venta']
                        
                        venta = {
                            'fecha': datetime.now().isoformat(),
                            'producto': item['Producto'],
                            'color': color_seleccionado,
                            'talla': talla_seleccionada,
                            'precio_sugerido': item['Precio_Sugerido'],
                            'precio_venta': precio_final,
                            'categoria': item['Categoria'],
                            'ubicacion': item['Ubicacion']
                        }
                        st.session_state.ventas_diarias.append(venta)
                        st.session_state.caja += precio_final
                        
                        guardar_inventario()
                        return True, precio_final, item['Ubicacion']
                    else:
                        return False, f"No hay stock para {color_seleccionado} - Talla {talla_seleccionada}", None
                else:
                    return False, f"La talla {talla_seleccionada} no existe para el color {color_seleccionado}", None
            else:
                return False, f"El color {color_seleccionado} no existe en este producto", None
    return False, "Producto no encontrado", None

def agregar_producto(nuevo_producto):
    st.session_state.inventario.append(nuevo_producto)
    guardar_inventario()
    return True

def eliminar_producto(producto_id):
    for i, item in enumerate(st.session_state.inventario):
        if item['ID'] == producto_id:
            producto_eliminado = st.session_state.inventario.pop(i)
            if producto_eliminado['Ventas_Total'] > 0:
                ventas_producto = [v for v in st.session_state.ventas_diarias 
                                  if v.get('producto') == producto_eliminado['Producto']]
                total_ventas_producto = sum(v.get('precio_venta', 0) for v in ventas_producto)
                st.session_state.caja -= total_ventas_producto
                if st.session_state.caja < 0: st.session_state.caja = 0
            guardar_inventario()
            return True, f"Producto '{producto_eliminado['Producto']}' eliminado correctamente"
    return False, "Producto no encontrado"

def calcular_caja_total():
    total = 0.0
    for venta in st.session_state.ventas_diarias:
        total += venta.get('precio_venta', 0)
    return total

# ============================================
# INTERFAZ PRINCIPAL
# ============================================
def main():
    st.title("👔 Inventario Ropa de Caballero")
    
    cargar_datos()
    
    with st.expander("ℹ️ Información del Sistema", expanded=False):
        st.write("**✨ NUEVO SISTEMA DE COLORES Y TALLAS:**")
        st.write("- Agrega un color y dentro de él el stock por talla (S, M, L, XL).")
        st.write("- Puedes agregar tantos colores como quieras con el botón '+'.")

    st.markdown("---")
    
    df = pd.DataFrame(st.session_state.inventario)
    
    tab1, tab2, tab3 = st.tabs(["🛍️ Registrar Ventas", "📊 Reporte y Caja", "⚙️ Gestión Inventario"])
    
    # ================= TAB 1: REGISTRAR VENTAS =================
    with tab1:
        st.header("Registrar Ventas")
        
        # Filtros Rápidos - BOTONES DE CATEGORÍA
        st.subheader("🔍 Filtros Rápidos por Categoría")
        cols = st.columns(len(obtener_todas_categorias()) + 1)
        
        if 'filtro_ventas_categoria' not in st.session_state:
            st.session_state.filtro_ventas_categoria = "Todas"
            
        with cols[0]:
            if st.button("🚀 Todas", use_container_width=True):
                st.session_state.filtro_ventas_categoria = "Todas"
                st.rerun()
        
        for i, cat in enumerate(obtener_todas_categorias()):
            with cols[i+1]:
                if st.button(cat, use_container_width=True):
                    st.session_state.filtro_ventas_categoria = cat
                    st.rerun()
        
        st.markdown("---")
        
        if df.empty:
            st.info("📭 No hay productos en el inventario.")
        else:
            col_filt1, col_filt2, col_filt3 = st.columns(3)
            with col_filt1:
                categoria_filtro = st.selectbox("Categoría:", ['Todas'] + sorted(obtener_todas_categorias()), key="cat_filtro_ventas")
            with col_filt2:
                ubicacion_filtro = st.selectbox("Ubicación:", ['Todas', 'Exhibido', 'Bodega'], key="ubic_filtro_ventas")
            with col_filt3:
                search_term = st.text_input("🔍 Buscar:", "", key="search_ventas")
            
            filtered_df = df.copy()
            
            if not df.empty:
                if categoria_filtro != 'Todas':
                    filtered_df = filtered_df[filtered_df['Categoria'] == categoria_filtro]
                # Sobrescribir si se usó el botón rápido
                if st.session_state.filtro_ventas_categoria != "Todas":
                    filtered_df = filtered_df[filtered_df['Categoria'] == st.session_state.filtro_ventas_categoria]
                
                if ubicacion_filtro != 'Todas':
                    filtered_df = filtered_df[filtered_df['Ubicacion'] == ubicacion_filtro]
                
                if search_term:
                    filtered_df = filtered_df[filtered_df['Producto'].str.contains(search_term, case=False, na=False)]
            
            if filtered_df.empty:
                st.info("No se encontraron productos.")
            else:
                st.write(f"**📊 {len(filtered_df)} productos encontrados**")
                
                # Visualización de productos
                for _, row in filtered_df.iterrows():
                    # Sumarizar stock para mostrar
                    stock_total_producto = 0
                    colores_str = ""
                    tallas_str = ""
                    
                    if 'Colores_Data' in row and row['Colores_Data']:
                        colores_lista = list(row['Colores_Data'].keys())
                        colores_str = ", ".join(colores_lista)
                        
                        # Calcular tallas
                        tallas_set = set()
                        for color, tallas in row['Colores_Data'].items():
                            for talla, cant in tallas.items():
                                tallas_set.add(talla)
                                stock_total_producto += cant
                        tallas_str = ", ".join(sorted(list(tallas_set)))

                    with st.expander(f"📦 {row['Producto']} | 🎨 {colores_str} | 👕 {tallas_str}"):
                        col_info1, col_info2 = st.columns(2)
                        
                        with col_info1:
                            st.write(f"**📋 Categoría:** {row['Categoria']}")
                            st.write(f"**📍 Ubicación:** {row['Ubicacion']}")
                            st.write(f"**💰 Sugerido:** ${row['Precio_Sugerido']:,.2f}")
                            st.write(f"**💵 Venta:** ${row['Precio_Venta']:,.2f}")
                        
                        with col_info2:
                            st.write(f"**🛍️ Exhibido:** {int(row['Stock_Exhibido'])}")
                            st.write(f"**📦 Bodega:** {int(row['Stock_Bodega'])}")
                            st.write(f"**📊 Total:** {int(row['Stock_Total'])}")
                            st.write(f"**📈 Ventas:** {int(row['Ventas_Total'])}")
                        
                        st.markdown("---")
                        
                        # SELECCIÓN DE COLOR Y TALLA PARA VENTA
                        colores_disponibles = list(row['Colores_Data'].keys())
                        color_seleccionado = st.selectbox("Selecciona el Color:", colores_disponibles, key=f"color_venta_{row['ID']}")
                        
                        if color_seleccionado:
                            tallas_disponibles = list(row['Colores_Data'][color_seleccionado].keys())
                            # Filtrar tallas con stock > 0
                            tallas_con_stock = [t for t in tallas_disponibles if row['Colores_Data'][color_seleccionado][t] > 0]
                            
                            if not tallas_con_stock:
                                st.error(f"❌ Sin stock disponible para {color_seleccionado}")
                            else:
                                talla_seleccionada = st.selectbox("Selecciona la Talla:", tallas_con_stock, key=f"talla_venta_{row['ID']}")
                                
                                with st.form(key=f"venta_form_{row['ID']}"):
                                    col_precio1, col_precio2 = st.columns(2)
                                    with col_precio1:
                                        precio_venta = st.number_input(
                                            f"Precio de venta ($):",
                                            min_value=0.0,
                                            value=float(row['Precio_Venta']),
                                            step=0.01,
                                            format="%.2f",
                                            key=f"precio_venta_{row['ID']}"
                                        )
                                    
                                    with col_precio2:
                                        if st.form_submit_button("✅ Vender 1 Unidad", use_container_width=True, type="primary"):
                                            success, resultado, ubicacion = registrar_venta(row['ID'], color_seleccionado, talla_seleccionada, precio_venta)
                                            if success:
                                                st.success(f"✅ Vendido por ${resultado:,.2f} ({color_seleccionado} - Talla {talla_seleccionada})")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {resultado}")
                        else:
                            st.error("No hay colores disponibles en este producto.")

    # ================= TAB 2: REPORTE Y CAJA =================
    with tab2:
        st.header("📊 Reporte y Caja")
        
        with st.expander("🔄 Control de Gráficas", expanded=False):
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                nueva_fecha_reset = st.date_input(
                    "Próximo reset de gráficas:",
                    value=datetime.strptime(st.session_state.reset_graficas_fecha, '%Y-%m-%d'),
                    key="fecha_reset"
                )
            with col_res2:
                if st.button("💾 Guardar Fecha", use_container_width=True):
                    st.session_state.reset_graficas_fecha = nueva_fecha_reset.strftime('%Y-%m-%d')
                    st.success(f"Fecha guardada: {nueva_fecha_reset.strftime('%Y-%m-%d')}")
                
                if st.button("🔄 Resetear Gráficas Ahora", use_container_width=True, type="secondary"):
                    st.session_state.ventas_diarias = []
                    guardar_inventario()
                    st.success("¡Gráficas reseteadas!")
                    st.rerun()
        
        if df.empty:
            st.info("No hay datos para mostrar.")
        else:
            columnas_necesarias = ['Stock_Bodega', 'Stock_Exhibido', 'Stock_Total', 
                                 'Ventas_Total', 'Precio_Sugerido', 'Precio_Venta']
            
            caja_total = calcular_caja_total()
            st.session_state.caja = caja_total
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_ventas = df['Ventas_Total'].sum()
                st.metric("📈 Ventas Totales", f"{int(total_ventas)}")
            with col2:
                st.metric("💰 Caja Total", f"${caja_total:,.2f}")
            with col3:
                stock_exhibido = df['Stock_Exhibido'].sum()
                st.metric("🛍️ Stock Exhibido", f"{int(stock_exhibido)}")
            with col4:
                stock_bodega = df['Stock_Bodega'].sum()
                st.metric("📦 Stock Bodega", f"{int(stock_bodega)}")
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if not df.empty:
                    ventas_por_categoria = df.groupby('Categoria')['Ventas_Total'].sum().reset_index()
                    if not ventas_por_categoria.empty:
                        fig = px.pie(ventas_por_categoria, values='Ventas_Total', names='Categoria', title="📊 Ventas por Categoría", hole=0.3)
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
            with col2:
                if not df.empty:
                    stock_data = pd.DataFrame({
                        'Ubicacion': ['Exhibido', 'Bodega'],
                        'Stock': [int(df['Stock_Exhibido'].sum()), int(df['Stock_Bodega'].sum())]
                    })
                    if not stock_data.empty:
                        fig = px.bar(stock_data, x='Ubicacion', y='Stock', title="📍 Distribución del Stock", color='Ubicacion', text='Stock')
                        fig.update_traces(textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📋 Inventario Completo")
            
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                todas_categorias_tabla = ['Todas'] + sorted(df['Categoria'].unique().tolist())
                filtro_categoria = st.selectbox("Filtrar categoría:", todas_categorias_tabla, key="filtro_categoria_tabla")
            with col_f2:
                filtro_ubicacion = st.selectbox("Filtrar ubicación:", ['Todas', 'Exhibido', 'Bodega'], key="filtro_ubicacion_tabla")
            with col_f3:
                ordenar_por = st.selectbox("Ordenar por:", ['Producto', 'Stock_Total', 'Ventas_Total', 'Precio_Venta'], key="ordenar_por_tabla")
            
            display_df = df.copy()
            
            if filtro_categoria != 'Todas':
                display_df = display_df[display_df['Categoria'] == filtro_categoria]
            if filtro_ubicacion != 'Todas':
                display_df = display_df[display_df['Ubicacion'] == filtro_ubicacion]
            
            if ordenar_por == 'Stock_Total':
                display_df = display_df.sort_values('Stock_Total', ascending=False)
            elif ordenar_por == 'Ventas_Total':
                display_df = display_df.sort_values('Ventas_Total', ascending=False)
            elif ordenar_por == 'Precio_Venta':
                display_df = display_df.sort_values('Precio_Venta', ascending=False)
            else:
                display_df = display_df.sort_values('Producto')
            
            if not display_df.empty:
                # Para la tabla, necesitamos reconstruir un texto legible de colores y tallas
                colores_str_list = []
                tallas_str_list = []
                for _, row in display_df.iterrows():
                    if 'Colores_Data' in row and row['Colores_Data']:
                        colores_str_list.append(", ".join(row['Colores_Data'].keys()))
                        # Sumarizar stock de tallas para mostrar visualmente
                        tallas_stock_str = []
                        for color_data in row['Colores_Data'].values():
                            for t, s in color_data.items():
                                if s > 0:
                                    tallas_stock_str.append(f"{t}:{s}")
                        tallas_str_list.append(", ".join(tallas_stock_str))
                    else:
                        colores_str_list.append("N/A")
                        tallas_str_list.append("N/A")
                
                display_df = display_df.copy()
                display_df['Colores'] = colores_str_list
                display_df['Tallas_Stock'] = tallas_str_list
                
                display_df['Precio_Sugerido'] = display_df['Precio_Sugerido'].apply(lambda x: f"${x:,.2f}")
                display_df['Precio_Venta'] = display_df['Precio_Venta'].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(
                    display_df[['Categoria', 'Producto', 'Colores', 'Tallas_Stock', 'Ubicacion', 
                               'Stock_Bodega', 'Stock_Exhibido', 'Stock_Total', 
                               'Ventas_Total', 'Precio_Sugerido', 'Precio_Venta']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Categoria': st.column_config.TextColumn("Categoría"),
                        'Producto': st.column_config.TextColumn("Producto"),
                        'Colores': st.column_config.TextColumn("🎨 Colores"),
                        'Tallas_Stock': st.column_config.TextColumn("📏 Tallas (Stock)"),
                        'Ubicacion': st.column_config.TextColumn("📍 Ubicación"),
                        'Stock_Bodega': st.column_config.NumberColumn("📦 Bodega", format="%d"),
                        'Stock_Exhibido': st.column_config.NumberColumn("🛍️ Exhibido", format="%d"),
                        'Stock_Total': st.column_config.NumberColumn("📊 Total", format="%d"),
                        'Ventas_Total': st.column_config.NumberColumn("📈 Ventas", format="%d"),
                        'Precio_Sugerido': st.column_config.TextColumn("💰 Sugerido"),
                        'Precio_Venta': st.column_config.TextColumn("💵 Venta")
                    }
                )
            else:
                st.info("No hay productos que coincidan con los filtros.")

    # ================= TAB 3: GESTIÓN INVENTARIO =================
    with tab3:
        st.header("⚙️ Gestión de Inventario")
        
        if not st.session_state.admin_logged_in:
            st.markdown("### 🔒 Acceso Administrador")
            with st.container(border=True):
                password = st.text_input("Contraseña:", type="password", key="password_input_admin")
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🔑 Ingresar", type="primary", use_container_width=True, key="login_admin"):
                        if password == CONTRASENA:
                            st.session_state.admin_logged_in = True
                            st.success("✅ Acceso concedido")
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta")
        else:
            st.success("✅ **Modo administrador activado**")
            col_logout, col_cats, col_mover, col_space = st.columns([1, 1, 1, 1])
            with col_logout:
                if st.button("🚪 Cerrar Sesión", use_container_width=True, key="logout_admin"):
                    st.session_state.admin_logged_in = False
                    st.session_state.modo_edicion = None
                    st.rerun()
            with col_cats:
                if st.button("🏷️ Categorías", use_container_width=True, type="primary" if st.session_state.mostrar_gestion_categorias else "secondary"):
                    st.session_state.mostrar_gestion_categorias = not st.session_state.mostrar_gestion_categorias
                    st.session_state.modo_edicion = None
                    st.rerun()
            
            st.markdown("---")
            
            # PANEL DE GESTIÓN DE CATEGORÍAS
            if st.session_state.mostrar_gestion_categorias:
                st.subheader("🏷️ Gestión de Categorías")
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    with st.container(border=True):
                        st.markdown("### 📋 Categorías Existentes")
                        todas_categorias = obtener_todas_categorias()
                        st.write("**Categorías base:**")
                        for cat in CATEGORIAS_BASE: st.write(f"- {cat}")
                        if st.session_state.categorias_personalizadas:
                            st.write("\n**Categorías personalizadas:**")
                            for cat in st.session_state.categorias_personalizadas: st.write(f"- 📌 {cat}")
                with col_info2:
                    with st.container(border=True):
                        st.markdown("### ➕ Agregar Nueva Categoría")
                        nueva_categoria = st.text_input("Nombre:", placeholder="Ej: Sudaderas")
                        if st.button("➕ Agregar", use_container_width=True):
                            if nueva_categoria:
                                if agregar_categoria_personalizada(nueva_categoria):
                                    st.success(f"✅ Categoría '{nueva_categoria}' agregada!")
                                    st.rerun()
                                else: st.error(f"❌ La categoría '{nueva_categoria}' ya existe.")
                            else: st.error("❌ Ingresa un nombre.")
            else:
                # PANEL DE ACCIONES
                st.subheader("📋 Acciones Disponibles")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("➕ Agregar Producto", use_container_width=True, type="primary" if st.session_state.modo_edicion == 'agregar' else "secondary"):
                        st.session_state.modo_edicion = 'agregar'
                        st.rerun()
                
                st.markdown("---")
                
                if st.session_state.modo_edicion == 'agregar':
                    st.subheader("📝 Agregar Nuevo Producto")
                    
                    # -- FORMULARIO DE AGREGAR CON TARJETAS DE COLOR --
                    with st.form("form_agregar_producto"):
                        col1, col2 = st.columns(2)
                        with col1:
                            categoria = st.selectbox("Categoría:", obtener_todas_categorias(), key="cat_agregar")
                            producto = st.text_input("Nombre del Producto*:", key="prod_agregar")
                        with col2:
                            st.markdown("### 📦 Distribución del Stock")
                            col_stock1, col_stock2 = st.columns(2)
                            with col_stock1: stock_bodega = st.number_input("Stock en Bodega:", min_value=0, value=0, step=1, key="stock_bodega_agregar")
                            with col_stock2: stock_exhibido = st.number_input("Stock en Exhibido:", min_value=0, value=1, step=1, key="stock_exhibido_agregar")
                            st.markdown("### 💰 Precios")
                            precio_sugerido = st.number_input("Precio Sugerido ($):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="precio_sug_agregar")
                            precio_venta = st.number_input("Precio Venta ($):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="precio_venta_agregar")
                        
                        st.divider()
                        st.subheader("🎨 Ingresa los Colores y su Stock por Talla")
                        
                        # Inicializar contador de colores
                        if 'num_colores' not in st.session_state:
                            st.session_state.num_colores = 1
                        
                        colores_data = {}
                        for i in range(st.session_state.num_colores):
                            with st.container(border=True):
                                st.markdown(f"**Color #{i+1}**")
                                color_nombre = st.text_input(f"Nombre del Color (ej: Rojo):", key=f"nombre_color_{i}")
                                
                                if color_nombre:
                                    c1, c2, c3, c4 = st.columns(4)
                                    with c1: stock_s = st.number_input(f"Stock Talla S", min_value=0, step=1, key=f"stock_s_{i}")
                                    with c2: stock_m = st.number_input(f"Stock Talla M", min_value=0, step=1, key=f"stock_m_{i}")
                                    with c3: stock_l = st.number_input(f"Stock Talla L", min_value=0, step=1, key=f"stock_l_{i}")
                                    with c4: stock_xl = st.number_input(f"Stock Talla XL", min_value=0, step=1, key=f"stock_xl_{i}")
                                    
                                    # Guardar datos temporalmente
                                    tallas_parcial = {}
                                    if stock_s > 0: tallas_parcial['S'] = stock_s
                                    if stock_m > 0: tallas_parcial['M'] = stock_m
                                    if stock_l > 0: tallas_parcial['L'] = stock_l
                                    if stock_xl > 0: tallas_parcial['XL'] = stock_xl
                                    
                                    if tallas_parcial:
                                        colores_data[color_nombre] = tallas_parcial
                        
                        st.markdown("---")
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
                        with col_btn2:
                            if st.form_submit_button("➕ Agregar Otro Color", use_container_width=True):
                                st.session_state.num_colores += 1
                                st.rerun()
                        
                        submitted = st.form_submit_button("✅ Guardar Producto", type="primary", use_container_width=True)
                        
                        if submitted:
                            if not producto or not colores_data:
                                st.error("❌ Completa el nombre del producto y al menos un color con stock.")
                            elif (stock_bodega + stock_exhibido) == 0:
                                st.error("❌ El stock total general debe ser mayor a 0")
                            else:
                                nuevo_producto = crear_nuevo_producto(
                                    producto=producto,
                                    categoria=categoria,
                                    colores_data=colores_data,
                                    stock_bodega=stock_bodega,
                                    stock_exhibido=stock_exhibido,
                                    precio_sugerido=precio_sugerido,
                                    precio_venta=precio_venta if precio_venta > 0 else precio_sugerido
                                )
                                
                                if agregar_producto(nuevo_producto):
                                    st.success(f"✅ {producto} agregado exitosamente con {len(colores_data)} colores!")
                                    st.session_state.modo_edicion = None
                                    st.session_state.num_colores = 1
                                    st.rerun()

if __name__ == "__main__":
    main()