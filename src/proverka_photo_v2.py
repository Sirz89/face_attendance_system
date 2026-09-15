import os
import sys
import cv2
import time
import numpy as np

# --- СЕКЦИЯ СОВМЕСТИМОСТИ (HELL FIX) ---
# Оставляем, чтобы TensorFLow не ругался на CPU и Keras
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_USE_LEGACY_KERAS'] = '1'

try:
    import tensorflow as tf
    import tf_keras as keras
    sys.modules['keras'] = keras
    sys.modules['tensorflow.keras'] = keras
    sys.modules['tensorflow.keras.models'] = keras.models
    sys.modules['tensorflow.keras.layers'] = keras.layers
    sys.modules['tensorflow.keras.preprocessing'] = keras.preprocessing
    from deepface import DeepFace
    print("✅ Нейросети инициализированы.")
except ImportError:
    print("❌ Критическая ошибка импорта.")
    sys.exit()

# ==========================================================
# КОНФИГУРАЦИЯ
# ==========================================================
# 1. Твои эталонные фото людей
DATABASE_DIR = r"C:\face_attendance_system\data\db" 

# 2. Модели и детекторы для ГРУППОВЫХ фото
MODEL_FOR_RECOGNITION = "ArcFace"  # Самая точная на твоих скринах
DETECTOR_BACKEND = "mtcnn"       # Лучше ищет толпу, чем opencv

# 3. Насколько модель должна быть уверена (для ArcFace косинус <= 0.68 по умолчанию)
# Мы поставим чуть строже для диплома. Если дистанция больше - человек неизвестен.
THRESHOLD = 0.65 

def process_group_photo(test_img_path):
    print(f"\n🔍 Начинаю анализ группового фото: {os.path.basename(test_img_path)}")
    
    # Загружаем исходную картинку OpenCV
    original_img = cv2.imread(test_img_path)
    if original_img is None:
        print("❌ Не удалось открыть файл изображения.")
        return

    img_v = original_img.copy() # Копия для рисования
    h_orig, w_orig, _ = img_v.shape
    start_time_all = time.time()

    # ДЛЯ ДИПЛОМА: Удаляем старый .pkl, чтобы база пересчиталась точно
    pkl_path = os.path.join(DATABASE_DIR, f"representations_{MODEL_FOR_RECOGNITION.lower()}.pkl")
    if os.path.exists(pkl_path):
        os.remove(pkl_path)
        print("🧹 Старый индекс базы удален для чистоты теста.")

    try:
        # ЭТАП 1: Получаем координаты ВСЕХ лиц на фото
        # Мы используем represent, потому что он возвращает box (координаты) для всех лиц
        face_objs = DeepFace.represent(
            img_path=test_img_path,
            model_name=MODEL_FOR_RECOGNITION,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=False # Не падаем, если лиц нет
        )

        print(f"👥 Найдено лиц на фото: {len(face_objs)}")

        # ЭТАП 2: Проходим по каждому найденному лицу
        for i, face_obj in enumerate(face_objs):
            # Проверяем, какой ключ использует твоя версия библиотеки (facial_area или box)
            area = face_obj.get("facial_area") or face_obj.get("box")
            
            if not area:
                print(f"⚠️ Не удалось получить координаты для лица {i+1}")
                continue

            x, y, w, h = area["x"], area["y"], area["w"], area["h"]     
            
            # Немного расширим рамку для красоты
            padding = 10
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(w_orig, x + w + padding)
            y2 = min(h_orig, y + h + padding)
            
            # Вырезаем лицо (cropp) из ОРИГИНАЛЬНОГО изображения
            # ВНИМАНИЕ: OpenCV режет как [y:y2, x:x2]
            face_crop = original_img[y1:y2, x1:x2]
            
            if face_crop.size == 0: continue

            # ЭТАП 3: Сравниваем этот вырезанный кусок с базой
            name = "Unknown"
            distance = 1.0
            color = (0, 0, 255) # Красный для неизвестных (BGR формат)
            
            # ВАЖНО: используем detector_backend='skip', т.к. мы уже вырезали лицо
            try:
                results = DeepFace.find(
                    img_path=face_crop,
                    db_path=DATABASE_DIR,
                    model_name=MODEL_FOR_RECOGNITION,
                    detector_backend='skip', # Ускоряет процесс
                    enforce_detection=False,
                    silent=True
                )
                
                # Если нашли в базе
                if len(results) > 0 and not results[0].empty:
                    df = results[0]
                    distance = df['distance'].iloc[0] # Используем "умный" поиск имени колонки, если это старая версия
                    
                    # Проверяем наш порог (Threshold)
                    if distance <= THRESHOLD:
                        # Извлекаем имя папки
                        match_path = df['identity'].iloc[0]
                        name = os.path.basename(os.path.dirname(match_path))
                        color = (0, 255, 0) # Зеленый для известных
                    else:
                        name = "Unknown (low conf.)"

            except Exception as find_error:
                name = "Unknown (Error)"
                print(f"⚠️ Ошибка сравнения лица {i+1}: {find_error}")

            # ЭТАП 4: Рисуем рамку и текст на копии изображения
            # Рисуем квадрат
            cv2.rectangle(img_v, (x, y), (x + w, y + h), color, 2)
            
            # Создаем фон для текста (черная плашка)
            text_str = f"{name} (dist:{round(distance, 2)})"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            text_size, _ = cv2.getTextSize(text_str, font, font_scale, thickness)
            
            cv2.rectangle(img_v, (x, y - text_size[1] - 5), (x + text_size[0], y), color, -1)
            # Пишем имя белым цветом
            cv2.putText(img_v, text_str, (x, y - 5), font, font_scale, (255, 255, 255), thickness)

        duration = round(time.time() - start_time_all, 2)
        print(f"✅ Анализ завершен за {duration} сек.")

        # ЭТАП 5: Сохраняем и показываем результат
        # Генерируем имя файла: исходное_processed.jpg
        base_name = os.path.splitext(test_img_path)[0]
        output_path = f"{base_name}_processed.jpg"
        cv2.imwrite(output_path, img_v)
        print(f"💾 Результат сохранен в: {output_path}")

        # Пытаемся показать окно (может не работать на некоторых системах, если нет GUI)
        try:
            cv2.imshow("Attendance Visualization", img_v)
            print("📺 Окно с результатом открыто. Нажми любую клавишу в окне, чтобы закрыть.")
            cv2.waitKey(0) # Ждем нажатия клавиши
            cv2.destroyAllWindows()
        except:
            print("⚠️ Не удалось открыть окно просмотра (возможно, нет GUI). Проверь файл на диске.")

    except Exception as e:
        print(f"❌ Критическая ошибка при анализе фото: {e}")

# ==========================================================
# БЛОК ЗАПУСКА (Для контролируемого теста)
# ==========================================
if __name__ == "__main__":
    # Укажи тут путь к ОДНОМУ из своих групповых фото
    # (например, photo_2_2026-05-14_14-12-42.jpg)
    TEST_PHOTO_PATH = r"C:\face_attendance_system\data\db\Test_sovmestnux_photo\photo_5_2026-05-14_14-12-42.jpg" 
    
    process_group_photo(TEST_PHOTO_PATH)