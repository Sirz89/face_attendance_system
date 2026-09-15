import tensorflow as tf
import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

def test_model(model_path, test_img_path):
    # 1. Загрузка модели
    # Загружаем модель без компиляции, чтобы избежать ошибок десериализации метрик
    model = tf.keras.models.load_model(model_path, compile=False)
    
    # 2. Загрузка и подготовка картинки
    img = cv2.imread(test_img_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Делаем "мыло" (LR)
    hr_target = cv2.resize(img_rgb, (128, 128))
    lr_input = cv2.resize(hr_target, (32, 32), interpolation=cv2.INTER_CUBIC)
    lr_upscaled = cv2.resize(lr_input, (128, 128), interpolation=cv2.INTER_CUBIC) # Вход для сети
    
    # 3. Предсказание (Нормализуем перед подачей)
    input_tensor = np.expand_dims(lr_upscaled / 255.0, axis=0)
    sr_output = model.predict(input_tensor)[0]
    sr_output = np.clip(sr_output * 255, 0, 255).astype('uint8')
    
    # 4. Визуализация
    plt.figure(figsize=(15, 5))
    titles = ['Original (Target)', 'Bicubic (Upscaled)', 'SRCNN (Enhanced)']
    imgs = [hr_target, lr_upscaled, sr_output]
    
    for i in range(3):
        plt.subplot(1, 3, i+1)
        plt.imshow(imgs[i])
        plt.title(titles[i])
        plt.axis('off')
    
    plt.show()
    print("📸 Скриншот для диплома готов!")

if __name__ == "__main__":
    MODEL = "models/face_upscaler_v1.h5"
    SUBSET_DIR = r"C:\face_attendance_system\data\processed\sr_subset\hr"
    
    # Автоматически берем первый файл из папки, чтобы не гадать с названием
    files = [f for f in os.listdir(SUBSET_DIR) if f.endswith(('.jpg', '.png'))]
    if not files:
        print(f"❌ Ошибка: В папке {SUBSET_DIR} нет картинок!")
    else:
        TEST_IMG = os.path.join(SUBSET_DIR, files[0])
        print(f"✅ Тестируем на файле: {TEST_IMG}")
        test_model(MODEL, TEST_IMG)