import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
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
if 'categoria_seleccionada' not in st.session_state:
    st.session_state.categoria_seleccionada = 'Todas'

# Archivo para guardar datos
INVENTARIO_FILE = "inventario_data.json"
CATEGORIAS_FILE = "categorias_data.json"

# ============================================
# FUNCIONES DE DATOS
# ============================================
def crear_nuevo_producto(producto, talla, colores, categoria, stock_bodega, stock_exhibido, precio_sugerido, precio_venta):
    """Crear un nuevo producto especificando stock por ubicación y colores múltiples"""
    nuevo_id = f"PROD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    entrada_total = stock_bodega + stock_exhibido
    stock_total = entrada_total
    
    if stock_bodega > stock_exhibido:
        ubicacion_principal = "Bodega"
    elif stock_exhibido > stock_bodega:
        ubicacion_principal = "Exhibido"
    else:
        ubicacion_principal = "Exhibido"
    
    # Procesar colores
    colores_lista = []
    if colores:
        if isinstance(colores, str):
            colores_lista = [c.strip() for c in colores.split(',') if c.strip()]
        elif isinstance(colores, list):
            colores_lista = colores
    
    if not colores_lista:
        colores_lista = ['Sin color']
    
    return {
        'ID': nuevo_id,
        'Categoria': categoria,
        'Producto': producto,
        'Talla': talla,
        'Colores': colores_lista,
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
    """Cargar todos los datos desde archivos"""
    try:
        if os.path.exists(INVENTARIO_FILE):
            with open(INVENTARIO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.inventario = data.get('inventario', [])
                st.session_state.ventas_diarias = data.get('ventas_diarias', [])
                st.session_state.caja = data.get('caja', 0.0)
    except Exception as e:
        st.error(f"Error al cargar inventario: {str(e)}")
        st.session_state.inventario = []
        st.session_state.ventas_diarias = []
        st.session_state.caja = 0.0
    
    try:
        if os.path.exists(CATEGORIAS_FILE):
            with open(CATEGORIAS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.categorias_personalizadas = data.get('categorias_personalizadas', [])
    except:
        st.session_state.categorias_personalizadas = []

def guardar_inventario():
    """Guardar inventario en archivo"""
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
    """Guardar categorías personalizadas en archivo"""
    try:
        data = {
            'categorias_personalizadas': st.session_state.categorias_personalizadas,
            'ultima_actualizacion': datetime.now().isoformat()
        }
        with open(CATEGORIAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error al guardar categorías: {str(e)}")

def agregar_categoria_personalizada(nueva_categoria):
    """Agregar una nueva categoría personalizada"""
    if nueva_categoria and nueva_categoria not in obtener_todas_categorias():
        st.session_state.categorias_personalizadas.append(nueva_categoria)
        guardar_categorias()
        return True
    return False

def eliminar_categoria_personalizada(categoria):
    """Eliminar una categoría personalizada"""
    if categoria in st.session_state.categorias_personalizadas:
        productos_en_categoria = [p for p in st.session_state.inventario if p.get('Categoria') == categoria]
        
        if productos_en_categoria:
            return False, f"No se puede eliminar. Hay {len(productos_en_categoria)} productos usando esta categoría."
        
        st.session_state.categorias_personalizadas.remove(categoria)
        guardar_categorias()
        return True, f"Categoría '{categoria}' eliminada correctamente"
    
    return False, "Categoría no encontrada"

def registrar_venta(producto_id, precio_venta_real=None, color_seleccionado=None):
    """Registrar una venta con precio de venta real y color específico"""
    for item in st.session_state.inventario:
        if item['ID'] == producto_id:
            if item['Ubicacion'] == 'Exhibido':
                stock_disponible = item['Stock_Exhibido']
                ubicacion_venta = "exhibido"
            else:
                stock_disponible = item['Stock_Bodega']
                ubicacion_venta = "bodega"
            
            if stock_disponible > 0:
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
                    'talla': item['Talla'],
                    'color': color_seleccionado or (item['Colores'][0] if item['Colores'] else 'Sin color'),
                    'precio_sugerido': item['Precio_Sugerido'],
                    'precio_venta': precio_final,
                    'categoria': item['Categoria'],
                    'ubicacion': item['Ubicacion'],
                    'ubicacion_venta': ubicacion_venta
                }
                st.session_state.ventas_diarias.append(venta)
                st.session_state.caja += precio_final
                
                guardar_inventario()
                return True, precio_final, ubicacion_venta
            else:
                return False, f"No hay stock disponible en {item['Ubicacion']}", None
    
    return False, "Producto no encontrado", None

def agregar_producto(nuevo_producto):
    """Agregar nuevo producto al inventario"""
    st.session_state.inventario.append(nuevo_producto)
    guardar_inventario()
    return True

def eliminar_producto(producto_id):
    """Eliminar un producto del inventario"""
    for i, item in enumerate(st.session_state.inventario):
        if item['ID'] == producto_id:
            producto_eliminado = st.session_state.inventario.pop(i)
            
            if producto_eliminado['Ventas_Total'] > 0:
                ventas_producto = [v for v in st.session_state.ventas_diarias 
                                  if v.get('producto') == producto_eliminado['Producto']]
                
                total_ventas_producto = sum(v.get('precio_venta', 0) for v in ventas_producto)
                st.session_state.caja -= total_ventas_producto
                
                if st.session_state.caja < 0:
                    st.session_state.caja = 0
            
            guardar_inventario()
            return True, f"Producto '{producto_eliminado['Producto']}' eliminado correctamente"
    
    return False, "Producto no encontrado"

def mover_stock(producto_id, cantidad, origen, destino):
    """Mover stock entre bodega y exhibido"""
    for item in st.session_state.inventario:
        if item['ID'] == producto_id:
            stock_origen = item['Stock_Bodega'] if origen == 'Bodega' else item['Stock_Exhibido']
            
            if stock_origen < cantidad:
                return False, f"No hay suficiente stock en {origen} (solo hay {stock_origen})"
            
            if origen == 'Bodega':
                item['Stock_Bodega'] -= cantidad
                item['Stock_Exhibido'] += cantidad
            else:
                item['Stock_Exhibido'] -= cantidad
                item['Stock_Bodega'] += cantidad
            
            if item['Stock_Bodega'] > item['Stock_Exhibido']:
                item['Ubicacion'] = 'Bodega'
            elif item['Stock_Exhibido'] > item['Stock_Bodega']:
                item['Ubicacion'] = 'Exhibido'
            
            guardar_inventario()
            return True, f"{cantidad} unidades movidas de {origen} a {destino}"
    
    return False, "Producto no encontrado"

def calcular_caja_total():
    """Calcular el total de caja desde las ventas diarias"""
    total = 0.0
    for venta in st.session_state.ventas_diarias:
        total += venta.get('precio_venta', 0)
    return total

# ============================================
# INTERFAZ PRINCIPAL
# ============================================
def main():
    st.title("Inventario roPacheco")
    
    cargar_datos()
    
    with st.expander("Información del Sistema", expanded=False):
        st.write("""
        **CARACTERÍSTICAS PRINCIPALES:**
        - Stock por ubicación: Especifica cuántos van a bodega y cuántos a exhibido
        - Doble precio: Precio sugerido y precio de venta real
        - Mover stock: Transfiere entre ubicaciones
        - Ventas flexibles: Precio personalizable por venta
        - Colores múltiples: Hasta 500 colores por producto
        """)
    
    st.markdown("---")
    
    # Crear DataFrame y asegurar columnas necesarias
    df = pd.DataFrame(st.session_state.inventario)
    
    # Si el DataFrame está vacío, crear uno con las columnas necesarias
    if df.empty:
        df = pd.DataFrame(columns=['ID', 'Categoria', 'Producto', 'Talla', 'Colores', 'Ubicacion', 
                                   'Stock_Bodega', 'Stock_Exhibido', 'Stock_Total', 'Ventas_Total', 
                                   'Precio_Sugerido', 'Precio_Venta', 'Entrada_Total'])
    
    tab1, tab2, tab3 = st.tabs(["Registrar Ventas", "Reporte y Caja", "Gestion Inventario"])
    
    # ============================================
    # TAB 1: REGISTRAR VENTAS
    # ============================================
    with tab1:
        st.header("Registrar Ventas")
        
        if df.empty or len(st.session_state.inventario) == 0:
            st.info("No hay productos en el inventario. Ve a la pestaña 'Gestion Inventario' para agregar productos.")
        else:
            # Botones de categorías
            todas_categorias = obtener_todas_categorias()
            
            st.subheader("Categorías")
            
            # Crear columnas para botones (4 por fila)
            cols = st.columns(4)
            
            # Botón "Todas"
            if cols[0].button("Todas", use_container_width=True,
                             type="primary" if st.session_state.categoria_seleccionada == 'Todas' else "secondary"):
                st.session_state.categoria_seleccionada = 'Todas'
                st.rerun()
            
            # Botones para cada categoría
            for i, cat in enumerate(todas_categorias):
                col_idx = (i + 1) % 4
                if cols[col_idx].button(cat, use_container_width=True,
                                       type="primary" if st.session_state.categoria_seleccionada == cat else "secondary"):
                    st.session_state.categoria_seleccionada = cat
                    st.rerun()
            
            # Filtrar productos por categoría
            if st.session_state.categoria_seleccionada == 'Todas':
                filtered_df = df
            else:
                filtered_df = df[df['Categoria'] == st.session_state.categoria_seleccionada]
            
            if filtered_df.empty:
                st.info(f"No hay productos en la categoría {st.session_state.categoria_seleccionada}")
            else:
                st.subheader(f"Productos en {st.session_state.categoria_seleccionada}")
                
                for _, row in filtered_df.iterrows():
                    # Manejar colores
                    if 'Colores' in row:
                        if isinstance(row['Colores'], list):
                            colores_list = row['Colores']
                        elif isinstance(row['Colores'], str):
                            colores_list = [row['Colores']]
                        else:
                            colores_list = ['Sin color']
                    else:
                        colores_list = ['Sin color']
                    
                    colores_text = ", ".join(colores_list) if colores_list else "Sin color"
                    
                    with st.expander(f"{row['Producto']} | Talla: {row['Talla']} | Colores: {colores_text}"):
                        col_info1, col_info2 = st.columns(2)
                        
                        with col_info1:
                            st.write(f"Categoría: {row['Categoria']}")
                            st.write(f"Ubicación: {row['Ubicacion']}")
                            st.write(f"Precio sugerido: ${row['Precio_Sugerido']:,.2f}")
                            st.write(f"Precio venta: ${row['Precio_Venta']:,.2f}")
                        
                        with col_info2:
                            st.write(f"Exhibido: {int(row['Stock_Exhibido'])}")
                            st.write(f"Bodega: {int(row['Stock_Bodega'])}")
                            st.write(f"Total: {int(row['Stock_Total'])}")
                            st.write(f"Ventas: {int(row['Ventas_Total'])}")
                        
                        if row['Ubicacion'] == 'Exhibido':
                            stock_disponible = row['Stock_Exhibido']
                            ubicacion_texto = "exhibido"
                        else:
                            stock_disponible = row['Stock_Bodega']
                            ubicacion_texto = "bodega"
                        
                        if stock_disponible > 0:
                            # Selector de color
                            color_seleccionado = None
                            if colores_list and len(colores_list) > 0:
                                color_seleccionado = st.selectbox(
                                    "Color:",
                                    colores_list,
                                    key=f"color_{row['ID']}"
                                )
                            
                            with st.form(key=f"venta_form_{row['ID']}"):
                                col_precio1, col_precio2 = st.columns(2)
                                with col_precio1:
                                    precio_venta = st.number_input(
                                        "Precio de venta ($):",
                                        min_value=0.0,
                                        value=float(row['Precio_Venta']),
                                        step=0.01,
                                        format="%.2f",
                                        key=f"precio_venta_{row['ID']}"
                                    )
                                
                                with col_precio2:
                                    if st.form_submit_button("Vender 1 Unidad", use_container_width=True, type="primary"):
                                        success, resultado, ubicacion = registrar_venta(row['ID'], precio_venta, color_seleccionado)
                                        if success:
                                            st.success(f"Vendido por ${resultado:,.2f} (desde {ubicacion})")
                                            st.rerun()
                                        else:
                                            st.error(f"{resultado}")
                        else:
                            st.error(f"Sin stock disponible en {ubicacion_texto}")
    
    # ============================================
    # TAB 2: REPORTE Y CAJA
    # ============================================
    with tab2:
        st.header("Reporte y Caja")
        
        with st.expander("Control de Gráficas", expanded=False):
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                nueva_fecha_reset = st.date_input(
                    "Próximo reset de gráficas:",
                    value=datetime.strptime(st.session_state.reset_graficas_fecha, '%Y-%m-%d'),
                    key="fecha_reset"
                )
            
            with col_res2:
                if st.button("Guardar Fecha", use_container_width=True):
                    st.session_state.reset_graficas_fecha = nueva_fecha_reset.strftime('%Y-%m-%d')
                    st.success(f"Fecha guardada: {nueva_fecha_reset.strftime('%Y-%m-%d')}")
                
                if st.button("Resetear Gráficas Ahora", use_container_width=True, type="secondary"):
                    st.session_state.ventas_diarias = []
                    guardar_inventario()
                    st.success("Gráficas reseteadas!")
                    st.rerun()
        
        if df.empty or len(st.session_state.inventario) == 0:
            st.info("No hay datos para mostrar. Agrega productos primero.")
        else:
            caja_total = calcular_caja_total()
            st.session_state.caja = caja_total
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_ventas = df['Ventas_Total'].sum()
                st.metric("Ventas Totales", f"{int(total_ventas)}")
            
            with col2:
                st.metric("Caja Total", f"${caja_total:,.2f}")
            
            with col3:
                stock_exhibido = df['Stock_Exhibido'].sum()
                st.metric("Stock Exhibido", f"{int(stock_exhibido)}")
            
            with col4:
                stock_bodega = df['Stock_Bodega'].sum()
                st.metric("Stock Bodega", f"{int(stock_bodega)}")
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if not df.empty:
                    ventas_por_categoria = df.groupby('Categoria')['Ventas_Total'].sum().reset_index()
                    if not ventas_por_categoria.empty:
                        fig = px.pie(
                            ventas_por_categoria, 
                            values='Ventas_Total', 
                            names='Categoria',
                            title="Ventas por Categoría",
                            color_discrete_sequence=px.colors.qualitative.Set3,
                            hole=0.3
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if not df.empty:
                    stock_data = pd.DataFrame({
                        'Ubicacion': ['Exhibido', 'Bodega'],
                        'Stock': [int(df['Stock_Exhibido'].sum()), int(df['Stock_Bodega'].sum())]
                    })
                    
                    if not stock_data.empty:
                        fig = px.bar(
                            stock_data,
                            x='Ubicacion',
                            y='Stock',
                            title="Distribución del Stock",
                            color='Ubicacion',
                            text='Stock',
                            color_discrete_map={'Exhibido': '#2E86AB', 'Bodega': '#A23B72'}
                        )
                        fig.update_traces(textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            st.subheader("Inventario Completo")
            
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
                display_df_formatted = display_df.copy()
                display_df_formatted['Precio_Sugerido'] = display_df_formatted['Precio_Sugerido'].apply(lambda x: f"${x:,.2f}")
                display_df_formatted['Precio_Venta'] = display_df_formatted['Precio_Venta'].apply(lambda x: f"${x:,.2f}")
                display_df_formatted['Colores'] = display_df_formatted['Colores'].apply(
                    lambda x: ", ".join(x) if isinstance(x, list) else str(x) if x else ""
                )
                
                st.dataframe(
                    display_df_formatted[['Categoria', 'Producto', 'Talla', 'Colores', 'Ubicacion', 
                                         'Stock_Bodega', 'Stock_Exhibido', 'Stock_Total', 
                                         'Ventas_Total', 'Precio_Sugerido', 'Precio_Venta']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'Categoria': st.column_config.TextColumn("Categoría"),
                        'Producto': st.column_config.TextColumn("Producto"),
                        'Talla': st.column_config.TextColumn("Talla"),
                        'Colores': st.column_config.TextColumn("Colores"),
                        'Ubicacion': st.column_config.TextColumn("Ubicación"),
                        'Stock_Bodega': st.column_config.NumberColumn("Bodega", format="%d"),
                        'Stock_Exhibido': st.column_config.NumberColumn("Exhibido", format="%d"),
                        'Stock_Total': st.column_config.NumberColumn("Total", format="%d"),
                        'Ventas_Total': st.column_config.NumberColumn("Ventas", format="%d"),
                        'Precio_Sugerido': st.column_config.TextColumn("Sugerido"),
                        'Precio_Venta': st.column_config.TextColumn("Venta")
                    }
                )
            else:
                st.info("No hay productos que coincidan con los filtros.")
            
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            with col_exp1:
                if st.button("Exportar CSV", use_container_width=True, key="export_csv"):
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="Descargar CSV",
                        data=csv,
                        file_name=f"inventario_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_csv"
                    )
            
            with col_exp2:
                if st.button("Actualizar Precios", use_container_width=True, key="btn_actualizar_precios"):
                    st.session_state.modo_edicion = 'actualizar_precios'
                    st.rerun()
            
            with col_exp3:
                if st.button("Reiniciar Caja", use_container_width=True, key="reset_caja"):
                    st.session_state.caja = 0.0
                    st.session_state.ventas_diarias = []
                    for item in st.session_state.inventario:
                        item['Ventas_Total'] = 0
                        item['Stock_Total'] = item['Entrada_Total']
                    guardar_inventario()
                    st.success("Caja y ventas reiniciadas")
                    st.rerun()
    
    # ============================================
    # TAB 3: GESTIÓN INVENTARIO
    # ============================================
    with tab3:
        st.header("Gestión de Inventario")
        
        if not st.session_state.admin_logged_in:
            st.markdown("### Acceso Administrador")
            
            with st.container(border=True):
                password = st.text_input("Contraseña:", type="password", key="password_input_admin")
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("Ingresar", type="primary", use_container_width=True, key="login_admin"):
                        if password == CONTRASENA:
                            st.session_state.admin_logged_in = True
                            st.success("Acceso concedido")
                            st.rerun()
                        else:
                            st.error("Contraseña incorrecta")
        else:
            st.success("Modo administrador activado")
            
            col_logout, col_cats, col_mover, col_space = st.columns([1, 1, 1, 1])
            with col_logout:
                if st.button("Cerrar Sesión", use_container_width=True, key="logout_admin"):
                    st.session_state.admin_logged_in = False
                    st.session_state.modo_edicion = None
                    st.session_state.producto_editar = None
                    st.session_state.mostrar_gestion_categorias = False
                    st.session_state.modo_mover_stock = None
                    st.rerun()
            
            with col_cats:
                if st.button("Categorías", use_container_width=True, 
                           type="primary" if st.session_state.mostrar_gestion_categorias else "secondary"):
                    st.session_state.mostrar_gestion_categorias = not st.session_state.mostrar_gestion_categorias
                    st.session_state.modo_edicion = None
                    st.session_state.modo_mover_stock = None
                    st.rerun()
            
            with col_mover:
                if st.button("Mover Stock", use_container_width=True,
                           type="primary" if st.session_state.modo_mover_stock == 'seleccionar' else "secondary"):
                    st.session_state.modo_mover_stock = 'seleccionar'
                    st.session_state.mostrar_gestion_categorias = False
                    st.session_state.modo_edicion = None
                    st.rerun()
            
            st.markdown("---")
            
            # MODO: MOVER STOCK
            if st.session_state.modo_mover_stock == 'seleccionar':
                st.subheader("Mover Stock entre Ubicaciones")
                
                if df.empty or len(st.session_state.inventario) == 0:
                    st.info("No hay productos para mover.")
                else:
                    productos_opciones = {f"{row['Producto']} ({row['Talla']}) - B:{row['Stock_Bodega']} | E:{row['Stock_Exhibido']}": row['ID'] 
                                        for _, row in df.iterrows()}
                    
                    producto_seleccionado = st.selectbox(
                        "Selecciona un producto para mover stock:",
                        list(productos_opciones.keys()),
                        key="select_mover"
                    )
                    
                    if producto_seleccionado:
                        producto_id = productos_opciones[producto_seleccionado]
                        producto_data = next((item for item in st.session_state.inventario 
                                            if item['ID'] == producto_id), None)
                        
                        if producto_data:
                            st.session_state.producto_mover = producto_id
                            st.session_state.modo_mover_stock = 'mover'
                            st.rerun()
            
            elif st.session_state.modo_mover_stock == 'mover' and st.session_state.producto_mover:
                producto_id = st.session_state.producto_mover
                producto_data = next((item for item in st.session_state.inventario 
                                    if item['ID'] == producto_id), None)
                
                if producto_data:
                    st.subheader(f"Mover Stock: {producto_data['Producto']}")
                    
                    with st.form("form_mover_stock"):
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.write(f"Stock Bodega: {producto_data['Stock_Bodega']}")
                            st.write(f"Stock Exhibido: {producto_data['Stock_Exhibido']}")
                            st.write(f"Ubicación actual: {producto_data['Ubicacion']}")
                        
                        with col_info2:
                            direccion = st.selectbox(
                                "Dirección del movimiento:",
                                ["De Bodega a Exhibido", "De Exhibido a Bodega"],
                                key="direccion_mover"
                            )
                            
                            if direccion == "De Bodega a Exhibido":
                                origen = "Bodega"
                                destino = "Exhibido"
                                max_cantidad = producto_data['Stock_Bodega']
                            else:
                                origen = "Exhibido"
                                destino = "Bodega"
                                max_cantidad = producto_data['Stock_Exhibido']
                            
                            cantidad = st.number_input(
                                f"Cantidad a mover (máx: {max_cantidad}):",
                                min_value=1,
                                max_value=max_cantidad,
                                value=1 if max_cantidad > 0 else 0,
                                step=1,
                                key="cantidad_mover"
                            )
                        
                        col_btn1, col_btn2, col_btn3 = st.columns(3)
                        with col_btn1:
                            mover = st.form_submit_button("Mover Stock", type="primary", use_container_width=True)
                        with col_btn2:
                            cancelar = st.form_submit_button("Cancelar", use_container_width=True)
                        
                        if cancelar:
                            st.session_state.modo_mover_stock = None
                            st.session_state.producto_mover = None
                            st.rerun()
                        
                        if mover and cantidad > 0:
                            success, mensaje = mover_stock(producto_id, cantidad, origen, destino)
                            if success:
                                st.success(f"{mensaje}")
                                st.session_state.modo_mover_stock = None
                                st.session_state.producto_mover = None
                                st.rerun()
                            else:
                                st.error(f"{mensaje}")
            
            # PANEL DE GESTIÓN DE CATEGORÍAS
            elif st.session_state.mostrar_gestion_categorias:
                st.subheader("Gestión de Categorías")
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    with st.container(border=True):
                        st.markdown("### Categorías Existentes")
                        todas_categorias = obtener_todas_categorias()
                        
                        st.write("**Categorías base:**")
                        for cat in CATEGORIAS_BASE:
                            st.write(f"- {cat}")
                        
                        if st.session_state.categorias_personalizadas:
                            st.write("\n**Categorías personalizadas:**")
                            for cat in st.session_state.categorias_personalizadas:
                                st.write(f"- {cat}")
                        else:
                            st.info("No hay categorías personalizadas aún.")
                
                with col_info2:
                    with st.container(border=True):
                        st.markdown("### Agregar Nueva Categoría")
                        
                        nueva_categoria = st.text_input("Nombre de la nueva categoría:", 
                                                      placeholder="Ej: Sudaderas, Trajes, Chalecos...")
                        
                        if st.button("Agregar Categoría", use_container_width=True):
                            if nueva_categoria:
                                if agregar_categoria_personalizada(nueva_categoria):
                                    st.success(f"Categoría '{nueva_categoria}' agregada!")
                                    st.rerun()
                                else:
                                    st.error(f"La categoría '{nueva_categoria}' ya existe.")
                            else:
                                st.error("Ingresa un nombre para la categoría.")
                        
                        st.markdown("---")
                        
                        st.markdown("### Eliminar Categoría Personalizada")
                        
                        if st.session_state.categorias_personalizadas:
                            cat_a_eliminar = st.selectbox(
                                "Selecciona categoría a eliminar:",
                                st.session_state.categorias_personalizadas,
                                key="select_cat_eliminar"
                            )
                            
                            if st.button("Eliminar Categoría", use_container_width=True, type="secondary"):
                                success, message = eliminar_categoria_personalizada(cat_a_eliminar)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        else:
                            st.info("No hay categorías personalizadas para eliminar.")
                
                st.markdown("---")
                if st.button("Volver a Gestión", use_container_width=True):
                    st.session_state.mostrar_gestion_categorias = False
                    st.rerun()
            
            # MODO: ACTUALIZAR PRECIOS
            elif st.session_state.modo_edicion == 'actualizar_precios':
                st.subheader("Actualizar Precios")
                
                if df.empty or len(st.session_state.inventario) == 0:
                    st.info("No hay productos para actualizar.")
                else:
                    productos_opciones = []
                    for idx, row in df.iterrows():
                        opcion = f"{row['Producto']} ({row['Talla']}) - Sug:${row['Precio_Sugerido']:.2f} | Ven:${row['Precio_Venta']:.2f}"
                        productos_opciones.append((opcion, idx))
                    
                    opciones_texto = [op[0] for op in productos_opciones]
                    indices = [op[1] for op in productos_opciones]
                    
                    seleccion_index = st.selectbox(
                        "Selecciona un producto para actualizar precios:",
                        range(len(opciones_texto)),
                        format_func=lambda i: opciones_texto[i],
                        key="select_actualizar_precios"
                    )
                    
                    if seleccion_index is not None:
                        idx_producto = indices[seleccion_index]
                        producto_data = st.session_state.inventario[idx_producto]
                        
                        if producto_data:
                            with st.form("form_actualizar_precios"):
                                col_precio1, col_precio2 = st.columns(2)
                                
                                with col_precio1:
                                    nuevo_precio_sugerido = st.number_input(
                                        "Nuevo precio sugerido ($):",
                                        min_value=0.0,
                                        value=float(producto_data['Precio_Sugerido']),
                                        step=0.01,
                                        format="%.2f",
                                        key="nuevo_sugerido"
                                    )
                                
                                with col_precio2:
                                    nuevo_precio_venta = st.number_input(
                                        "Nuevo precio de venta ($):",
                                        min_value=0.0,
                                        value=float(producto_data['Precio_Venta']),
                                        step=0.01,
                                        format="%.2f",
                                        key="nuevo_venta"
                                    )
                                
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    guardar = st.form_submit_button("Actualizar Precios", type="primary", use_container_width=True)
                                with col_btn2:
                                    cancelar = st.form_submit_button("Cancelar", use_container_width=True)
                                
                                if cancelar:
                                    st.session_state.modo_edicion = None
                                    st.rerun()
                                
                                if guardar:
                                    producto_data['Precio_Sugerido'] = float(nuevo_precio_sugerido)
                                    producto_data['Precio_Venta'] = float(nuevo_precio_venta)
                                    guardar_inventario()
                                    st.success("Ambos precios actualizados")
                                    st.session_state.modo_edicion = None
                                    st.rerun()
            
            # MODO NORMAL: GESTIÓN DE PRODUCTOS
            else:
                st.subheader("Acciones Disponibles")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("Agregar Producto", use_container_width=True, 
                               type="primary" if st.session_state.modo_edicion == 'agregar' else "secondary"):
                        st.session_state.modo_edicion = 'agregar'
                        st.session_state.producto_editar = None
                        st.rerun()
                
                with col2:
                    if st.button("Editar Producto", use_container_width=True,
                               type="primary" if st.session_state.modo_edicion == 'editar' else "secondary"):
                        st.session_state.modo_edicion = 'editar'
                        st.rerun()
                
                with col3:
                    if st.button("Eliminar Producto", use_container_width=True,
                               type="primary" if st.session_state.modo_edicion == 'eliminar' else "secondary"):
                        st.session_state.modo_edicion = 'eliminar'
                        st.rerun()
                
                with col4:
                    if st.button("Ver Inventario", use_container_width=True,
                               type="primary" if st.session_state.modo_edicion is None else "secondary"):
                        st.session_state.modo_edicion = None
                        st.rerun()
                
                st.markdown("---")
                
                # MODO: AGREGAR PRODUCTO
                if st.session_state.modo_edicion == 'agregar':
                    st.subheader("Agregar Nuevo Producto")
                    
                    with st.form("form_agregar_producto", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            todas_categorias = obtener_todas_categorias()
                            
                            categoria = st.selectbox("Categoría:", todas_categorias, key="cat_agregar")
                            producto = st.text_input("Nombre del Producto*:", key="prod_agregar")
                            talla = st.text_input("Talla*:", placeholder="M, 32, Unitalla...", key="talla_agregar")
                            
                            colores_input = st.text_area(
                                "Colores* (separados por coma):", 
                                placeholder="Negro, Azul, Rojo, Verde, Blanco...",
                                key="colores_agregar",
                                help="Ingresa todos los colores disponibles separados por coma"
                            )
                        
                        with col2:
                            st.markdown("### Distribución del Stock")
                            
                            col_stock1, col_stock2 = st.columns(2)
                            with col_stock1:
                                stock_bodega = st.number_input(
                                    "Stock en Bodega:",
                                    min_value=0,
                                    value=0,
                                    step=1,
                                    key="stock_bodega_agregar"
                                )
                            
                            with col_stock2:
                                stock_exhibido = st.number_input(
                                    "Stock en Exhibido:",
                                    min_value=0,
                                    value=1,
                                    step=1,
                                    key="stock_exhibido_agregar"
                                )
                            
                            total_stock = stock_bodega + stock_exhibido
                            if total_stock == 0:
                                st.error("El stock total debe ser mayor a 0")
                            else:
                                ubicacion_principal = "Exhibido" if stock_exhibido > stock_bodega else "Bodega" if stock_bodega > stock_exhibido else "Exhibido (iguales)"
                                st.info(f"Stock total: {total_stock} unidades")
                                st.info(f"Ubicación principal: {ubicacion_principal}")
                            
                            st.markdown("### Precios")
                            precio_sugerido = st.number_input("Precio Sugerido ($):", 
                                                            min_value=0.0, 
                                                            value=0.0, 
                                                            step=0.01, 
                                                            format="%.2f", 
                                                            key="precio_sug_agregar")
                            
                            precio_venta = st.number_input("Precio Venta Inicial ($):", 
                                                         min_value=0.0, 
                                                         value=0.0, 
                                                         step=0.01, 
                                                         format="%.2f", 
                                                         key="precio_venta_agregar")
                        
                        st.caption("(*) Campos obligatorios")
                        
                        submitted = st.form_submit_button("Agregar al Inventario", type="primary", use_container_width=True)
                        
                        if submitted:
                            if not producto or not talla or not colores_input:
                                st.error("Completa los campos obligatorios (*)")
                            elif total_stock == 0:
                                st.error("El stock total debe ser mayor a 0")
                            else:
                                nuevo_producto = crear_nuevo_producto(
                                    producto=producto,
                                    talla=talla,
                                    colores=colores_input,
                                    categoria=categoria,
                                    stock_bodega=stock_bodega,
                                    stock_exhibido=stock_exhibido,
                                    precio_sugerido=precio_sugerido,
                                    precio_venta=precio_venta if precio_venta > 0 else precio_sugerido
                                )
                                
                                if agregar_producto(nuevo_producto):
                                    st.success(f"{producto} agregado exitosamente!")
                                    st.balloons()
                                    st.session_state.modo_edicion = None
                                    st.rerun()
                
                # MODO: EDITAR PRODUCTO
                elif st.session_state.modo_edicion == 'editar':
                    st.subheader("Editar Producto Existente")
                    
                    if df.empty or len(st.session_state.inventario) == 0:
                        st.info("No hay productos para editar.")
                    else:
                        productos_opciones = []
                        for idx, row in df.iterrows():
                            colores_text = ", ".join(row['Colores']) if row['Colores'] else "Sin color"
                            opcion = f"{row['Producto']} ({row['Talla']}) - {colores_text[:20]}..."
                            productos_opciones.append((opcion, idx))
                        
                        opciones_texto = [op[0] for op in productos_opciones]
                        indices = [op[1] for op in productos_opciones]
                        
                        seleccion_index = st.selectbox(
                            "Selecciona un producto para editar:",
                            range(len(opciones_texto)),
                            format_func=lambda i: opciones_texto[i],
                            key="select_editar"
                        )
                        
                        if seleccion_index is not None:
                            idx_producto = indices[seleccion_index]
                            producto_data = st.session_state.inventario[idx_producto]
                            
                            if producto_data:
                                st.info(f"Editando: {producto_data['Producto']} - {producto_data['Talla']}")
                                
                                with st.form("form_editar_producto"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        todas_categorias = obtener_todas_categorias()
                                        
                                        try:
                                            cat_index = todas_categorias.index(producto_data['Categoria']) 
                                        except ValueError:
                                            cat_index = 0
                                            
                                        nueva_categoria = st.selectbox(
                                            "Categoría:",
                                            todas_categorias,
                                            index=cat_index,
                                            key="cat_editar"
                                        )
                                        
                                        nuevo_producto = st.text_input("Nombre del Producto*:", 
                                                                      value=producto_data['Producto'],
                                                                      key="prod_editar")
                                        
                                        nueva_talla = st.text_input("Talla*:", 
                                                                  value=producto_data['Talla'],
                                                                  key="talla_editar")
                                        
                                        colores_actuales = ", ".join(producto_data['Colores']) if producto_data['Colores'] else ""
                                        nuevos_colores = st.text_area(
                                            "Colores* (separados por coma):",
                                            value=colores_actuales,
                                            key="colores_editar",
                                            help="Ingresa todos los colores disponibles separados por coma"
                                        )
                                    
                                    with col2:
                                        st.markdown("### Distribución del Stock")
                                        
                                        stock_actual_total = producto_data['Stock_Bodega'] + producto_data['Stock_Exhibido']
                                        ventas_actuales = producto_data['Ventas_Total']
                                        
                                        col_stock1, col_stock2 = st.columns(2)
                                        with col_stock1:
                                            nuevo_stock_bodega = st.number_input(
                                                "Stock en Bodega:",
                                                min_value=0,
                                                value=int(producto_data['Stock_Bodega']),
                                                step=1,
                                                key="stock_bodega_editar"
                                            )
                                        
                                        with col_stock2:
                                            nuevo_stock_exhibido = st.number_input(
                                                "Stock en Exhibido:",
                                                min_value=0,
                                                value=int(producto_data['Stock_Exhibido']),
                                                step=1,
                                                key="stock_exhibido_editar"
                                            )
                                        
                                        nuevo_stock_total = nuevo_stock_bodega + nuevo_stock_exhibido
                                        
                                        if nuevo_stock_total < 0:
                                            st.error("El stock total no puede ser negativo")
                                        elif nuevo_stock_total < ventas_actuales:
                                            st.error(f"No puedes reducir el stock por debajo de las ventas ({ventas_actuales})")
                                        else:
                                            if nuevo_stock_bodega > nuevo_stock_exhibido:
                                                nueva_ubicacion = "Bodega"
                                            elif nuevo_stock_exhibido > nuevo_stock_bodega:
                                                nueva_ubicacion = "Exhibido"
                                            else:
                                                nueva_ubicacion = "Exhibido"
                                            
                                            st.info(f"Nuevo stock total: {nuevo_stock_total}")
                                            st.info(f"Nueva ubicación: {nueva_ubicacion}")
                                        
                                        st.markdown("### Precios")
                                        nuevo_precio_sugerido = st.number_input("Precio Sugerido ($):", 
                                                                              min_value=0.0, 
                                                                              value=float(producto_data['Precio_Sugerido']),
                                                                              step=0.01,
                                                                              format="%.2f",
                                                                              key="precio_sug_editar")
                                        
                                        nuevo_precio_venta = st.number_input("Precio Venta ($):", 
                                                                            min_value=0.0, 
                                                                            value=float(producto_data['Precio_Venta']),
                                                                            step=0.01,
                                                                            format="%.2f",
                                                                            key="precio_venta_editar")
                                    
                                    with st.expander("Información actual", expanded=False):
                                        col_act1, col_act2 = st.columns(2)
                                        with col_act1:
                                            st.write(f"Ventas totales: {ventas_actuales}")
                                            st.write(f"Entrada total: {producto_data['Entrada_Total']}")
                                            st.write(f"Stock total actual: {stock_actual_total}")
                                        with col_act2:
                                            st.write(f"Ubicación principal: {producto_data['Ubicacion']}")
                                            st.write(f"Bodega actual: {producto_data['Stock_Bodega']}")
                                            st.write(f"Exhibido actual: {producto_data['Stock_Exhibido']}")
                                    
                                    st.caption("(*) Campos obligatorios")
                                    
                                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                                    
                                    with col_btn1:
                                        guardar = st.form_submit_button("Guardar Cambios", type="primary", use_container_width=True)
                                    
                                    with col_btn2:
                                        solo_precios = st.form_submit_button("Solo Cambiar Precios", use_container_width=True)
                                    
                                    with col_btn3:
                                        if st.form_submit_button("Cancelar", use_container_width=True):
                                            st.session_state.modo_edicion = None
                                            st.rerun()
                                    
                                    if solo_precios:
                                        producto_data['Precio_Sugerido'] = float(nuevo_precio_sugerido)
                                        producto_data['Precio_Venta'] = float(nuevo_precio_venta)
                                        guardar_inventario()
                                        st.success("Precios actualizados correctamente")
                                        st.session_state.modo_edicion = None
                                        st.rerun()
                                    
                                    if guardar:
                                        if not nuevo_producto or not nueva_talla or not nuevos_colores:
                                            st.error("Completa los campos obligatorios (*)")
                                        elif nuevo_stock_total < 0:
                                            st.error("El stock total no puede ser negativo")
                                        elif nuevo_stock_total < ventas_actuales:
                                            st.error(f"No puedes reducir el stock por debajo de las ventas ({ventas_actuales})")
                                        else:
                                            colores_lista = [c.strip() for c in nuevos_colores.split(',') if c.strip()]
                                            if not colores_lista:
                                                colores_lista = ['Sin color']
                                            
                                            producto_data['Categoria'] = nueva_categoria
                                            producto_data['Producto'] = nuevo_producto
                                            producto_data['Talla'] = nueva_talla
                                            producto_data['Colores'] = colores_lista
                                            producto_data['Stock_Bodega'] = nuevo_stock_bodega
                                            producto_data['Stock_Exhibido'] = nuevo_stock_exhibido
                                            producto_data['Stock_Total'] = nuevo_stock_total
                                            producto_data['Precio_Sugerido'] = float(nuevo_precio_sugerido)
                                            producto_data['Precio_Venta'] = float(nuevo_precio_venta)
                                            producto_data['Ubicacion'] = nueva_ubicacion
                                            producto_data['Entrada_Total'] = nuevo_stock_total + ventas_actuales
                                            
                                            guardar_inventario()
                                            st.success("Producto actualizado correctamente")
                                            st.session_state.modo_edicion = None
                                            st.rerun()
                
                # MODO: ELIMINAR PRODUCTO
                elif st.session_state.modo_edicion == 'eliminar':
                    st.subheader("Eliminar Producto")
                    
                    if df.empty or len(st.session_state.inventario) == 0:
                        st.info("No hay productos para eliminar.")
                    else:
                        productos_eliminar = {f"{row['Producto']} ({row['Talla']}) - Ventas: {row['Ventas_Total']}": row['ID'] 
                                            for _, row in df.iterrows()}
                        
                        producto_eliminar = st.selectbox(
                            "Selecciona un producto para eliminar:",
                            list(productos_eliminar.keys()),
                            key="select_eliminar"
                        )
                        
                        if producto_eliminar:
                            producto_id = productos_eliminar[producto_eliminar]
                            producto_data = next((item for item in st.session_state.inventario 
                                                if item['ID'] == producto_id), None)
                            
                            if producto_data:
                                st.warning(f"¿Estás seguro de eliminar {producto_data['Producto']}?")
                                
                                if producto_data['Ventas_Total'] > 0:
                                    st.error(f"ADVERTENCIA: Este producto tiene {producto_data['Ventas_Total']} ventas registradas.")
                                
                                col_info1, col_info2 = st.columns(2)
                                with col_info1:
                                    st.write(f"Categoría: {producto_data['Categoria']}")
                                    st.write(f"Talla: {producto_data['Talla']}")
                                    st.write(f"Ubicación: {producto_data['Ubicacion']}")
                                with col_info2:
                                    colores_text = ", ".join(producto_data['Colores']) if producto_data['Colores'] else "Sin color"
                                    st.write(f"Colores: {colores_text}")
                                    st.write(f"Precio Venta: ${producto_data['Precio_Venta']:,.2f}")
                                    st.write(f"Ventas: {producto_data['Ventas_Total']}")
                                
                                col_conf1, col_conf2, col_conf3 = st.columns([1, 1, 2])
                                
                                with col_conf1:
                                    if st.button("Sí, Eliminar", type="primary", use_container_width=True):
                                        success, message = eliminar_producto(producto_id)
                                        if success:
                                            st.success(message)
                                            st.session_state.modo_edicion = None
                                            st.rerun()
                                        else:
                                            st.error(message)
                                
                                with col_conf2:
                                    if st.button("Cancelar", use_container_width=True):
                                        st.session_state.modo_edicion = None
                                        st.rerun()
                
                # MODO: VER INVENTARIO
                else:
                    st.subheader("Inventario Actual")
                    
                    if df.empty or len(st.session_state.inventario) == 0:
                        st.info("No hay productos en el inventario.")
                    else:
                        col_res1, col_res2, col_res3 = st.columns(3)
                        with col_res1:
                            st.metric("Total Productos", len(df))
                        with col_res2:
                            valor_inventario = (df['Stock_Total'] * df['Precio_Venta']).sum()
                            st.metric("Valor Inventario", f"${valor_inventario:,.2f}")
                        with col_res3:
                            productos_con_stock = len(df[df['Stock_Total'] > 0])
                            st.metric("Productos con Stock", f"{productos_con_stock}")
                        
                        search_inv = st.text_input("Buscar en inventario:", key="search_inv")
                        
                        if search_inv:
                            filtered_inv = df[
                                df['Producto'].str.contains(search_inv, case=False, na=False) |
                                df['Categoria'].str.contains(search_inv, case=False, na=False) |
                                df['Talla'].str.contains(search_inv, case=False, na=False) |
                                df['Ubicacion'].str.contains(search_inv, case=False, na=False)
                            ]
                        else:
                            filtered_inv = df
                        
                        if not filtered_inv.empty:
                            display_inv = filtered_inv.copy()
                            display_inv['Precio_Sugerido'] = display_inv['Precio_Sugerido'].apply(lambda x: f"${x:,.2f}")
                            display_inv['Precio_Venta'] = display_inv['Precio_Venta'].apply(lambda x: f"${x:,.2f}")
                            display_inv['Colores'] = display_inv['Colores'].apply(
                                lambda x: ", ".join(x) if isinstance(x, list) else str(x) if x else ""
                            )
                            
                            st.dataframe(
                                display_inv[['Categoria', 'Producto', 'Talla', 'Colores', 'Ubicacion',
                                           'Stock_Bodega', 'Stock_Exhibido', 'Stock_Total', 
                                           'Ventas_Total', 'Precio_Sugerido', 'Precio_Venta']],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    'Categoria': st.column_config.TextColumn("Categoría"),
                                    'Producto': st.column_config.TextColumn("Producto"),
                                    'Talla': st.column_config.TextColumn("Talla"),
                                    'Colores': st.column_config.TextColumn("Colores"),
                                    'Ubicacion': st.column_config.TextColumn("Ubicación"),
                                    'Stock_Bodega': st.column_config.NumberColumn("Bodega", format="%d"),
                                    'Stock_Exhibido': st.column_config.NumberColumn("Exhibido", format="%d"),
                                    'Stock_Total': st.column_config.NumberColumn("Total", format="%d"),
                                    'Ventas_Total': st.column_config.NumberColumn("Ventas", format="%d"),
                                    'Precio_Sugerido': st.column_config.TextColumn("Sugerido"),
                                    'Precio_Venta': st.column_config.TextColumn("Venta")
                                }
                            )
                        else:
                            st.info("No hay productos que coincidan con la búsqueda.")

if __name__ == "__main__":
    main()