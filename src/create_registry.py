import os
import cv2
import pickle
import numpy as np
from insightface.app import FaceAnalysis

def create_db(registry_path, db_save_path):
    # 1. Настройка путей, чтобы избежать автоматического скачивания
    # Скрипт будет искать модели в C:\Users\dmitr\.insightface\models\buffalo_l
    insightface_folder = os.path.expanduser('~/.insightface')
    
    # Инициализируем FaceAnalysis, указывая путь к локальным моделям
    # Мы не передаем name='buffalo_l' напрямую в конструктор, чтобы не вызвать проверку обновлений на GitHub
    app = FaceAnalysis(root=insightface_folder, providers=['CPUExecutionProvider'])
    
    # Подготавливаем модель buffalo_l
    app.prepare(ctx_id=0, det_size=(640, 640))
    
    database = {}

    print(f"--- Индексация лиц в {registry_path} ---")
    
    if not os.listdir(registry_path):
        print(f"⚠️ Папка {registry_path} пуста! Добавь свои фото.")
        return

    for file in os.listdir(registry_path):
        if file.endswith(('.jpg', '.png', '.jpeg')):
            # Извлекаем имя (например, из 'Dmitry_1.jpg' получим 'Dmitry')
            name = os.path.splitext(file)[0].split('_')[0] 
            img_path = os.path.join(registry_path, file)
            img = cv2.imread(img_path)
            
            if img is None:
                print(f"❌ Не удалось прочитать файл: {file}")
                continue

            # Находим лицо и извлекаем вектор (embedding)
            faces = app.get(img)
            
            if len(faces) > 0:
                # Сортируем лица по размеру и берем самое крупное (основное)
                faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
                embedding = faces[0].normed_embedding
                database[name] = embedding
                print(f"✅ Добавлен в базу: {name} (файл: {file})")
            else:
                print(f"⚠️ Лицо не обнаружено на фото: {file}")

    # 2. Сохраняем готовую базу векторов
    os.makedirs(os.path.dirname(db_save_path), exist_ok=True)
    with open(db_save_path, 'wb') as f:
        pickle.dump(database, f)
    
    print(f"\n🚀 Успех! Файл базы создан: {db_save_path}")
    print(f"Всего в базе студентов: {len(database)}")

if __name__ == "__main__":
    # Твои пути из структуры проекта
    REGISTRY_DIR = r"C:\face_attendance_system\data\registry"
    DB_FILE = r"C:\face_attendance_system\models\students_db.pkl"
    
    create_db(REGISTRY_DIR, DB_FILE)