import streamlit as st
import requests
import json
from PIL import Image
from io import BytesIO
import base64

# Configuración
st.set_page_config(
    page_title="Bsale ↔ Shopify Sync",
    page_icon="🔄",
    layout="wide"
)

# URLs
BSALE_API_URL = "https://api.bsale.io/v1"
SHOPIFY_API_VERSION = "2024-01"

def get_bsale_headers():
    """Obtener headers de Bsale desde session_state (actualizados)"""
    token = st.session_state.get("bsale_token", "")
    return {
        "access_token": token,
        "Content-Type": "application/json"
    }

def get_shopify_headers():
    """Obtener headers de Shopify desde session_state (actualizados)"""
    token = st.session_state.get("shopify_token", "")
    return {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }

def get_shopify_url():
    """Obtener URL de Shopify desde session_state"""
    shop = st.session_state.get("shopify_shop", "morekashop1")
    return f"https://{shop}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}"

# ==================== FUNCIONES Bsale ====================

def get_bsale_products(limit=100, offset=0):
    """Obtener productos de Bsale"""
    url = f"{BSALE_API_URL}/products.json?limit={limit}&offset={offset}&expand=[variants,product_type]"
    response = requests.get(url, headers=get_bsale_headers())
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"Error Bsale productos: {response.status_code} - {response.text[:200]}")
    return []

def get_bsale_variants(product_id):
    """Obtener variantes de un producto Bsale"""
    url = f"{BSALE_API_URL}/products/{product_id}/variants.json"
    response = requests.get(url, headers=get_bsale_headers())
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def get_bsale_variant_detail(variant_id):
    """Obtener detalle de una variante Bsale"""
    url = f"{BSALE_API_URL}/variants/{variant_id}.json"
    response = requests.get(url, headers=get_bsale_headers())
    if response.status_code == 200:
        return response.json()
    return {}

def update_bsale_variant_web(variant_id, web_name, web_description, web_active=True):
    """Actualizar campos web de una variante Bsale"""
    url = f"{BSALE_API_URL}/variants/{variant_id}.json"
    data = {
        "webName": web_name,
        "webDescription": web_description,
        "webActive": web_active
    }
    response = requests.put(url, headers=get_bsale_headers(), json=data)
    return response.status_code == 200, response.json() if response.status_code == 200 else response.text

def upload_bsale_image_to_variant(variant_id, image_url):
    """Subir imagen a una variante Bsale desde URL"""
    try:
        img_response = requests.get(image_url, timeout=15)
        if img_response.status_code != 200:
            return False, f"No se pudo descargar imagen: {img_response.status_code}"
        
        img_base64 = base64.b64encode(img_response.content).decode('utf-8')
        
        url = f"{BSALE_API_URL}/variants/{variant_id}/images.json"
        data = {
            "filename": f"image_{variant_id}.jpg",
            "base64": img_base64
        }
        response = requests.post(url, headers=get_bsale_headers(), json=data, timeout=30)
        return response.status_code == 201, response.json() if response.status_code == 201 else response.text
    except Exception as e:
        return False, str(e)

def get_product_with_web_status(product):
    """Obtener producto con estado web agregado"""
    product_id = product["id"]
    product_name = product.get("name", "Sin nombre")
    
    # Obtener variantes
    variants = get_bsale_variants(product_id)
    
    # Verificar estado web de cada variante
    variants_web = []
    has_any_web_desc = False
    all_have_web_desc = True
    any_web_active = False
    
    for variant in variants:
        variant_id = variant["id"]
        detail = get_bsale_variant_detail(variant_id)
        
        web_desc = detail.get("webDescription", "").strip()
        web_name = detail.get("webName", "").strip()
        web_active = detail.get("webActive", False)
        web_image = detail.get("webImage", "")
        
        if web_desc:
            has_any_web_desc = True
        else:
            all_have_web_desc = False
        
        if web_active:
            any_web_active = True
        
        variants_web.append({
            "id": variant_id,
            "sku": variant.get("code", "N/A"),
            "variant_name": variant.get("description", "Sin nombre"),
            "has_web_description": bool(web_desc),
            "web_description": web_desc,
            "web_name": web_name,
            "web_active": web_active,
            "has_web_image": bool(web_image),
            "web_image_url": web_image,
            "web_price": detail.get("webPrice", 0)
        })
    
    return {
        "id": product_id,
        "name": product_name,
        "product_type": product.get("product_type", {}).get("name", "Sin categoría"),
        "variants_count": len(variants),
        "has_any_web_description": has_any_web_desc,
        "all_have_web_description": all_have_web_desc,
        "any_web_active": any_web_active,
        "variants": variants_web
    }

# ==================== FUNCIONES Shopify ====================

def search_shopify_products(query, limit=50):
    """Buscar productos en Shopify"""
    url = f"{get_shopify_url()}/products.json?title={query}&limit={limit}"
    response = requests.get(url, headers=get_shopify_headers())
    if response.status_code == 200:
        return response.json().get("products", [])
    else:
        st.error(f"Error Shopify: {response.status_code} - {response.text[:300]}")
    return []

def get_shopify_product(product_id):
    """Obtener producto específico de Shopify"""
    url = f"{get_shopify_url()}/products/{product_id}.json"
    response = requests.get(url, headers=get_shopify_headers())
    if response.status_code == 200:
        return response.json().get("product", {})
    return {}

# ==================== UI ====================

def main():
    st.title("🔄 Bsale ↔ Shopify Sync")
    st.markdown("Verifica descripción web de productos Bsale y sincroniza con Shopify")
    
    # Sidebar - Configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Bsale
        st.subheader("Bsale")
        bsale_token = st.text_input(
            "Access Token Bsale",
            value=st.session_state.get("bsale_token", st.secrets.get("bsale", {}).get("access_token", "")),
            type="password"
        )
        
        # Shopify
        st.subheader("Shopify")
        shopify_token = st.text_input(
            "Access Token Shopify",
            value=st.session_state.get("shopify_token", st.secrets.get("shopify", {}).get("MOREKA_ACCESS_TOKEN", "")),
            type="password"
        )
        shopify_shop = st.text_input(
            "Shop Name",
            value=st.session_state.get("shopify_shop", st.secrets.get("shopify", {}).get("shop_name", "morekashop1"))
        )
        
        if st.button("💾 Guardar Configuración"):
            st.session_state.bsale_token = bsale_token
            st.session_state.shopify_token = shopify_token
            st.session_state.shopify_shop = shopify_shop
            st.success("✅ Configuración guardada")
            st.rerun()
    
    # Verificar credenciales
    bsale_token = st.session_state.get("bsale_token", "")
    shopify_token = st.session_state.get("shopify_token", "")
    
    if not bsale_token:
        st.warning("⚠️ Configura el Access Token de Bsale en el sidebar")
        return
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📦 Productos Bsale", "🔍 Buscar en Shopify", "🔄 Sincronizar"])
    
    # ==================== TAB 1: Productos Bsale (por producto) ====================
    with tab1:
        st.header("📦 Productos Bsale - Estado Web")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_bsale = st.text_input("🔍 Buscar producto (nombre)", "")
        with col2:
            filter_status = st.selectbox(
                "Filtrar por estado",
                ["Todos", "Sin descripción web", "Con descripción web (algunas)", "Todas las variantes tienen desc", "Web activo"]
            )
        with col3:
            limit = st.selectbox("Productos por página", [25, 50, 100], index=1)
        
        if st.button("📥 Cargar Productos Bsale", type="primary"):
            with st.spinner("Cargando productos y verificando estado web..."):
                products_raw = get_bsale_products(limit=limit)
                
                enriched_products = []
                for product in products_raw:
                    enriched = get_product_with_web_status(product)
                    enriched_products.append(enriched)
                
                st.session_state.bsale_products = enriched_products
                st.success(f"✅ {len(enriched_products)} productos cargados")
        
        # Mostrar productos
        if "bsale_products" in st.session_state:
            products = st.session_state.bsale_products
            
            # Aplicar filtros
            filtered = products
            if search_bsale:
                filtered = [p for p in filtered if search_bsale.lower() in p["name"].lower()]
            
            if filter_status == "Sin descripción web":
                filtered = [p for p in filtered if not p["has_any_web_description"]]
            elif filter_status == "Con descripción web (algunas)":
                filtered = [p for p in filtered if p["has_any_web_description"] and not p["all_have_web_description"]]
            elif filter_status == "Todas las variantes tienen desc":
                filtered = [p for p in filtered if p["all_have_web_description"]]
            elif filter_status == "Web activo":
                filtered = [p for p in filtered if p["any_web_active"]]
            
            st.write(f"Mostrando **{len(filtered)}** de **{len(products)}** productos")
            
            for product in filtered:
                with st.container():
                    # Card de producto
                    col_main, col_action = st.columns([4, 1])
                    
                    with col_main:
                        # Estado visual
                        if product["all_have_web_description"]:
                            st.success(f"✅ **{product['name']}**")
                        elif product["has_any_web_description"]:
                            st.warning(f"⚠️ **{product['name']}** (algunas variantes)")
                        else:
                            st.error(f"❌ **{product['name']}** (sin descripción web)")
                        
                        st.caption(f"Tipo: {product['product_type']} | Variantes: {product['variants_count']}")
                        
                        # Expandir para ver variantes
                        with st.expander(f"Ver {product['variants_count']} variantes"):
                            for variant in product["variants"]:
                                cols = st.columns([1, 1, 1, 1])
                                with cols[0]:
                                    st.write(f"**{variant['variant_name']}**")
                                    st.caption(f"SKU: {variant['sku']}")
                                with cols[1]:
                                    if variant["has_web_description"]:
                                        st.success("✅ Desc. web")
                                        if variant["web_description"]:
                                            st.caption(f"_{variant['web_description'][:50]}..._")
                                    else:
                                        st.error("❌ Sin desc. web")
                                with cols[2]:
                                    if variant["web_active"]:
                                        st.success("🟢 Activo")
                                    else:
                                        st.warning("🔴 Inactivo")
                                with cols[3]:
                                    if variant["has_web_image"]:
                                        st.success("🖼️ Imagen")
                                    else:
                                        st.error("❌ Sin imagen")
                                st.divider()
                    
                    with col_action:
                        if not product["all_have_web_description"]:
                            if st.button("🔍 Buscar en Shopify", key=f"search_{product['id']}"):
                                st.session_state.selected_bsale_product = product
                                st.session_state.shopify_search_query = product["name"]
                                st.session_state.active_tab = 1  # Ir a tab 2
                                st.rerun()
                        else:
                            st.info("✅ Completo")
                    
                    st.divider()
    
    # ==================== TAB 2: Buscar en Shopify ====================
    with tab2:
        st.header("🔍 Buscar Productos en Shopify")
        
        if not shopify_token:
            st.warning("⚠️ Configura el Access Token de Shopify en el sidebar")
        else:
            search_query = st.text_input(
                "Buscar producto en Shopify",
                value=st.session_state.get("shopify_search_query", ""),
                key="shopify_search_input"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔍 Buscar en Shopify") and search_query:
                    with st.spinner("Buscando..."):
                        shopify_products = search_shopify_products(search_query)
                        st.session_state.shopify_results = shopify_products
            
            if "shopify_results" in st.session_state:
                shopify_products = st.session_state.shopify_results
                
                if not shopify_products:
                    st.info("No se encontraron productos. Probá con otro término.")
                else:
                    st.success(f"✅ {len(shopify_products)} productos encontrados")
                    
                    for product in shopify_products:
                        with st.container():
                            col_img, col_info, col_select = st.columns([1, 2, 1])
                            
                            with col_img:
                                if product.get("images"):
                                    st.image(product["images"][0]["src"], width=150)
                                else:
                                    st.write("Sin imagen")
                            
                            with col_info:
                                st.write(f"**{product['title']}**")
                                st.caption(f"Handle: {product['handle']}")
                                
                                # Descripción
                                if product.get("body_html"):
                                    with st.expander("Ver descripción"):
                                        st.write(product["body_html"], unsafe_allow_html=True)
                                else:
                                    st.caption("Sin descripción")
                                
                                # Variantes
                                if product.get("variants"):
                                    st.caption(f"Variantes: {len(product['variants'])} | Precio: ${product['variants'][0].get('price', 'N/A')}")
                                
                                if product.get("tags"):
                                    st.caption(f"Tags: {', '.join(product['tags'][:3])}")
                            
                            with col_select:
                                if st.button("➡️ Seleccionar", key=f"select_{product['id']}"):
                                    st.session_state.selected_shopify_product = product
                                    st.success("✅ Producto seleccionado")
                                    st.session_state.active_tab = 2  # Ir a tab 3
                                    st.rerun()
                            
                            st.divider()
    
    # ==================== TAB 3: Sincronización ====================
    with tab3:
        st.header("🔄 Sincronizar Bsale ← Shopify")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 Producto Bsale (Destino)")
            if "selected_bsale_product" in st.session_state:
                bp = st.session_state.selected_bsale_product
                
                if bp["all_have_web_description"]:
                    st.success(f"✅ {bp['name']}")
                elif bp["has_any_web_description"]:
                    st.warning(f"⚠️ {bp['name']}")
                else:
                    st.error(f"❌ {bp['name']}")
                
                st.caption(f"Tipo: {bp['product_type']} | Variantes: {bp['variants_count']}")
                
                # Mostrar variantes y cuáles faltan
                st.write("**Variantes:**")
                for variant in bp["variants"]:
                    status = "✅" if variant["has_web_description"] else "❌"
                    st.write(f"{status} {variant['variant_name']} (SKU: {variant['sku']})")
            else:
                st.info("Seleccioná un producto Bsale desde la pestaña 'Productos Bsale'")
        
        with col2:
            st.subheader("🛒 Producto Shopify (Origen)")
            if "selected_shopify_product" in st.session_state:
                sp = st.session_state.selected_shopify_product
                st.write(f"**{sp['title']}**")
                
                if sp.get("images"):
                    st.image(sp["images"][0]["src"], width=200)
                
                st.write("**Datos disponibles:**")
                st.write(f"- Título: ✅")
                st.write(f"- Descripción: {'✅' if sp.get('body_html') else '❌'}")
                st.write(f"- Imágenes: {'✅' if sp.get('images') else '❌'}")
                
                if sp.get("body_html"):
                    with st.expander("Ver descripción Shopify"):
                        st.write(sp["body_html"], unsafe_allow_html=True)
            else:
                st.info("Seleccioná un producto Shopify desde la pestaña 'Buscar en Shopify'")
        
        # Configuración de sync
        if "selected_bsale_product" in st.session_state and "selected_shopify_product" in st.session_state:
            st.write("---")
            st.subheader("⚙️ Opciones de Sincronización")
            
            bp = st.session_state.selected_bsale_product
            sp = st.session_state.selected_shopify_product
            
            # Seleccionar qué variantes sincronizar
            st.write("**Variantes a sincronizar:**")
            variants_to_sync = []
            for variant in bp["variants"]:
                if not variant["has_web_description"]:
                    if st.checkbox(f"Sincronizar: {variant['variant_name']} (SKU: {variant['sku']})", value=True, key=f"sync_{variant['id']}"):
                        variants_to_sync.append(variant)
            
            if not variants_to_sync:
                st.info("Todas las variantes ya tienen descripción web. No hay nada que sincronizar.")
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    sync_title = st.checkbox("Título (webName)", value=True)
                with col2:
                    sync_description = st.checkbox("Descripción (webDescription)", value=True)
                with col3:
                    sync_images = st.checkbox("Imágenes", value=True)
                
                activate_web = st.checkbox("Activar en web (webActive)", value=True)
                
                # Previsualización
                with st.expander("👁️ Previsualizar cambios"):
                    st.write(f"**Producto Bsale:** {bp['name']}")
                    st.write(f"**Origen Shopify:** {sp['title']}")
                    st.write(f"**Variantes a sincronizar:** {len(variants_to_sync)}")
                    for v in variants_to_sync:
                        st.write(f"- {v['variant_name']}: desc=❌ → ✅")
                
                # Ejecutar sync
                if st.button("🚀 Sincronizar Variantes Seleccionadas", type="primary"):
                    with st.spinner("Sincronizando..."):
                        results = []
                        
                        for variant in variants_to_sync:
                            variant_results = []
                            
                            # 1. Actualizar campos web
                            if sync_title or sync_description:
                                new_title = sp["title"] if sync_title else variant["web_name"]
                                new_desc = sp.get("body_html", "") if sync_description else variant["web_description"]
                                
                                success, result = update_bsale_variant_web(
                                    variant["id"],
                                    new_title,
                                    new_desc,
                                    activate_web
                                )
                                variant_results.append(f"Campos web: {'✅' if success else '❌'}")
                            
                            # 2. Subir imágenes
                            if sync_images and sp.get("images"):
                                for img in sp["images"]:
                                    success, result = upload_bsale_image_to_variant(variant["id"], img["src"])
                                    variant_results.append(f"Imagen: {'✅' if success else '❌'}")
                            
                            results.append({
                                "variant": variant["variant_name"],
                                "sku": variant["sku"],
                                "results": variant_results
                            })
                        
                        # Mostrar resultados
                        st.write("---")
                        st.subheader("📋 Resultados")
                        
                        for r in results:
                            with st.container():
                                st.write(f"**{r['variant']}** (SKU: {r['sku']})")
                                for vr in r["results"]:
                                    st.write(f"  {vr}")
                                st.divider()
                        
                        # Verificar si todo fue exitoso
                        all_success = all(
                            all("✅" in vr for vr in r["results"])
                            for r in results
                        )
                        
                        if all_success:
                            st.success("🎉 Sincronización completada exitosamente")
                        else:
                            st.warning("⚠️ Algunos pasos fallaron, revisá los resultados")
                        
                        # Limpiar selección
                        if st.button("🔄 Limpiar y continuar"):
                            del st.session_state.selected_bsale_product
                            del st.session_state.selected_shopify_product
                            st.rerun()

if __name__ == "__main__":
    main()
