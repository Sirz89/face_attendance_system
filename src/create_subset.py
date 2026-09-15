import pandas as pd
import os
import cv2
import numpy as np
from tqdm import tqdm

def prepare_sr_data(csv_path, output_dir, n_samples=10000):
    df = pd.read_csv(csv_path)
    
    # Берем случайную выборку
    subset = df.sample(n=min(n_samples, len(df)), random_state=42)
    
    hr_dir = os.path.join(output_dir, "hr")
    lr_dir = os.path.join(output_dir, "lr")
    os.makedirs(hr_dir, exist_ok=True)
    os.makedirs(lr_dir, exist_ok=True)
    
    print(f"--- Подготовка {n_samples} пар изображений ---")
    
    for i, row in enumerate(tqdm(subset.itertuples(), total=len(subset))):
        img = cv2.imread(row.file_path)
        if img is None: continue
        
        # 1. Сохраняем оригинал (High-Res) - приводим к 128x128 для удобства
        hr_img = cv2.resize(img, (128, 128))
        cv2.imwrite(os.path.join(hr_dir, f"face_{i}.jpg"), hr_img)
        
        # 2. Создаем Low-Res (уменьшаем в 4 раза до 32x32, затем обратно с размытием)
        lr_img = cv2.resize(hr_img, (32, 32), interpolation=cv2.INTER_CUBIC)
        # Сохраняем маленькую картинку
        cv2.imwrite(os.path.join(lr_dir, f"face_{i}.jpg"), lr_img)

    print(f"\n✅ Готово! Данные для обучения SR лежат в: {output_dir}")

if __name__ == "__main__":
    CSV = r"C:\face_attendance_system\data\processed\vgg_metadata.csv"
    OUT = r"C:\face_attendance_system\data\processed\sr_subset"
    prepare_sr_data(CSV, OUT)