# api/routers/tattoo_ar.py
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import Response
import io
from PIL import Image

router = APIRouter(prefix="/tattoo", tags=["Tattoo AR"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "tattoo_ar"}


def apply_smart_transparency(img_data: bytes) -> bytes:
    """
    Convierte los píxeles claros/blancos en transparentes de forma progresiva.
    Preserva los colores del tatuaje y suaviza los bordes para eliminar halos.
    """
    img = Image.open(io.BytesIO(img_data)).convert("RGBA")
    datas = img.getdata()
    new_data = []
    
    for item in datas:
        r, g, b, a = item[0], item[1], item[2], item[3]
        if a < 10:
            new_data.append(item)
            continue
            
        # La blancura es el valor mínimo de los canales (para no afectar a colores saturados)
        whiteness = min(r, g, b)
        
        if whiteness > 175:
            # Desvanecimiento progresivo: de 175 (opaco) a 240 (totalmente transparente)
            alpha_factor = (240 - whiteness) / 65.0
            new_alpha = int(min(max(a * alpha_factor, 0.0), 255.0))
            new_data.append((r, g, b, new_alpha))
        else:
            new_data.append(item)
            
    img.putdata(new_data)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


@router.post("/remove_bg")
async def remove_bg(file: UploadFile = File(...)):
    """
    Recibe imagen PNG o JPG, devuelve PNG con fondo transparente limpio.
    """
    content_type = file.content_type
    
    # Soporte robusto para octet-stream enviado desde Flutter/mobile
    if content_type == "application/octet-stream" or not content_type:
        filename = file.filename.lower() if file.filename else ""
        if filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif filename.endswith(".webp"):
            content_type = "image/webp"
        else:
            content_type = "image/jpeg"  # Fallback predeterminado tolerante

    if content_type not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {file.content_type}. Usa PNG o JPG."
        )
    try:
        data = await file.read()
        if len(data) == 0:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        
        try:
            # 1. Intentar rembg (remoción avanzada por IA)
            from rembg import remove
            raw_result = remove(data)
            # 2. Aplicar transparencia inteligente para limpiar halos blancos y bordes
            result = apply_smart_transparency(raw_result)
        except Exception as rembg_err:
            # 3. Fallback: Procesado inteligente directo sobre la imagen original
            print(f"[WARNING] rembg falló: {rembg_err}. Usando procesador inteligente directo.")
            result = apply_smart_transparency(data)
            
        return Response(content=result, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar imagen: {str(e)}")