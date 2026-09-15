import os
import sys
import cv2
import time
import tkinter as tk
from tkinter import filedialog
from deepface import DeepFace

# --- Секция совместимости (та же, что и раньше) ---
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_USE_LEGACY_KERAS'] = '1'

import tensorflow as tf
import tf_keras as keras
sys.modules['keras'] = keras
sys.modules['tensorflow.keras'] = keras

# --- Настройки ---
DB_PATH = r"C:\face_attendance_system\data\db"
MODELS = ["VGG-Face", "Facenet512", "ArcFace"]

def select_file():
    root = tk.Tk()
    root.withdraw() # Скрываем основное окно tkinter
    file_path = filedialog.askopenfilename(title="Выберите фото для анализа",
                                          filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    return file_path

def battle_of_models(image_path):
    print(f"\n🔍 Анализ файла: {os.path.basename(image_path)}")
    print("-" * 65)
    print(f"{'Модель':<15} | {'Результат':<15} | {'Дистанция':<10} | {'Время (сек)':<10}")
    print("-" * 65)

    for model_name in MODELS:
        start_time = time.time()
        try:
            # Использование enforce_detection=False позволяет коду работать, 
            # даже если лицо не найдено явно
            results = DeepFace.find(img_path=image_path,
                                    db_path=DB_PATH,
                                    model_name=model_name,
                                    distance_metric="cosine",
                                    enforce_detection=False, # <--- ВАЖНО: не выдавать ошибку
                                    detector_backend='opencv', # Можно заменить на 'retinaface' для супер-точности
                                    silent=True)
            
            end_time = time.time()
            duration = round(end_time - start_time, 2)

# results - это список таблиц для каждого найденного лица
            if len(results) > 0:
                found_anyone = False
                
                # Пробегаемся циклом по всем найденным лицам на фото
                for face_idx, df in enumerate(results):
                    if not df.empty:
                        found_anyone = True
                        
                        # Извлекаем данные для конкретного лица
                        match_path = df['identity'].iloc[0]
                        person_name = os.path.basename(os.path.dirname(match_path))
                        
                        # Умный поиск колонки с дистанцией
                        if 'distance' in df.columns:
                            distance = round(df['distance'].iloc[0], 4)
                        else:
                            dist_col = [c for c in df.columns if 'cosine' in c.lower() or 'distance' in c.lower()][0]
                            distance = round(df[dist_col].iloc[0], 4)
                        
                        # Выводим результат с указанием номера лица (Лицо 1, Лицо 2 и т.д.)
                        print(f"{model_name:<15} | Лицо {face_idx+1}: {person_name:<12} | {distance:<10} | {duration:<10}")
                
                # Если списки вернулись, но все они пустые (лица найдены, но их нет в базе)
                if not found_anyone:
                    print(f"{model_name:<15} | Неизвестные (лиц: {len(results)}) | {'-':<10} | {duration:<10}")
                    
            else:
                print(f"{model_name:<15} | Лица не обнаружены | {'-':<10} | {duration:<10}")

        except Exception as e:
            # Чтобы больше не гадать, будем выводить полную ошибку
            print(f"{model_name:<15} | Ошибка: {e}")

if __name__ == "__main__":
    img_to_test = select_file()
    if img_to_test:
        battle_of_models(img_to_test)
    else:
        print("Файл не выбран.")