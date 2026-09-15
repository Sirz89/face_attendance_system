import os
import pandas as pd
from tqdm import tqdm

def build_dataset_metadata(raw_data_path, output_csv):
    data_list = []
    
    # Теперь указываем путь к РАСПАКОВАННЫМ картинкам
    identities = [d for d in os.listdir(raw_data_path) if os.path.isdir(os.path.join(raw_data_path, d))]
    
    print(f"--- Индексация распакованных данных в {raw_data_path} ---")
    
    for person_id in tqdm(identities, desc="Создание реестра"):
        person_dir = os.path.join(raw_data_path, person_id)
        images = [f for f in os.listdir(person_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        for img_name in images:
            data_list.append({
                'person_id': person_id,
                'file_path': os.path.join(person_dir, img_name)
            })
            
    df = pd.DataFrame(data_list)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"\n✅ Успех! Создан файл {output_csv}. Найдено {len(df)} фото.")

if __name__ == "__main__":
    RAW_PATH = "C:/face_attendance_system/data/raw/vgg_images_extracted"
    SAVE_PATH = "C:/face_attendance_system/data/processed/vgg_metadata.csv"
    build_dataset_metadata(RAW_PATH, SAVE_PATH)