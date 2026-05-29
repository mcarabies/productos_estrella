import os
from pathlib import Path
from PIL import Image

def compress_images_in_dir(directory: Path, max_width: int = 1200, quality: int = 85):
    """
    Comprime las imágenes PNG/JPG de un directorio.
    Si son muy grandes, las redimensiona y guarda en formato WEBP o en el mismo formato optimizado.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = Path(root) / file
                try:
                    # Abrir imagen original
                    with Image.open(filepath) as img:
                        original_size = os.path.getsize(filepath)
                        
                        # Si es PNG con transparencia, conservar modo RGBA o convertir
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGBA')
                        else:
                            img = img.convert('RGB')
                        
                        # Redimensionar si es ancho excesivo
                        if img.width > max_width:
                            ratio = max_width / img.width
                            new_size = (max_width, int(img.height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                        
                        # Guardar optimizada sobreescribiendo
                        # Se usa el formato original, pero optimizado
                        save_format = 'PNG' if file.lower().endswith('.png') else 'JPEG'
                        
                        kwargs = {'optimize': True}
                        if save_format == 'JPEG':
                            kwargs['quality'] = quality
                        
                        img.save(filepath, format=save_format, **kwargs)
                        
                        new_size_bytes = os.path.getsize(filepath)
                        saved_kb = (original_size - new_size_bytes) / 1024
                        
                        if saved_kb > 0:
                            print(f"✅ Optimizada: {file} | Ahorrado: {saved_kb:.2f} KB")
                        else:
                            print(f"✓ {file} ya estaba optimizada.")
                except Exception as e:
                    print(f"❌ Error optimizando {file}: {e}")

if __name__ == "__main__":
    current_dir = Path(__file__).parent.parent
    products_dir = current_dir / "products" / "el-arte-del-sueno-profundo"
    
    if products_dir.exists():
        print(f"Iniciando compresión extrema en: {products_dir.name}...")
        compress_images_in_dir(products_dir)
        print("¡Compresión finalizada!")
    else:
        print("La ruta de productos no existe.")
