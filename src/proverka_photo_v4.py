import os
import sys
import cv2
import time
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

# ==========================================================
# СЕКЦИЯ СОВМЕСТИМОСТИ
# ==========================================================
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_USE_LEGACY_KERAS'] = '1'

try:
    from deepface import DeepFace
    print("✅ Нейросети готовы к работе.")
except ImportError:
    print("❌ Ошибка импорта DeepFace.")
    sys.exit()

# ==========================================================
# КОНФИГУРАЦИЯ
# ==========================================================
DATABASE_DIR = r"C:\face_attendance_system\data\db" 
OUTPUT_DIR = r"C:\face_attendance_system\data\results"

MODEL_FOR_RECOGNITION = "ArcFace"
DETECTOR_BACKEND = "retinaface" 
# ПОРОГ: Увеличил до 0.75 для более гибкого распознавания
THRESHOLD = 0.75

# ==========================================================
# ФУНКЦИОНАЛ ПРИЛОЖЕНИЯ
# ==========================================================

def save_attendance_report(present_list, source_image):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_name = f"attendance_{timestamp}.txt"
    report_path = os.path.join(OUTPUT_DIR, report_name)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"ОТЧЕТ О ПОСЕЩАЕМОСТИ\n")
        f.write(f"Дата и время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Исходный файл: {os.path.basename(source_image)}\n")
        f.write("-" * 30 + "\n")
        f.write(f"Присутствуют ({len(present_list)} чел.):\n")
        for i, name in enumerate(sorted(present_list), 1):
            f.write(f"{i}. {name}\n")
            
    return report_path

def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Выберите фотографию",
        filetypes=[("Изображения", "*.jpg *.jpeg *.png *.bmp")]
    )
    root.destroy()
    return file_path

def run_app():
    test_img_path = select_file()
    if not test_img_path: return

    print(f"\n🔍 Анализ: {os.path.basename(test_img_path)}")
    
    original_img = cv2.imread(test_img_path)
    img_v = original_img.copy()
    h_orig, w_orig, _ = img_v.shape
    start_time_all = time.time()

    # ЖЕСТКАЯ ОЧИСТКА КЭША
    print("🧹 Очистка временных индексов базы данных...")
    for file in os.listdir(DATABASE_DIR):
        if file.endswith(".pkl"):
            try:
                os.remove(os.path.join(DATABASE_DIR, file))
                print(f"🗑️ Удален старый индекс: {file}")
            except: pass

    try:
        # ЭТАП 1: Поиск лиц с помощью RetinaFace
        # Добавляем align=True для принудительного выравнивания лиц
        face_objs = DeepFace.represent(
            img_path=test_img_path,
            model_name=MODEL_FOR_RECOGNITION,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=False,
            align=True 
        )
        print(f"👥 Найдено лиц (RetinaFace): {len(face_objs)}")

        # ЭТАП 2: Сбор гипотез
        all_hypotheses = []
        face_metadata = {}

        for i, face_obj in enumerate(face_objs):
            area = face_obj.get("facial_area") or face_obj.get("box")
            if not area: continue
            
            x, y, w, h = area["x"], area["y"], area["w"], area["h"]
            face_metadata[i] = (x, y, w, h)
            
            # Вырезаем лицо для сравнения
            face_img = original_img[max(0,y-20):min(h_orig,y+h+20), max(0,x-20):min(w_orig,x+w+20)]
            
            try:
                # Ищем совпадения в базе
                results = DeepFace.find(
                    img_path=face_img, 
                    db_path=DATABASE_DIR, 
                    model_name=MODEL_FOR_RECOGNITION, 
                    detector_backend='skip', 
                    enforce_detection=False, 
                    silent=True
                )
                
                if results and not results[0].empty:
                    df = results[0]
                    for _, row in df.iterrows():
                        # Определяем колонку с дистанцией
                        dist_col = 'distance' if 'distance' in df.columns else [c for c in df.columns if 'distance' in c.lower() or 'cosine' in c.lower()][0]
                        
                        curr_dist = row[dist_col]
                        curr_name = os.path.basename(os.path.dirname(row['identity']))
                        
                        # ДЕБАГ ВЫВОД: Теперь ты увидишь ВСЕХ кандидатов
                        print(f"   [Face {i}] Кандидат: {curr_name} | Dist: {round(curr_dist, 4)} {'✅' if curr_dist <= THRESHOLD else '❌'}")
                        
                        if curr_dist <= THRESHOLD:
                            all_hypotheses.append((curr_dist, i, curr_name))
                else:
                    print(f"   [Face {i}] В базе совпадений вообще нет.")
            except Exception as e:
                print(f"   [Face {i}] Ошибка распознавания: {e}")
                continue

        # ЭТАП 3: Жадное распределение
        all_hypotheses.sort(key=lambda x: x[0])
        assigned_faces, assigned_names, final_results = set(), set(), {}

        for dist, f_idx, p_name in all_hypotheses:
            if f_idx not in assigned_faces and p_name not in assigned_names:
                final_results[f_idx] = (p_name, dist)
                assigned_faces.add(f_idx)
                assigned_names.add(p_name)

        # ЭТАП 4: Отрисовка
        students_present = []
        for f_idx, (x, y, w, h) in face_metadata.items():
            if f_idx in final_results:
                name, dist = final_results[f_idx]
                color, text = (0, 255, 0), f"{name} ({round(dist, 2)})"
                students_present.append(name)
            else:
                color, text = (0, 0, 255), "Unknown"

            cv2.rectangle(img_v, (x, y), (x + w, y + h), color, 2)
            cv2.putText(img_v, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # ЭТАП 5: Сохранение
        out_img_path = os.path.join(OUTPUT_DIR, f"res_{os.path.basename(test_img_path)}")
        cv2.imwrite(out_img_path, img_v)
        save_attendance_report(students_present, test_img_path)

        print(f"\n📊 Итог: {len(students_present)} человек опознано.")
        
        # Показываем результат
        cv2.imshow("Result (Press any key)", cv2.resize(img_v, (1000, 700)) if w_orig > 1000 else img_v)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    run_app()