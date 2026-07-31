import streamlit as st
import json
import os
import base64
import requests
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inventario de Ropa", page_icon="👕", layout="wide")

# --- DIAGNÓSTICO Y CONEXIÓN A GITHUB ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_NAME = st.secrets.get("REPO_NAME", "")

if not GITHUB_TOKEN:
    st.error("⚠️ FALTA CONFIGURAR 'GITHUB_TOKEN' EN LOS SECRETS DE STREAMLIT CLOUD.")
if not REPO_NAME:
    st.error("⚠️ FALTA CONFIGURAR 'REPO_NAME' EN LOS SECRETS DE STREAMLIT CLOUD.")

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def cargar_json(path_archivo, default_val):
    """Carga datos desde GitHub API si existe, o localmente como respaldo."""
    if GITHUB_TOKEN and REPO_NAME:
        try:
            url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path_archivo}"
            res = requests.get(url, headers=github_headers(), timeout=5)
            if res.status_code == 200:
                content = res.json().get("content", "")
                decoded = base64.b64decode(content).decode('utf-8')
                return json.loads(decoded)
        except Exception:
            pass
            
    if os.path.exists(path_archivo):
        try:
            with open(path_archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    return default_val

def guardar_json(path_archivo, datos, mensaje_commit="Actualización de datos"):
    """Guarda en archivo local y sube inmediatamente a GitHub."""
    os.makedirs(os.path.dirname(path_archivo), exist_ok=True)
    with open(path_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        
    if not GITHUB_TOKEN or not REPO_NAME:
        st.warning("⚠️ Guardado solo local. Faltan los Secrets de GitHub para sincronizar en la nube.")
        return False

    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path_archivo}"
    get_res = requests.get(url, headers=github_headers())
    sha = get_res.json().get("sha") if get_res.status_code == 200 else None
    
    content_bytes = json.dumps(datos, ensure_ascii=False, indent=2).encode('utf-8')
    content_b64 = base64.b64encode(content_bytes).decode('utf-8')
    
    payload = {
        "message": mensaje_commit,
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha
        
    put_res = requests.put(url, headers=github_headers(), json=payload)
    
    if put_res.status_code in [200, 201]:
        st.success(f"☁️ ¡Guardado y sincronizado en GitHub! ({path_archivo})")
        return True
    else:
        err_msg = put_res.json().get("message", "Error desconocido")
        st.error(f"❌ Error de sincronización GitHub [{put_res.status_code}]: {err_msg}")
        return False

# --- CONFIGURACIÓN DE RUTAS Y ESTRUCTURAS POR DEFECTO ---
RUTA_INV = "data/inventario.json"
RUTA_VENTAS = "data/ventas.json"
RUTA_APARTADOS = "data/apartados.json"
RUTA_CAMBIOS = "data/cambios.json"

INVENTARIO_DEFAULT = {
    "Chamarras": [],
    "Jeans": [],
    "Playeras": [],
    "Shorts": [],
    "Niño": [],
    "Bermudas": []
}

# --- CARGA Y VALIDACIÓN DE DATOS EN SESSION STATE ---
inv_cargado = cargar_json(RUTA_INV, INVENTARIO_DEFAULT)

# Garantizar que inventario sea estrictamente un diccionario
if not isinstance(inv_cargado, dict):
    inv_cargado = INVENTARIO_DEFAULT

# Asegurar que todas las categorías por defecto existan dentro del diccionario
for cat, items in INVENTARIO_DEFAULT.items():
    if cat not in inv_cargado or not isinstance(inv_cargado[cat], list):
        inv_cargado[cat] = []

if 'inventario' not in st.session_state or not isinstance(st.session_state.inventario, dict):
    st.session_state.inventario = inv_cargado

ventas_cargadas = cargar_json(RUTA_VENTAS, [])
if not isinstance(ventas_cargadas, list):
    ventas_cargadas = []
if 'ventas' not in st.session_state or not isinstance(st.session_state.ventas, list):
    st.session_state.ventas = ventas_cargadas

apartados_cargados = cargar_json(RUTA_APARTADOS, [])
if not isinstance(apartados_cargados, list):
    apartados_cargados = []
if 'apartados' not in st.session_state or not isinstance(st.session_state.apartados, list):
    st.session_state.apartados = apartados_cargados

cambios_cargados = cargar_json(RUTA_CAMBIOS, [])
if not isinstance(cambios_cargados, list):
    cambios_cargados = []
if 'cambios' not in st.session_state or not isinstance(st.session_state.cambios, list):
    st.session_state.cambios = cambios_cargados

# --- INTERFAZ PRINCIPAL ---
st.title("👕 Inventario de Ropa")

col_menu1, col_menu2, col_menu3, col_menu4, col_menu5, col_menu6 = st.columns(6)

with col_menu1:
    btn_venta = st.button("🛒 Venta", use_container_width=True)
with col_menu2:
    btn_cambios = st.button("🔄 Cambios", use_container_width=True)
with col_menu3:
    btn_apartados = st.button("📑 Apartados", use_container_width=True)
with col_menu4:
    btn_inv = st.button("📋 Inventario", use_container_width=True)
with col_menu5:
    btn_caja = st.button("💰 Caja", use_container_width=True)
with col_menu6:
    btn_admin = st.button("🔐 Admin", use_container_width=True)

if 'vista' not in st.session_state:
    st.session_state.vista = "venta"

if btn_venta: st.session_state.vista = "venta"
if btn_cambios: st.session_state.vista = "cambios"
if btn_apartados: st.session_state.vista = "apartados"
if btn_inv: st.session_state.vista = "inventario"
if btn_caja: st.session_state.vista = "caja"
if btn_admin: st.session_state.vista = "admin"

st.divider()

# --- VISTA: REGISTRAR VENTAS ---
if st.session_state.vista == "venta":
    st.subheader("Registrar Ventas")
    
    categorias = list(st.session_state.inventario.keys())
    cat_sel = st.radio("Categoría:", categorias, horizontal=True)
    
    productos = st.session_state.inventario.get(cat_sel, [])
    
    if not productos:
        st.info("No hay productos registrados en esta categoría.")
    else:
        opciones_prod = [f"{p['nombre']} | Color: {p.get('color','N/A')} | Talla: {p.get('talla','N/A')} | ${p.get('precio',0)}" for p in productos]
        prod_idx = st.selectbox("Selecciona producto:", range(len(opciones_prod)), format_func=lambda x: opciones_prod[x])
        
        prod_sel = productos[prod_idx]
        st.write(f"**Stock disponible:** Vitrina ({prod_sel.get('stock_vitrina',0)}) | Bodega ({prod_sel.get('stock_bodega',0)})")
        
        origen_stock = st.radio("Descontar de:", ["Vitrina", "Bodega"], horizontal=True)
        cantidad = st.number_input("Cantidad a vender:", min_value=1, value=1)
        
        if st.button("🛒 Confirmar Venta", type="primary"):
            key_stock = 'stock_vitrina' if origen_stock == "Vitrina" else 'stock_bodega'
            if prod_sel[key_stock] >= cantidad:
                prod_sel[key_stock] -= cantidad
                
                registro_venta = {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "producto": prod_sel['nombre'],
                    "categoria": cat_sel,
                    "precio_unitario": prod_sel['precio'],
                    "cantidad": cantidad,
                    "total": prod_sel['precio'] * cantidad,
                    "origen": origen_stock
                }
                
                st.session_state.ventas.append(registro_venta)
                
                guardar_json(RUTA_INV, st.session_state.inventario, f"Venta de {prod_sel['nombre']}")
                guardar_json(RUTA_VENTAS, st.session_state.ventas, "Registro de nueva venta")
                
                st.balloons()
                st.rerun()
            else:
                st.error("Stock insuficiente para realizar la venta.")

# --- VISTA: CAMBIOS ---
elif st.session_state.vista == "cambios":
    st.subheader("🔄 Registrar Cambios o Devoluciones")
    prod_devuelto = st.text_input("Producto devuelto:")
    prod_nuevo = st.text_input("Producto entregado a cambio:")
    diferencia = st.number_input("Diferencia cobrada ($):", value=0.0)
    
    if st.button("💾 Guardar Cambio"):
        if prod_devuelto and prod_nuevo:
            registro_cambio = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "devuelto": prod_devuelto,
                "nuevo": prod_nuevo,
                "diferencia": diferencia
            }
            st.session_state.cambios.append(registro_cambio)
            guardar_json(RUTA_CAMBIOS, st.session_state.cambios, "Registro de cambio de producto")
            st.success("Cambio registrado correctamente.")
            st.rerun()

# --- VISTA: APARTADOS ---
elif st.session_state.vista == "apartados":
    st.subheader("📑 Gestión de Apartados")
    cliente = st.text_input("Nombre del cliente:")
    concepto = st.text_input("Producto(s) apartado(s):")
    total_apartado = st.number_input("Precio Total ($):", min_value=0.0, value=0.0)
    anticipo = st.number_input("Anticipo / Abono ($):", min_value=0.0, value=0.0)
    
    if st.button("💾 Crear Apartado"):
        if cliente and concepto:
            nuevo_apartado = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cliente": cliente,
                "concepto": concepto,
                "total": total_apartado,
                "abonado": anticipo,
                "restante": total_apartado - anticipo,
                "estado": "Pendiente"
            }
            st.session_state.apartados.append(nuevo_apartado)
            guardar_json(RUTA_APARTADOS, st.session_state.apartados, "Registro de nuevo apartado")
            st.success(f"Apartado registrado para {cliente}.")
            st.rerun()

    st.divider()
    st.write("### Historial de Apartados")
    if st.session_state.apartados:
        st.json(st.session_state.apartados)

# --- VISTA: INVENTARIO GENERAL ---
elif st.session_state.vista == "inventario":
    st.subheader("📋 Inventario General")
    st.json(st.session_state.inventario)

# --- VISTA: CAJA Y VENTAS ---
elif st.session_state.vista == "caja":
    st.subheader("💰 Resumen de Caja")
    total_ventas = sum(v.get('total', 0) for v in st.session_state.ventas)
    st.metric("Total acumulado en Ventas", f"${total_ventas:,.2f}")
    
    st.write("### Historial de Ventas")
    if st.session_state.ventas:
        st.dataframe(st.session_state.ventas)

# --- VISTA: ADMINISTRACIÓN ---
elif st.session_state.vista == "admin":
    st.subheader("🔐 Panel de Administración")
    
    pwd = st.text_input("Contraseña de Administrador:", type="password")
    
    if pwd == "michiotaku":
        st.success("Acceso concedido.")
        st.write("---")
        st.write("### ➕ Añadir Nuevo Producto")
        
        cat_destino = st.selectbox("Categoría:", list(st.session_state.inventario.keys()))
        nom_prod = st.text_input("Nombre del producto:")
        col_prod = st.text_input("Color:")
        talla_prod = st.selectbox("Talla:", ["XS", "S", "M", "L", "XL", "2XL", "30", "32", "34", "36", "Única"])
        precio_prod = st.number_input("Precio ($):", min_value=0.0, value=0.0)
        stk_vitrina = st.number_input("Stock inicial en Vitrina:", min_value=0, value=1)
        stk_bodega = st.number_input("Stock inicial en Bodega:", min_value=0, value=0)
        
        if st.button("💾 Guardar Producto", type="primary"):
            if nom_prod:
                nuevo_item = {
                    "nombre": nom_prod,
                    "color": col_prod,
                    "talla": talla_prod,
                    "precio": precio_prod,
                    "stock_vitrina": stk_vitrina,
                    "stock_bodega": stk_bodega
                }
                st.session_state.inventario[cat_destino].append(nuevo_item)
                
                guardar_json(RUTA_INV, st.session_state.inventario, f"Añadido producto {nom_prod}")
                
                st.success(f"¡Producto '{nom_prod}' guardado con éxito! Ya aparece en '{cat_destino}'.")
                st.rerun()
            else:
                st.warning("Por favor ingresa al menos el nombre del producto.")
