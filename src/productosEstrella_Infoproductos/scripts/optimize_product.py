import os
import re
import sys
import argparse
from pathlib import Path
from PIL import Image

def minify_css(content):
    # Eliminar comentarios
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Eliminar espacios innecesarios
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([{:;,])\s*', r'\1', content)
    return content.strip()

def minify_js(content):
    # Eliminar comentarios de una línea
    content = re.sub(r'//.*?\n', '\n', content)
    # Eliminar comentarios multilínea
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Eliminar espacios y saltos de línea excesivos
    content = re.sub(r'\n\s*', '\n', content)
    return content.strip()

def process_images(img_dir, max_width=1000, quality=75):
    if not img_dir.exists():
        print(f"⚠️  No se encontró directorio de imágenes en {img_dir}")
        return

    for file in os.listdir(img_dir):
        filepath = img_dir / file
        if file.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                with Image.open(filepath) as img:
                    # Redimensionar si es necesario
                    if img.width > max_width:
                        ratio = max_width / img.width
                        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
                    
                    # Guardar como WebP
                    webp_path = filepath.with_suffix('.webp')
                    img.save(webp_path, format='WEBP', quality=quality, method=6)
                    
                    # Eliminar original
                    os.remove(filepath)
                    print(f"✅ Imagen optimizada y convertida: {file} -> {webp_path.name}")
            except Exception as e:
                print(f"❌ Error con {file}: {e}")

def process_assets(product_dir):
    # Optimizar Imágenes
    process_images(product_dir / "img")

    # Cargar Index para Inlining
    index_path = product_dir / "index.html"
    if not index_path.exists():
        print(f"⚠️  No se encontró index.html en {product_dir}")
        return

    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Minificar e Inlinear CSS
    css_dir = product_dir / "css"
    if css_dir.exists():
        for file in os.listdir(css_dir):
            if file.endswith('.css'):
                path = css_dir / file
                print(f"📦 Minificando e Inlineando CSS: {file}...")
                with open(path, 'r', encoding='utf-8') as f:
                    content = minify_css(f.read())
                
                # Buscar el tag de link o el style previo e inyectar
                link_pattern = rf'<link rel="stylesheet" href="css/{file}">|<style>.*?</style>'
                if re.search(link_pattern, html_content, flags=re.DOTALL):
                    html_content = re.sub(link_pattern, f'<style>{content}</style>', html_content, flags=re.DOTALL, count=1)
                else:
                    # Inyectar antes de </head> como fallback
                    html_content = html_content.replace('</head>', f'<style>{content}</style>\n</head>')

    # Minificar e Inlinear JS
    js_dir = product_dir / "js"
    if js_dir.exists():
        for file in os.listdir(js_dir):
            if file.endswith('.js'):
                path = js_dir / file
                print(f"📦 Minificando e Inlineando JS: {file}...")
                with open(path, 'r', encoding='utf-8') as f:
                    content = minify_js(f.read())
                
                # Buscar el tag de script e inyectar
                script_pattern = rf'<script src="js/{file}"></script>|<script>.*?</script>'
                # Solo reemplazamos si el script actual parece ser el que inyectamos o el link original
                # Nota: Esta lógica es simplificada.
                if f'src="js/{file}"' in html_content:
                    html_content = html_content.replace(f'<script src="js/{file}"></script>', f'<script>{content}</script>')
                
    # Guardar index actualizado
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    parser = argparse.ArgumentParser(description="Optimiza assets de una landing page específica e inyecta CSS/JS inline.")
    parser.add_argument("product", help="Nombre de la carpeta del producto (slug) en /products/")
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent
    product_dir = base_path / "products" / args.product

    if not product_dir.exists():
        print(f"❌ Error: La carpeta '{args.product}' no existe en /products/")
        sys.exit(1)

    print(f"🚀 Iniciando optimización e inlining para: {args.product}...")
    process_assets(product_dir)
    print(f"✨ ¡Hecho! Assets optimizados e inyectados en '{args.product}/index.html'.")

if __name__ == "__main__":
    main()
