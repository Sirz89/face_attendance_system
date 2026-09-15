import os
import sys
import cv2
import time
import numpy as np

# ==========================================================
# СЕКЦИЯ СОВМЕСТИМОСТИ (HELL FIX для TensorFlow/Keras)
# ==========================================================
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
# КОНФИГУРАЦИЯ СИСТЕМЫ
# ==========================================================
DATABASE_DIR = r"C:\face_attendance_system\data\db" 
# Папка, куда будут сохраняться результаты
OUTPUT_DIR = r"C:\face_attendance_system\data\results"

MODEL_FOR_RECOGNITION = "ArcFace"
DETECTOR_BACKEND = "mtcnn"
THRESHOLD = 0.65

def process_group_photo(test_img_path):
    print(f"\n🔍 Анализ группового фото: {os.path.basename(test_img_path)}")
    
    # 0. Создаем папку для результатов, если ее нет
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 Создана папка для результатов: {OUTPUT_DIR}")

    # 1. Загрузка изображения
    original_img = cv2.imread(test_img_path)
    if original_img is None:
        print(f"❌ Не удалось открыть файл: {test_img_path}")
        return

    img_v = original_img.copy()
    h_orig, w_orig, _ = img_v.shape
    start_time_all = time.time()

    # 2. Очистка кэша базы данных
    pkl_path = os.path.join(DATABASE_DIR, f"representations_{MODEL_FOR_RECOGNITION.lower()}.pkl")
    if os.path.exists(pkl_path):
        os.remove(pkl_path)

    try:
        # ЭТАП 1: ДЕТЕКЦИЯ ЛИЦ
        face_objs = DeepFace.represent(
            img_path=test_img_path,
            model_name=MODEL_FOR_RECOGNITION,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=False
        )

        if not face_objs:
            print("Лица не найдены.")
            return

        # ЭТАП 2: ПОДГОТОВКА СЕГМЕНТОВ
        face_crops = {}
        for i, face_obj in enumerate(face_objs):
            area = face_obj.get("facial_area") or face_obj.get("box")
            if not area: continue
            
            x, y, w, h = area["x"], area["y"], area["w"], area["h"]
            padding = 10
            x1, y1 = max(0, x - padding), max(0, y - padding)
            x2, y2 = min(w_orig, x + w + padding), min(h_orig, y + h + padding)
            
            face_img = original_img[y1:y2, x1:x2]
            if face_img.size > 0:
                face_crops[i] = (x, y, w, h, face_img)

        # ЭТАП 3: ГЕНЕРАЦИЯ ГИПОТЕЗ
        all_hypotheses = []
        for face_idx, data in face_crops.items():
            _, _, _, _, face_img = data
            try:
                results = DeepFace.find(
                    img_path=face_img, 
                    db_path=DATABASE_DIR, 
                    model_name=MODEL_FOR_RECOGNITION, 
                    detector_backend='skip', 
                    enforce_detection=False, 
                    silent=True
                )
                
                if len(results) > 0 and not results[0].empty:
                    df = results[0]
                    for _, row in df.iterrows():
                        dist_col = 'distance' if 'distance' in df.columns else [c for c in df.columns if 'cosine' in c.lower() or 'distance' in c.lower()][0]
                        distance = row[dist_col]
                        
                        if distance <= THRESHOLD:
                            person_name = os.path.basename(os.path.dirname(row['identity']))
                            all_hypotheses.append((distance, face_idx, person_name))
            except: continue

        # ЭТАП 4: ЖАДНЫЙ АЛГОРИТМ
        all_hypotheses.sort(key=lambda item: item[0]) 
        assigned_faces, assigned_names, final_results = set(), set(), {}

        for distance, face_idx, person_name in all_hypotheses:
            if face_idx not in assigned_faces and person_name not in assigned_names:
                final_results[face_idx] = (person_name, distance)
                assigned_faces.add(face_idx)
                assigned_names.add(person_name)

        # ЭТАП 5: ОТРИСОВКА
        for face_idx, data in face_crops.items():
            x, y, w, h, _ = data
            if face_idx in final_results:
                name, distance = final_results[face_idx]
                color, text_str = (0, 255, 0), f"{name} ({round(distance, 2)})"
            else:
                color, text_str = (0, 0, 255), "Unknown"

            cv2.rectangle(img_v, (x, y), (x + w, y + h), color, 2)
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size, _ = cv2.getTextSize(text_str, font, 0.6, 2)
            cv2.rectangle(img_v, (x, y - text_size[1] - 5), (x + text_size[0], y), color, -1)
            cv2.putText(img_v, text_str, (x, y - 5), font, 0.6, (255, 255, 255), 2)

        # ЭТАП 6: СОХРАНЕНИЕ В ОТДЕЛЬНУЮ ПАПКУ
        duration = round(time.time() - start_time_all, 2)
        
        # Получаем только имя файла из полного пути
        file_name = os.path.basename(test_img_path)
        # Формируем путь сохранения: папка_результатов / имя_файла_recognized.jpg
        output_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(file_name)[0]}_recognized.jpg")
        
        cv2.imwrite(output_path, img_v)
        print(f"✅ Анализ завершен за {duration} сек.")
        print(f"💾 Результат сохранен в: {output_path}")

        try:
            cv2.imshow("Result", img_v)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except: pass

    except Exception as e:
        print(f"❌ Ошибка: {e}")

# ==========================================================
# ТОЧКА ВХОДА
# ==========================================================
if __name__ == "__main__":
    # Укажи путь к фото для теста
    TEST_PHOTO_PATH = r"C:\face_attendance_system\data\db\Test_sovmestnux_photo\Photo_Grupui.jpg"
    process_group_photo(TEST_PHOTO_PATH)