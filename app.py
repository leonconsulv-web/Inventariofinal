import datetime
import json
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Inventario y Ventas - Ropa Caballero",
    page_icon="👔",
    layout="wide",
)

# --- ARCHIVOS DE PERSISTENCIA ---
INVENTORY_FILE = "inventory.json"
SALES_FILE = "sales.json"
CATEGORIES_FILE = "categories.json"

DEFAULT_CATEGORIES = [
    "Camisas",
    "Playeras",
    "Suéteres",
    "Chamarras",
    "Pantalones",
    "Shorts",
    "Jeans",
    "Sacos y Trajes",
    "Niño",
]

DEFAULT_ADMIN_PASSWORD = "admin"  # Puedes cambiar la contraseña aquí


# --- FUNCIONES DE CARGA Y GUARDADO ---
def load_json(filename, default_data):
    if not os.path.exists(filename):
        save_json(filename, default_data)
        return default_data
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- INICIALIZACIÓN DEL ESTADO ---
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

inventory = load_json(INVENTORY_FILE, [])
sales = load_json(SALES_FILE, [])
categories = load_json(CATEGORIES_FILE, DEFAULT_CATEGORIES)


# --- NAVEGACIÓN Y AUTENTICACIÓN ---
st.sidebar.title("👔 Menú Principal")

# Control de Rol
role_option = st.sidebar.radio(
    "Selecciona Tu Rol:", ["👷 Trabajadora (Ventas)", "👑 Administradora"]
)

if role_option == "👑 Administradora":
    if not st.session_state["admin_authenticated"]:
        pwd = st.sidebar.text_input("Contraseña de Admin:", type="password")
        if st.sidebar.button("Ingresar"):
            if pwd == DEFAULT_ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.sidebar.success("Acceso concedido")
                st.rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")
else:
    st.session_state["admin_authenticated"] = False

# Selección de Vista
if (
    role_option == "👑 Administradora"
    and st.session_state["admin_authenticated"]
):
    menu = st.sidebar.selectbox(
        "Módulo:",
        [
            "🛍️ Registrar Venta",
            "📊 Corte de Caja y Reportes",
            "📦 Gestión de Inventario",
            "🏷️ Categorías",
        ],
    )
else:
    menu = st.sidebar.selectbox(
        "Módulo:", ["🛍️ Registrar Venta", "📊 Corte de Caja"]
    )


# ==========================================
# MÓDULO 1: REGISTRAR VENTA
# ==========================================
if menu == "🛍️ Registrar Venta":
    st.title("🛍️ Punto de Venta")
    st.caption("Selecciona una categoría para ver y vender productos.")

    # Filtro por categorías
    selected_cat = st.selectbox("Filtrar por Categoría:", ["Todas"] + categories)

    filtered_inventory = inventory
    if selected_cat != "Todas":
        filtered_inventory = [
            p for p in inventory if p.get("categoria") == selected_cat
        ]

    if not filtered_inventory:
        st.info("No hay productos disponibles en esta categoría.")
    else:
        for p in filtered_inventory:
            # Calcular stocks totales del producto
            total_exhibido = sum(
                var.get("exhibido", 0) for var in p.get("variantes", {}).values()
            )
            total_bodega = sum(
                var.get("bodega", 0) for var in p.get("variantes", {}).values()
            )

            status_color = "🟢" if (total_exhibido + total_bodega) >= 3 else "🔴"

            with st.expander(
                f"{status_color} {p['nombre']} (Talla: {p['talla']}) - ${p['precio_sugerido']:.2f}"
            ):
                col1, col2 = st.columns([2, 2])

                with col1:
                    st.write(f"**Categoría:** {p['categoria']}")
                    st.write(f"**Precio Sugerido:** ${p['precio_sugerido']:.2f}")

                    # Mostrar tabla de variantes y stock
                    var_df = []
                    for color, stks in p.get("variantes", {}).items():
                        var_df.append(
                            {
                                "Color": color,
                                "Exhibido": stks.get("exhibido", 0),
                                "Bodega": stks.get("bodega", 0),
                            }
                        )
                    if var_df:
                        st.dataframe(pd.DataFrame(var_df), use_container_width=True)

                with col2:
                    st.subheader("Registrar Salida")
                    available_colors = [
                        c
                        for c, s in p.get("variantes", {}).items()
                        if (s.get("exhibido", 0) + s.get("bodega", 0)) > 0
                    ]

                    if not available_colors:
                        st.error("❌ Producto Agotado en todos los colores.")
                    else:
                        chosen_color = st.selectbox(
                            f"Color para {p['id']}:",
                            available_colors,
                            key=f"col_{p['id']}",
                        )
                        sale_price = st.number_input(
                            f"Precio Real Venta ($):",
                            min_value=0.0,
                            value=float(p["precio_sugerido"]),
                            step=10.0,
                            key=f"price_{p['id']}",
                        )
                        payment_method = st.selectbox(
                            "Método de Pago:",
                            ["Efectivo", "Tarjeta", "Transferencia"],
                            key=f"pay_{p['id']}",
                        )

                        curr_exhibido = p["variantes"][chosen_color].get(
                            "exhibido", 0
                        )
                        curr_bodega = p["variantes"][chosen_color].get(
                            "bodega", 0
                        )

                        if st.button("Vender 1 Unidad", key=f"btn_{p['id']}"):
                            location_used = ""
                            # Regla: Prioridad Exhibido -> luego Bodega
                            if curr_exhibido > 0:
                                p["variantes"][chosen_color]["exhibido"] -= 1
                                location_used = "Exhibido"
                            elif curr_bodega > 0:
                                p["variantes"][chosen_color]["bodega"] -= 1
                                location_used = "Bodega"

                            # Crear Registro de Venta
                            new_sale = {
                                "id_venta": f"VEN_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                "fecha": datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "producto_id": p["id"],
                                "producto_nombre": p["nombre"],
                                "categoria": p["categoria"],
                                "talla": p["talla"],
                                "color": chosen_color,
                                "precio_sugerido": p["precio_sugerido"],
                                "precio_venta": sale_price,
                                "precio_costo": p.get("precio_costo", 0.0),
                                "metodo_pago": payment_method,
                                "ubicacion_descuento": location_used,
                            }

                            sales.append(new_sale)
                            save_json(INVENTORY_FILE, inventory)
                            save_json(SALES_FILE, sales)

                            st.success(
                                f"✅ ¡Venta registrada! 1 unidad de {p['nombre']} ({chosen_color}) cobrada en ${sale_price:.2f} [{payment_method}]."
                            )
                            st.rerun()


# ==========================================
# MÓDULO 2: CORTE DE CAJA Y REPORTES
# ==========================================
elif menu in ["📊 Corte de Caja", "📊 Corte de Caja y Reportes"]:
    st.title("📊 Corte de Caja e Historial")

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # Filtrar ventas de hoy
    today_sales = [
        s for s in sales if s.get("fecha", "").startswith(today_str)
    ]

    st.subheader(f"Corte del Día ({today_str})")

    if not today_sales:
        st.info("Aún no hay ventas registradas el día de hoy.")
    else:
        df_today = pd.DataFrame(today_sales)

        total_recaudado = df_today["precio_venta"].sum()
        total_articulos = len(df_today)
        ganancia_estimada = (
            df_today["precio_venta"] - df_today["precio_costo"]
        ).sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Ingresos Hoy", f"${total_recaudado:,.2f}")
        m2.metric("Prendas Vendidas", f"{total_articulos} pcs")
        if (
            role_option == "👑 Administradora"
            and st.session_state["admin_authenticated"]
        ):
            m3.metric("Ganancia Neta Hoy", f"${ganancia_estimada:,.2f}")

        st.markdown("---")
        st.write("### Desglose por Método de Pago")
        pay_summary = (
            df_today.groupby("metodo_pago")["precio_venta"]
            .agg(["sum", "count"])
            .reset_index()
        )
        pay_summary.columns = ["Método", "Total ($)", "Cantidad Ventas"]
        st.table(pay_summary)

        st.write("### Detalle de Ventas de Hoy")
        st.dataframe(
            df_today[
                [
                    "fecha",
                    "producto_nombre",
                    "talla",
                    "color",
                    "precio_sugerido",
                    "precio_venta",
                    "metodo_pago",
                ]
            ],
            use_container_width=True,
        )

    # Dashboard Completo solo para la Administradora
    if (
        role_option == "👑 Administradora"
        and st.session_state["admin_authenticated"]
        and sales
    ):
        st.markdown("---")
        st.header("📈 Reportes Generales de Negocio")

        df_all = pd.DataFrame(sales)

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("Ventas por Categoría")
            cat_fig = px.pie(
                df_all, names="categoria", values="precio_venta", hole=0.4
            )
            st.plotly_chart(cat_fig, use_container_width=True)

        with col_g2:
            st.subheader("Ventas por Método de Pago")
            pay_fig = px.bar(
                df_all,
                x="metodo_pago",
                y="precio_venta",
                color="metodo_pago",
                title="Ingresos Totales",
            )
            st.plotly_chart(pay_fig, use_container_width=True)

        # Descargas de Reportes
        st.subheader("📥 Exportación de Datos")
        csv_sales = df_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar Historial de Ventas (CSV)",
            data=csv_sales,
            file_name=f"reporte_ventas_{today_str}.csv",
            mime="text/csv",
        )


# ==========================================
# MÓDULO 3: GESTIÓN DE INVENTARIO (ADMIN)
# ==========================================
elif menu == "📦 Gestión de Inventario":
    st.title("📦 Gestión Integral de Inventario")

    tab1, tab2, tab3 = st.tabs(
        ["➕ Agregar Producto", "✏️ Editar / Mover Stock", "🗑️ Eliminar / Lista"]
    )

    # --- TAB 1: AGREGAR PRODUCTO ---
    with tab1:
        st.subheader("Nuevo Producto")
        with st.form("form_add_product"):
            cat = st.selectbox("Categoría:", categories)
            name = st.text_input("Nombre del Producto (Ej: Camisa Oxford):")
            size = st.text_input("Talla (Ej: M, 32, Unitalla):")

            col_p1, col_p2 = st.columns(2)
            cost_p = col_p1.number_input("Precio Costo ($):", min_value=0.0)
            sugg_p = col_p2.number_input("Precio Sugerido ($):", min_value=0.0)

            st.markdown("---")
            st.write("**Variantes de Color y Stock Inicial**")
            colors_input = st.text_input(
                "Colores disponibles (separados por coma, Ej: Azul, Blanco, Negro):"
            )

            bodega_init = st.number_input(
                "Stock Inicial por Color en Bodega:", min_value=0, value=5
            )
            exhibido_init = st.number_input(
                "Stock Inicial por Color en Exhibición:", min_value=0, value=5
            )

            submit_add = st.form_submit_button("Guardar Producto")

            if submit_add:
                if not name or not colors_input:
                    st.error("Por favor completa el nombre y los colores.")
                else:
                    color_list = [
                        c.strip().capitalize()
                        for c in colors_input.split(",")
                        if c.strip()
                    ]
                    variantes_dict = {}
                    for col in color_list:
                        variantes_dict[col] = {
                            "bodega": int(bodega_init),
                            "exhibido": int(exhibido_init),
                        }

                    new_prod = {
                        "id": f"PROD_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "categoria": cat,
                        "nombre": name,
                        "talla": size,
                        "precio_costo": float(cost_p),
                        "precio_sugerido": float(sugg_p),
                        "variantes": variantes_dict,
                    }

                    inventory.append(new_prod)
                    save_json(INVENTORY_FILE, inventory)
                    st.success(
                        f"¡Producto '{name}' registrado exitosamente!"
                    )
                    st.rerun()

    # --- TAB 2: EDITAR / MOVER STOCK ---
    with tab2:
        st.subheader("Ajustar Stock y Precios")
        if not inventory:
            st.info("No hay productos en inventario.")
        else:
            prod_titles = {
                f"{p['nombre']} (Talla: {p['talla']}) - ID: {p['id']}": p
                for p in inventory
            }
            selected_prod_title = st.selectbox(
                "Selecciona Producto a Modificar:", list(prod_titles.keys())
            )
            prod = prod_titles[selected_prod_title]

            st.write(f"**Modificando:** {prod['nombre']}")

            col_e1, col_e2 = st.columns(2)
            new_cost = col_e1.number_input(
                "Precio Costo ($)",
                value=float(prod.get("precio_costo", 0.0)),
                key="edit_cost",
            )
            new_sugg = col_e2.number_input(
                "Precio Sugerido ($)",
                value=float(prod.get("precio_sugerido", 0.0)),
                key="edit_sugg",
            )

            st.write("---")
            st.write("**Ajustar Stock por Color**")

            updated_variantes = prod.get("variantes", {})
            for color, stks in list(updated_variantes.items()):
                st.markdown(f"**Color: {color}**")
                ce1, ce2 = st.columns(2)
                b_val = ce1.number_input(
                    f"Bodega ({color}):",
                    min_value=0,
                    value=int(stks.get("bodega", 0)),
                    key=f"eb_{prod['id']}_{color}",
                )
                e_val = ce2.number_input(
                    f"Exhibido ({color}):",
                    min_value=0,
                    value=int(stks.get("exhibido", 0)),
                    key=f"ee_{prod['id']}_{color}",
                )
                updated_variantes[color] = {"bodega": b_val, "exhibido": e_val}

            # Opción para agregar nuevo color
            new_col_name = st.text_input(
                "Agregar un nuevo color a este producto:",
                key=f"ncol_{prod['id']}",
            )
            if st.button("Añadir Color") and new_col_name:
                updated_variantes[new_col_name.strip().capitalize()] = {
                    "bodega": 0,
                    "exhibido": 0,
                }
                save_json(INVENTORY_FILE, inventory)
                st.rerun()

            if st.button("Guardar Cambios de Producto"):
                prod["precio_costo"] = new_cost
                prod["precio_sugerido"] = new_sugg
                prod["variantes"] = updated_variantes
                save_json(INVENTORY_FILE, inventory)
                st.success("¡Producto actualizado correctamente!")
                st.rerun()

    # --- TAB 3: ELIMINAR / VISTA GENERAL ---
    with tab3:
        st.subheader("Lista Completa de Inventario")

        if inventory:
            # Aplanar datos para tabla
            flat_data = []
            for p in inventory:
                for color, stks in p.get("variantes", {}).items():
                    flat_data.append(
                        {
                            "ID": p["id"],
                            "Categoría": p["categoria"],
                            "Producto": p["nombre"],
                            "Talla": p["talla"],
                            "Color": color,
                            "Stock Bodega": stks.get("bodega", 0),
                            "Stock Exhibido": stks.get("exhibido", 0),
                            "Total": stks.get("bodega", 0)
                            + stks.get("exhibido", 0),
                            "Precio Costo": p.get("precio_costo", 0.0),
                            "Precio Sugerido": p.get("precio_sugerido", 0.0),
                        }
                    )

            df_inv = pd.DataFrame(flat_data)
            st.dataframe(df_inv, use_container_width=True)

            # Exportar inventario
            csv_inv = df_inv.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Descargar Inventario (CSV)",
                data=csv_inv,
                file_name="inventario_completo.csv",
                mime="text/csv",
            )

            st.markdown("---")
            st.subheader("Eliminar Producto")
            prod_to_del = st.selectbox(
                "Selecciona producto a borrar:",
                [f"{p['nombre']} ({p['talla']}) - {p['id']}" for p in inventory],
            )

            if st.button("Eliminar Producto Seleccionado"):
                target_id = prod_to_del.split(" - ")[-1]
                inventory = [p for p in inventory if p["id"] != target_id]
                save_json(INVENTORY_FILE, inventory)
                st.warning("Producto eliminado del inventario.")
                st.rerun()


# ==========================================
# MÓDULO 4: GESTIÓN DE CATEGORÍAS (ADMIN)
# ==========================================
elif menu == "🏷️ Categorías":
    st.title("🏷️ Administración de Categorías")

    st.write("### Categorías Actuales")
    st.write(", ".join(categories))

    st.markdown("---")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.subheader("Agregar Categoría")
        new_cat = st.text_input("Nombre de la nueva categoría:")
        if st.button("Guardar Categoría"):
            if new_cat and new_cat not in categories:
                categories.append(new_cat.strip())
                save_json(CATEGORIES_FILE, categories)
                st.success(f"Categoría '{new_cat}' agregada.")
                st.rerun()

    with col_c2:
        st.subheader("Eliminar Categoría")
        cat_to_remove = st.selectbox("Seleccionar categoría:", categories)
        if st.button("Eliminar Categoría"):
            # Verificar si hay productos asociados
            prods_in_cat = [
                p for p in inventory if p.get("categoria") == cat_to_remove
            ]
            if prods_in_cat:
                st.error(
                    f"No se puede eliminar: Hay {len(prods_in_cat)} productos asociados a esta categoría."
                )
            else:
                categories.remove(cat_to_remove)
                save_json(CATEGORIES_FILE, categories)
                st.success("Categoría eliminada.")
                st.rerun()
