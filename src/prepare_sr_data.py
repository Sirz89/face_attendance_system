import pandas as pd
import os
import cv2
from tqdm import tqdm

def make_subset(csv_path, output_dir, n=10000):
    df = pd.read_csv(csv_path)
    subset = df.sample(n=min(n, len(df)))
    
    os.makedirs(os.path.join(output_dir, "hr"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "lr"), exist_ok=True)
    
    for i, row in enumerate(tqdm(subset.itertuples(), total=len(subset))):
        img = cv2.imread(row.file_path)
        if img is None: continue
        
        # Делаем эталон (128x128)
        hr = cv2.resize(img, (128, 128))
        # Делаем "мыло" для обучения (32x32)
        lr = cv2.resize(hr, (32, 32), interpolation=cv2.INTER_CUBIC)
        
        cv2.imwrite(os.path.join(output_dir, f"hr/f_{i}.jpg"), hr)
        cv2.imwrite(os.path.join(output_dir, f"lr/f_{i}.jpg"), lr)

if __name__ == "__main__":
    make_subset(r"C:\face_attendance_system\data\processed\vgg_metadata.csv", 
                r"C:\face_attendance_system\data\processed\sr_subset")