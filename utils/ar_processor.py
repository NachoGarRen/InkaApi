import cv2
import numpy as np

_rembg_session = None

def generar_stencil_ar(file_bytes: bytes) -> bytes:
    """
    Pipeline de Visión Artificial Avanzado v3.0 (Senior Grade) para extraer tatuajes.
    
    Usa espacio de color LAB para separar piel de tinta matemáticamente.
    La piel humana (cualquier tono) cae en una región específica del plano AB.
    La tinta del tatuaje siempre se sale de esa región.
    
    Pipeline:
      1. Detección rápida de bocetos digitales (bypass)
      2. rembg: eliminar fondo (pared, mesa, etc.)
      3. LAB: separar luminosidad de color
      4. Máscara de piel por rango AB (matemática, no brillo)
      5. Morphología + suavizado para bordes limpios
      6. Refuerzo de contraste solo en áreas de tinta
      7. Fusión final con transparencia profesional
    """
    try:
        print("🪄 AR Pipeline v3.0: Paso 0 - Cargando imagen...")
        nparr_orig = np.frombuffer(file_bytes, np.uint8)
        img_original = cv2.imdecode(nparr_orig, cv2.IMREAD_UNCHANGED)

        if img_original is None:
            raise Exception("No se pudo decodificar la imagen")

        # ========================================================
        # 🚀 BYPASS 1: Imagen ya transparente (boceto digital PNG)
        # ========================================================
        if len(img_original.shape) == 3 and img_original.shape[2] == 4:
            alpha = img_original[:, :, 3]
            if np.any(alpha < 255):
                print("⚡ Bypass: Imagen ya transparente (boceto digital). Retornando tal cual.")
                return file_bytes

        # Convertir a BGR si tiene canal alpha
        if len(img_original.shape) == 3 and img_original.shape[2] == 4:
            img_bgr_orig = cv2.cvtColor(img_original, cv2.COLOR_BGRA2BGR)
        else:
            img_bgr_orig = img_original.copy()

        # ========================================================
        # 🚀 BYPASS 2: Boceto en fondo blanco puro (JPG plano)
        # ========================================================
        gray_orig = cv2.cvtColor(img_bgr_orig, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray_orig)
        mean_val = np.mean(gray_orig)
        
        if std_dev < 15 and mean_val > 245:
            print("⚡ Bypass: Boceto en fondo blanco puro detectado.")
            img_final = cv2.cvtColor(img_bgr_orig, cv2.COLOR_BGR2BGRA)
            # Hacer blanco puro transparente
            lower_white = np.array([240, 240, 240, 0])
            upper_white = np.array([255, 255, 255, 255])
            mask_white = cv2.inRange(img_final, lower_white, upper_white)
            img_final[:, :, 3] = cv2.bitwise_not(mask_white)
            _, buffer = cv2.imencode('.png', img_final)
            return buffer.tobytes()

        # ========================================================
        # ⚔️ PIPELINE PROFESIONAL: Foto real con piel
        # ========================================================
        
        # --- PASO 1: Eliminar fondo con IA (rembg) ---
        print("🪄 AR Pipeline v3.0: Paso 1 - Eliminando fondo con rembg (modelo ligero u2netp)...")
        from rembg import remove
        global _rembg_session
        if _rembg_session is None:
            from rembg import new_session
            print("📦 Inicializando sesión de rembg con modelo ligero u2netp...")
            _rembg_session = new_session("u2netp")
        brazo_recortado_bytes = remove(file_bytes, session=_rembg_session)
        nparr = np.frombuffer(brazo_recortado_bytes, np.uint8)
        img_recortada = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        
        if img_recortada is None or img_recortada.shape[2] < 4:
            raise Exception("rembg no generó imagen con canal alpha")
        
        # Separar canales
        b, g, r, alpha_rembg = cv2.split(img_recortada)
        img_bgr = cv2.merge([b, g, r])

        # --- PASO 2: Convertir a espacio LAB ---
        print("🪄 AR Pipeline v3.0: Paso 2 - Convirtiendo a LAB...")
        img_lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(img_lab)

        # --- PASO 3: Detectar piel en el plano AB ---
        # La piel humana (cualquier tono) se concentra en:
        #   A: 128 ± rango (centro neutro es 128 en LAB de OpenCV, piel tiende a >128 = rojizo)
        #   B: 128 ± rango (piel tiende a >128 = amarillento)
        # La tinta negra/oscura tiene A≈128, B≈128 (neutro) y L muy bajo.
        # Colores de tinta (rojo, azul, verde) se salen del rango de piel.
        print("🪄 AR Pipeline v3.0: Paso 3 - Segmentación piel vs tinta (LAB)...")
        
        # Rango amplio de piel en LAB (OpenCV usa L:0-255, A:0-255, B:0-255 con centro en 128)
        lower_skin_lab = np.array([40, 130, 130], dtype=np.uint8)   # L_min, A_min, B_min
        upper_skin_lab = np.array([255, 175, 200], dtype=np.uint8)  # L_max, A_max, B_max
        
        mask_piel_raw = cv2.inRange(img_lab, lower_skin_lab, upper_skin_lab)
        
        # También considerar como "piel" las zonas muy claras (reflejos, zonas iluminadas)
        # que la máscara LAB podría no capturar
        mask_claro = cv2.inRange(L, 200, 255)
        mask_piel_combinada = cv2.bitwise_or(mask_piel_raw, mask_claro)

        # --- PASO 4: Limpieza morfológica ---
        # Cerrar huecos pequeños dentro de la piel (poros, sombras menores)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask_piel_cerrada = cv2.morphologyEx(mask_piel_combinada, cv2.MORPH_CLOSE, kernel_close)
        
        # Abrir para eliminar ruido pequeño
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_piel_limpia = cv2.morphologyEx(mask_piel_cerrada, cv2.MORPH_OPEN, kernel_open)

        # Suavizar bordes para transición natural
        mask_piel_suave = cv2.GaussianBlur(mask_piel_limpia, (15, 15), 0)

        # Invertir: piel=0 (transparente), tinta=255 (opaca)
        mask_tinta = cv2.bitwise_not(mask_piel_suave)

        # --- PASO 5: Reforzar contraste del tatuaje ---
        print("🪄 AR Pipeline v3.0: Paso 4 - Reforzando contraste de la tinta...")
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization) para mejorar contraste local
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        L_enhanced = clahe.apply(L)
        
        # Reconstruir imagen LAB con luminosidad mejorada
        img_lab_enhanced = cv2.merge([L_enhanced, A, B])
        img_bgr_enhanced = cv2.cvtColor(img_lab_enhanced, cv2.COLOR_LAB2BGR)
        
        # Oscurecer ligeramente las áreas de tinta para que se vean sólidas
        # alpha=1.4 aumenta contraste, beta=-40 oscurece
        img_tinta_reforzada = cv2.convertScaleAbs(img_bgr_enhanced, alpha=1.4, beta=-40)
        
        # Mezclar: donde hay piel usamos la original (se hará transparente),
        # donde hay tinta usamos la versión reforzada
        mask_tinta_norm = mask_tinta.astype(np.float32) / 255.0
        mask_tinta_3ch = np.stack([mask_tinta_norm] * 3, axis=-1)
        
        img_final_bgr = (mask_tinta_3ch * img_tinta_reforzada + 
                         (1.0 - mask_tinta_3ch) * img_bgr).astype(np.uint8)

        # --- PASO 6: Fusionar alpha final ---
        print("🪄 AR Pipeline v3.0: Paso 5 - Fusionando transparencias finales...")
        
        # El alpha final es: (alpha de rembg) AND (máscara de tinta)
        # Esto asegura que solo las áreas de tinta dentro del recorte son visibles
        # Aplicamos un umbral mínimo a la máscara de tinta para hacer cortes más limpios
        _, mask_tinta_binaria = cv2.threshold(mask_tinta, 50, 255, cv2.THRESH_BINARY)
        
        # Combinar con el alpha de rembg
        nuevo_alpha = cv2.bitwise_and(alpha_rembg, mask_tinta_binaria)
        
        # Eliminar píxeles semi-transparentes fantasma: si alpha < 30, forzar a 0
        nuevo_alpha[nuevo_alpha < 30] = 0

        # Reconstruir imagen BGRA final
        img_final = cv2.merge([
            img_final_bgr[:, :, 0],
            img_final_bgr[:, :, 1], 
            img_final_bgr[:, :, 2],
            nuevo_alpha
        ])

        # --- PASO 7: Codificar a PNG ---
        print("🪄 AR Pipeline v3.0: Paso 6 - Codificando PNG final...")
        exito, buffer = cv2.imencode('.png', img_final)
        if not exito:
            raise Exception("No se pudo codificar la imagen a PNG")

        print("✅ AR Pipeline v3.0: Stencil profesional generado con éxito.")
        return buffer.tobytes()

    except Exception as e:
        print(f"⚠️ Error en AR Pipeline v3.0: {e}")
        return None