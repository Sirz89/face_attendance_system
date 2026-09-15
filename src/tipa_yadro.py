import os
import sys
import cv2
import numpy as np
import pandas as pd
from datetime import datetime

# ==========================================
# 1. СЕКЦИЯ СОВМЕСТИМОСТИ (HELL FIX)
# ==========================================
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1' # Работаем на CPU для стабильности
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
    print("✅ Система инициализирована. Модели готовы.")
except ImportError:
    print("❌ Критическая ошибка: проверь установку tf-keras и deepface")
    sys.exit()

# ==========================================
# 2. НАСТРОЙКИ ПРОЕКТА
# ==========================================
DB_PATH = r"C:\face_attendance_system\data\db"
LOG_FILE = "attendance_log.csv"

# Выбери модель: "VGG-Face", "Facenet512", "ArcFace"
SELECTED_MODEL = "VGG-Face" 

# ==========================================
# 3. ФУНКЦИЯ ЛОГИРОВАНИЯ
# ==========================================
def log_attendance(name):
    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if not os.path.isfile(LOG_FILE):
        df = pd.DataFrame(columns=["Name", "Time"])
    else:
        df = pd.read_csv(LOG_FILE)

    # Проверка на дубликаты (не записываем чаще раза в 1 минуту)
    last_person_records = df[df['Name'] == name].tail(1)
    if not last_person_records.empty:
        last_time = datetime.strptime(last_person_records['Time'].iloc[0], "%Y-%m-%d %H:%M:%S")
        if (now - last_time).total_seconds() < 60:
            return

    new_row = {"Name": name, "Time": dt_string}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)
    print(f"📝 [ЖУРНАЛ] Зафиксирован: {name} ({dt_string})")

# ==========================================
# 4. ОСНОВНОЙ ЦИКЛ
# ==========================================
def run_attendance_system():
    cap = cv2.VideoCapture(0)
    print(f"🚀 Запуск камеры. Модель: {SELECTED_MODEL}")
    print("Нажми 'Q' для выхода.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        try:
            # Поиск лица в базе
            results = DeepFace.find(
                img_path=frame,
                db_path=DB_PATH,
                model_name=SELECTED_MODEL,
                distance_metric="cosine",
                enforce_detection=False,
                detector_backend='opencv', # Самый быстрый вариант
                silent=True
            )

            if len(results) > 0 and not results[0].empty:
                # Извлекаем путь к самому похожему фото
                match_path = results[0]['identity'][0]
                
                # Получаем имя человека (название папки)
                person_name = os.path.basename(os.path.dirname(match_path))
                
                # Записываем в журнал
                log_attendance(person_name)

                # Визуализация
                cv2.rectangle(frame, (10, 10), (300, 60), (0, 0, 0), -1) # Фон для текста
                cv2.putText(frame, f"ID: {person_name}", (20, 45), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Unknown User", (20, 45), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        except Exception as e:
            # Выводим статус загрузки, если модель еще инициализируется
            cv2.putText(frame, "System Initializing...", (20, 45), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Attendance System - Diploma Project", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_attendance_system()