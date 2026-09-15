import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, Model

# --- НАСТРОЙКА GPU ---
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError:
        pass

# --- ПАРАМЕТРЫ ---
BASE_PATH = r"C:\face_attendance_system\data\processed\sr_subset"
MODEL_SAVE_PATH = r"C:\face_attendance_system\models\face_upscaler_v5.h5"
BATCH_SIZE = 32 
IMG_SIZE = 128
EPOCHS = 100

# --- CHARBONNIER LOSS (Для максимальной резкости) ---
def charbonnier_loss(y_true, y_pred):
    epsilon = 1e-3
    return tf.reduce_mean(tf.sqrt(tf.square(y_true - y_pred) + tf.square(epsilon)))

# --- АРХИТЕКТУРА V4 (High-Frequency Recovery) ---
def build_v5_model():
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    
    # 1. Входной блок (делаем 64 фильтра, чтобы совпадало с блоками ниже)
    x = layers.Conv2D(64, 3, padding='same', activation='relu')(inputs)
    x_skip_global = x 
    
    # 2. Глубокий стек Residual блоков
    for i in range(8):
        shortcut = x
        x = layers.Conv2D(64, 3, padding='same', activation='relu')(x)
        x = layers.Conv2D(64, 3, padding='same')(x)
        # Теперь оба тензора имеют форму (128, 128, 64) — ошибка исчезнет
        x = layers.Add()([shortcut, x])
        x = layers.Activation('relu')(x)
    
    # 3. Финальная сборка деталей
    x = layers.Conv2D(64, 3, padding='same')(x)
    x = layers.Add()([x_skip_global, x])
    
    x = layers.Conv2D(32, 3, padding='same', activation='relu')(x)
    outputs = layers.Conv2D(3, 3, padding='same', activation='sigmoid')(x)
    
    model = Model(inputs, outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(2e-4), loss=charbonnier_loss)
    return model

# --- УСИЛЕННАЯ АУГМЕНТАЦИЯ (Геометрия + Тон) ---
def augment_data(lr_img, hr_img):
    seed = tf.random.uniform([2], maxval=1000, dtype=tf.int32)
    
    # 1. Горизонтальный переворот (Flip) - ОСТАВЛЯЕМ, это важно для точности
    lr_img = tf.image.stateless_random_flip_left_right(lr_img, seed=seed)
    hr_img = tf.image.stateless_random_flip_left_right(hr_img, seed=seed)
    
    # 2. Насыщенность (вместо размытия) - помогает при разном освещении
    lr_img = tf.image.stateless_random_saturation(lr_img, lower=0.5, upper=1.5, seed=seed)
    hr_img = tf.image.stateless_random_saturation(hr_img, lower=0.5, upper=1.5, seed=seed)
    
    # 3. Оттенок (Hue) - очень эффективно для борьбы с ложными срабатываниями
    lr_img = tf.image.stateless_random_hue(lr_img, max_delta=0.05, seed=seed)
    hr_img = tf.image.stateless_random_hue(hr_img, max_delta=0.05, seed=seed)
    
    # 4. Яркость
    lr_img = tf.image.stateless_random_brightness(lr_img, max_delta=0.1, seed=seed)
    hr_img = tf.image.stateless_random_brightness(hr_img, max_delta=0.1, seed=seed)

    return tf.clip_by_value(lr_img, 0.0, 1.0), tf.clip_by_value(hr_img, 0.0, 1.0)

# --- ЗАГРУЗКА ---
def load_and_preprocess(file_path):
    def read_img(subdir):
        path = tf.strings.join([BASE_PATH, subdir, file_path])
        img = tf.io.read_file(path)
        img = tf.image.decode_jpeg(img, channels=3)
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        return tf.cast(img, tf.float32) / 255.0

    return read_img("\\lr\\"), read_img("\\hr\\")

def train():
    lr_dir = os.path.join(BASE_PATH, "lr")
    file_names = [f for f in os.listdir(lr_dir) if f.endswith('.jpg')][:15000]
    
    dataset = tf.data.Dataset.from_tensor_slices(file_names).map(load_and_preprocess)
    
    train_size = int(0.9 * len(file_names))
    train_ds = dataset.take(train_size).map(augment_data).shuffle(1000).batch(BATCH_SIZE).prefetch(2)
    val_ds = dataset.skip(train_size).batch(BATCH_SIZE).prefetch(2)

    model = build_v5_model()
    
    # Убираем жесткий EarlyStopping, даем модели поучиться
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=20, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=7)
    ]

    print("🚀 Обучение финальной модели V4 Precision...")
    model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)
    model.save(MODEL_SAVE_PATH)

if __name__ == "__main__":
    train()