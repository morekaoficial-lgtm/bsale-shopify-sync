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

# Secrets
BSALE_ACCESS_TOKEN = st.secrets.get("bsale", {}).get("access_token", "")
BSALE_DOCUMENT_TYPE_ID = st.secrets.get("bsale", {}).get("document_type_id", "")
SHOPIFY_ACCESS_TOKEN = st.secrets.get("shopify", {}).get("MOREKA_ACCESS_TOKEN", "")
SHOPIFY_SHOP_NAME = st.secrets.get("shopify", {}).get("shop_name", "morekashop1")

# URLs
BSALE_API_URL = "https://api.bsale.io/v1"
SHOPIFY_API_URL = f"https://{SHOPIFY_SHOP_NAME}.myshopify.com/admin/api/2024-01"

# Headers
bsale_headers = {
    "access_token": BSALE_ACCESS_TOKEN,
    "Content-Type": "application/json"
}

shopify_headers = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# ==================== FUNCIONES Bsale ====================

def get_bsale_products(limit=100, offset=0):
    """Obtener productos de Bsale"""
    url = f"{BSALE_API_URL}/products.json?limit={limit}&offset={offset}"
    response = requests.get(url, headers=bsale_headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def get_bsale_variants(product_id):
    """Obtener variantes de un producto Bsale"""
    url = f"{BSALE_API_URL}/products/{product_id}/variants.json"
    response = requests.get(url, headers=bsale_headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def get_bsale_variant_detail(variant_id):
    """Obtener detalle de una variante Bsale"""
    url = f"{BSALE_API_URL}/variants/{variant_id}.json"
    response = requests.get(url, headers=bsale_headers)
    if response.status_code == 200:
        return response.json()
    return {}

def update_bsale_web_fields(variant_id, web_name, web_description, web_active=True):
    """Actualizar campos web de una variante Bsale"""
    url = f"{BSALE_API_URL}/variants/{variant_id}.json"
    data = {
        "webName": web_name,
        "webDescription": web_description,
        "webActive": web_active
    }
    response = requests.put(url, headers=bsale_headers, json=data)
    return response.status_code == 200, response.json() if response.status_code == 200 else response.text

def upload_bsale_image(variant_id, image_url):
    """Subir imagen a Bsale desde URL"""
    # Primero descargar imagen
    img_response = requests.get(image_url)
    if img_response.status_code != 200:
        return False, "No se pudo descargar la imagen"
    
    # Convertir a base64
    img_base64 = base64.b64encode(img_response.content).decode('utf-8')
    
    # Subir a Bsale
    url = f"{BSALE_API_URL}/variants/{variant_id}/images.json"
    data = {
        "filename": f"image_{variant_id}.jpg",
        "base64": img_base64
    }
    response = requests.post(url, headers=bsale_headers, json=data)
    return response.status_code == 201, response.json() if response.status_code == 201 else response.text

# ==================== FUNCIONES Shopify ====================

def search_shopify_products(query, limit=50):
    """Buscar productos en Shopify"""
    url = f"{SHOPIFY_API_URL}/products.json?title={query}&limit={limit}"
    response = requests.get(url, headers=shopify_headers)
    if response.status_code == 200:
        return response.json().get("products", [])
    return []

def get_shopify_product(product_id):
    """Obtener producto específico de Shopify"""
    url = f"{SHOPIFY_API_URL}/products/{product_id}.json"
    response = requests.get(url, headers=shopify_headers)
    if response.status_code == 200:
        return response.json().get("product", {})
    return {}

# ==================== UI ====================

def main():
    st.title("🔄 Bsale ↔ Shopify Sync")
    st.markdown("Sincroniza descripciones, títulos e imágenes de Shopify a Bsale")
    
    # Sidebar - Configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Bsale
        st.subheader("Bsale (Nebro)")
        bsale_token = st.text_input("Access Token", value=BSALE_ACCESS_TOKEN, type="password")
        bsale_doc_type = st.text_input("Document Type ID", value=BSALE_DOCUMENT_TYPE_ID)
        
        # Shopify
        st.subheader("Shopify (morekashop1)")
        shopify_token = st.text_input("Access Token", value=SHOPIFY_ACCESS_TOKEN, type="password")
        shopify_shop = st.text_input("Shop Name", value=SHOPIFY_SHOP_NAME)
        
        # Actualizar credenciales en session state
        if st.button("💾 Guardar Configuración"):
            st.session_state.bsale_token = bsale_token
            st.session_state.bsale_doc_type = bsale_doc_type
            st.session_state.shopify_token = shopify_token
            st.session_state.shopify_shop = shopify_shop
            st.success("✅ Configuración guardada")
    
    # Usar credenciales de session state o defaults
    bsale_token = st.session_state.get("bsale_token", BSALE_ACCESS_TOKEN)
    shopify_token = st.session_state.get("shopify_token", SHOPIFY_ACCESS_TOKEN)
    
    # Verificar credenciales
    if not bsale_token or not shopify_token:
        st.warning("⚠️ Configura los tokens en el sidebar primero")
        return
    
    # Actualizar headers
    bsale_headers["access_token"] = bsale_token
    shopify_headers["X-Shopify-Access-Token"] = shopify_token
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📦 Productos Bsale", "🔍 Buscar en Shopify", "🔄 Sincronización"])
    
    # ==================== TAB 1: Productos Bsale ====================
    with tab1:
        st.header("Productos Bsale - Estado Web")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_bsale = st.text_input("🔍 Buscar producto Bsale (nombre o SKU)", "")
        with col2:
            filter_status = st.selectbox(
                "Filtrar por estado",
                ["Todos", "Sin descripción web", "Con descripción web", "Web activo", "Web inactivo"]
            )
        
        if st.button("📥 Cargar Productos Bsale"):
            with st.spinner("Cargando productos..."):
                products = get_bsale_products(limit=100)
                
                # Enriquecer con variantes y campos web
                enriched_products = []
                for product in products:
                    variants = get_bsale_variants(product["id"])
                    for variant in variants:
                        detail = get_bsale_variant_detail(variant["id"])
                        
                        # Determinar estado web
                        has_web_desc = bool(detail.get("webDescription", "").strip())
                        web_active = detail.get("webActive", False)
                        has_web_image = bool(detail.get("webImage", ""))
                        
                        enriched_products.append({
                            "id": variant["id"],
                            "product_id": product["id"],
                            "sku": variant.get("code", "N/A"),
                            "name": product.get("name", "Sin nombre"),
                            "variant_name": variant.get("description", "Sin descripción"),
                            "has_web_description": has_web_desc,
                            "web_description": detail.get("webDescription", ""),
                            "web_name": detail.get("webName", ""),
                            "web_active": web_active,
                            "has_web_image": has_web_image,
                            "web_image_url": detail.get("webImage", ""),
                            "web_price": detail.get("webPrice", 0)
                        })
                
                st.session_state.bsale_products = enriched_products
                st.success(f"✅ {len(enriched_products)} variantes cargadas")
        
        # Mostrar productos
        if "bsale_products" in st.session_state:
            products = st.session_state.bsale_products
            
            # Aplicar filtros
            filtered = products
            if search_bsale:
                filtered = [p for p in filtered if search_bsale.lower() in p["name"].lower() or search_bsale.lower() in p["sku"].lower()]
            
            if filter_status == "Sin descripción web":
                filtered = [p for p in filtered if not p["has_web_description"]]
            elif filter_status == "Con descripción web":
                filtered = [p for p in filtered if p["has_web_description"]]
            elif filter_status == "Web activo":
                filtered = [p for p in filtered if p["web_active"]]
            elif filter_status == "Web inactivo":
                filtered = [p for p in filtered if not p["web_active"]]
            
            st.write(f"Mostrando {len(filtered)} de {len(products)} variantes")
            
            # Tabla de productos
            for product in filtered:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{product['name']}**")
                        st.write(f"SKU: {product['sku']}")
                        st.write(f"Variante: {product['variant_name']}")
                    
                    with col2:
                        if product["has_web_description"]:
                            st.success("✅ Descripción web")
                            st.write(f"Nombre web: {product['web_name'][:30]}...")
                        else:
                            st.error("❌ Sin descripción web")
                    
                    with col3:
                        if product["web_active"]:
                            st.success("🟢 Activo web")
                        else:
                            st.warning("🔴 Inactivo web")
                    
                    with col4:
                        if product["has_web_image"]:
                            st.success("🖼️ Imagen")
                            st.write(f"[Ver imagen]({product['web_image_url']})")
                        else:
                            st.error("❌ Sin imagen")
                    
                    with col5:
                        if not product["has_web_description"]:
                            if st.button("🔍 Buscar en Shopify", key=f"search_{product['id']}"):
                                st.session_state.selected_bsale_product = product
                                st.session_state.shopify_search_query = product["name"]
                                st.rerun()
                        else:
                            st.write(f"Precio web: ${product['web_price']}")
                    
                    st.divider()
    
    # ==================== TAB 2: Buscar en Shopify ====================
    with tab2:
        st.header("🔍 Buscar Productos en Shopify")
        
        search_query = st.text_input(
            "Buscar producto en Shopify",
            value=st.session_state.get("shopify_search_query", ""),
            key="shopify_search"
        )
        
        if st.button("🔍 Buscar") and search_query:
            with st.spinner("Buscando en Shopify..."):
                shopify_products = search_shopify_products(search_query)
                st.session_state.shopify_results = shopify_products
                st.success(f"✅ {len(shopify_products)} productos encontrados")
        
        if "shopify_results" in st.session_state:
            shopify_products = st.session_state.shopify_results
            
            for product in shopify_products:
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        # Imagen principal
                        if product.get("images"):
                            st.image(product["images"][0]["src"], width=150)
                        else:
                            st.write("Sin imagen")
                    
                    with col2:
                        st.write(f"**{product['title']}**")
                        st.write(f"ID: {product['id']}")
                        st.write(f"Handle: {product['handle']}")
                        
                        # Descripción (body_html)
                        if product.get("body_html"):
                            with st.expander("Ver descripción"):
                                st.write(product["body_html"], unsafe_allow_html=True)
                        
                        # Tags
                        if product.get("tags"):
                            st.write(f"Tags: {', '.join(product['tags'][:5])}")
                    
                    with col3:
                        st.write(f"Precio: ${product.get('variants', [{}])[0].get('price', 'N/A')}")
                        st.write(f"Stock: {product.get('variants', [{}])[0].get('inventory_quantity', 'N/A')}")
                        
                        if st.button("➡️ Seleccionar para sync", key=f"select_{product['id']}"):
                            st.session_state.selected_shopify_product = product
                            st.success("✅ Producto seleccionado")
                    
                    st.divider()
    
    # ==================== TAB 3: Sincronización ====================
    with tab3:
        st.header("🔄 Sincronizar Bsale ← Shopify")
        
        # Mostrar productos seleccionados
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 Producto Bsale (Destino)")
            if "selected_bsale_product" in st.session_state:
                bp = st.session_state.selected_bsale_product
                st.write(f"**{bp['name']}**")
                st.write(f"SKU: {bp['sku']}")
                st.write(f"ID Variante: {bp['id']}")
                
                st.write("---")
                st.write("**Estado actual:**")
                st.write(f"- Descripción web: {'✅' if bp['has_web_description'] else '❌'}")
                st.write(f"- Web activo: {'✅' if bp['web_active'] else '❌'}")
                st.write(f"- Imagen: {'✅' if bp['has_web_image'] else '❌'}")
            else:
                st.info("Selecciona un producto Bsale desde la pestaña 'Productos Bsale'")
        
        with col2:
            st.subheader("🛒 Producto Shopify (Origen)")
            if "selected_shopify_product" in st.session_state:
                sp = st.session_state.selected_shopify_product
                st.write(f"**{sp['title']}**")
                st.write(f"ID: {sp['id']}")
                
                if sp.get("images"):
                    st.image(sp["images"][0]["src"], width=200)
                
                st.write("---")
                st.write("**Datos disponibles:**")
                st.write(f"- Título: ✅")
                st.write(f"- Descripción: {'✅' if sp.get('body_html') else '❌'}")
                st.write(f"- Imágenes: {'✅' if sp.get('images') else '❌'}")
            else:
                st.info("Selecciona un producto Shopify desde la pestaña 'Buscar en Shopify'")
        
        # Configuración de sync
        if "selected_bsale_product" in st.session_state and "selected_shopify_product" in st.session_state:
            st.write("---")
            st.subheader("⚙️ Opciones de Sincronización")
            
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
                bp = st.session_state.selected_bsale_product
                sp = st.session_state.selected_shopify_product
                
                st.write("**Datos actuales Bsale → Datos nuevos Shopify**")
                
                if sync_title:
                    st.write(f"Nombre web: `{bp['web_name']}` → `{sp['title']}`")
                
                if sync_description:
                    current_desc = bp['web_description'][:100] + "..." if len(bp['web_description']) > 100 else bp['web_description']
                    new_desc = sp.get('body_html', '')[:100] + "..." if len(sp.get('body_html', '')) > 100 else sp.get('body_html', '')
                    st.write(f"Descripción: `{current_desc}` → `{new_desc}`")
                
                if sync_images:
                    st.write(f"Imágenes: {'Sí' if bp['has_web_image'] else 'No'} → {'Sí' if sp.get('images') else 'No'}")
                
                st.write(f"Web activo: {'Sí' if bp['web_active'] else 'No'} → {'Sí' if activate_web else 'No'}")
            
            # Ejecutar sync
            if st.button("🚀 Ejecutar Sincronización", type="primary"):
                with st.spinner("Sincronizando..."):
                    bp = st.session_state.selected_bsale_product
                    sp = st.session_state.selected_shopify_product
                    
                    results = []
                    
                    # 1. Actualizar campos web
                    if sync_title or sync_description:
                        success, result = update_bsale_web_fields(
                            bp["id"],
                            sp["title"] if sync_title else bp["web_name"],
                            sp.get("body_html", "") if sync_description else bp["web_description"],
                            activate_web
                        )
                        results.append(f"Campos web: {'✅' if success else '❌'} {result}")
                    
                    # 2. Subir imágenes
                    if sync_images and sp.get("images"):
                        for img in sp["images"]:
                            success, result = upload_bsale_image(bp["id"], img["src"])
                            results.append(f"Imagen {img['id']}: {'✅' if success else '❌'} {result}")
                    
                    # Mostrar resultados
                    st.write("---")
                    st.subheader("📋 Resultados")
                    for result in results:
                        st.write(result)
                    
                    if all("✅" in r for r in results):
                        st.success("🎉 Sincronización completada exitosamente")
                        # Limpiar selección
                        del st.session_state.selected_bsale_product
                        del st.session_state.selected_shopify_product
                    else:
                        st.warning("⚠️ Algunos pasos fallaron, revisa los resultados")

if __name__ == "__main__":
    main()
