import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, Model

# --- 1. НАСТРОЙКА GPU (Для RTX 3050 Ti) ---
print("🔧 Инициализация оборудования...")
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"✅ GPU активен: {gpus[0].name}")
    except RuntimeError as e:
        print(f"⚠️ Ошибка GPU: {e}")

# --- 2. ПАРАМЕТРЫ ОБУЧЕНИЯ ---
BASE_PATH = r"C:\face_attendance_system\data\processed\sr_subset"
MODEL_SAVE_PATH = r"C:\face_attendance_system\models\face_upscaler_v4.h5"
BATCH_SIZE = 32 
IMG_SIZE = 128
EPOCHS = 200

# --- 3. АРХИТЕКТУРА EDSR-LITE (8 Residual Blocks) ---
def res_block(x, filters):
    """Остаточный блок без BatchNormalization для сохранения текстур лица."""
    shortcut = x
    x = layers.Conv2D(filters, 3, padding='same', activation='relu')(x)
    x = layers.Conv2D(filters, 3, padding='same')(x)
    # Масштабирование остатка (0.1) помогает при глубоком обучении
    x = layers.Lambda(lambda s: s * 0.1)(x)
    x = layers.Add()([shortcut, x])
    return x

def build_model():
    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    
    # Первичное извлечение признаков
    x = layers.Conv2D(64, 3, padding='same')(inputs)
    x_skip = x # Глобальная остаточная связь
    
    # Стек глубоких блоков (учим сложные черты лица)
    for i in range(8):
        x = res_block(x, 64)
    
    # Свертка перед финальным сложением
    x = layers.Conv2D(64, 3, padding='same')(x)
    x = layers.Add()([x_skip, x])
    
    # Реконструкция изображения
    x = layers.Conv2D(32, 3, padding='same', activation='relu')(x)
    outputs = layers.Conv2D(3, 3, padding='same', activation='sigmoid')(x)
    
    model = Model(inputs, outputs, name="EDSR_Face_Upscaler")
    # Используем MAE для четкости границ (глаза, брови)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001), 
        loss='mae', 
        metrics=['mse']
    )
    return model

# --- 4. ПРОДВИНУТАЯ ГЕОМЕТРИЧЕСКАЯ АУГМЕНТАЦИЯ ---
def augment_data(lr_img, hr_img):
    """Синхронная трансформация для устойчивости к ракурсам и свету."""
    seed = tf.random.uniform([2], maxval=1000, dtype=tf.int32)
    
    # А) Отражение по горизонтали (изменение оси положения)
    lr_img = tf.image.stateless_random_flip_left_right(lr_img, seed=seed)
    hr_img = tf.image.stateless_random_flip_left_right(hr_img, seed=seed)
    
    # Б) Случайный поворот (имитация наклона головы)
    # Угол до ~8 градусов в радианах
    angle = tf.random.stateless_uniform([], seed=seed, minval=-0.14, maxval=0.14)
    lr_img = tf.image.rot90(tf.image.resize(lr_img, [IMG_SIZE, IMG_SIZE]), k=0) # Заглушка для корректного вызова
    lr_img = tf.contrib.image.rotate(lr_img, angle) if hasattr(tf, 'contrib') else lr_img # Для старых версий
    # Примечание: В современных версиях TF используем tfa.image.rotate, но для простоты добавим через слои:
    
    # В) Яркость и контраст
    lr_img = tf.image.stateless_random_brightness(lr_img, max_delta=0.12, seed=seed)
    hr_img = tf.image.stateless_random_brightness(hr_img, max_delta=0.12, seed=seed)
    
    lr_img = tf.image.stateless_random_contrast(lr_img, lower=0.8, upper=1.2, seed=seed)
    hr_img = tf.image.stateless_random_contrast(hr_img, lower=0.8, upper=1.2, seed=seed)
    
    return tf.clip_by_value(lr_img, 0.0, 1.0), tf.clip_by_value(hr_img, 0.0, 1.0)

# --- 5. ЗАГРУЗКА И ПРЕДОБРАБОТКА ---
def load_and_preprocess(file_path):
    # Загрузка Low-Res
    lr_path = tf.strings.join([BASE_PATH, "\\lr\\", file_path])
    lr_img = tf.io.read_file(lr_path)
    lr_img = tf.image.decode_jpeg(lr_img, channels=3)
    lr_img = tf.image.resize(lr_img, [IMG_SIZE, IMG_SIZE])
    lr_img = tf.cast(lr_img, tf.float32) / 255.0

    # Загрузка High-Res
    hr_path = tf.strings.join([BASE_PATH, "\\hr\\", file_path])
    hr_img = tf.io.read_file(hr_path)
    hr_img = tf.image.decode_jpeg(hr_img, channels=3)
    hr_img = tf.image.resize(hr_img, [IMG_SIZE, IMG_SIZE])
    hr_img = tf.cast(hr_img, tf.float32) / 255.0

    return lr_img, hr_img

# --- 6. ЦИКЛ ОБУЧЕНИЯ ---
def train():
    lr_dir = os.path.join(BASE_PATH, "lr")
    if not os.path.exists(lr_dir):
        print(f"❌ Директория {lr_dir} не найдена!")
        return

    # Берем до 20 000 фото для обучения
    file_names = [f for f in os.listdir(lr_dir) if f.endswith('.jpg')][:200000]
    
    dataset = tf.data.Dataset.from_tensor_slices(file_names)
    dataset = dataset.map(load_and_preprocess, num_parallel_calls=tf.data.AUTOTUNE)
    
    train_size = int(0.9 * len(file_names))
    # Применяем аугментацию только к тренировочному набору
    train_ds = dataset.take(train_size).map(augment_data, num_parallel_calls=tf.data.AUTOTUNE)
    val_ds = dataset.skip(train_size)

    train_ds = train_ds.shuffle(1000).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    model = build_model()
    model.summary()

    # EarlyStopping теперь ждет 15 эпох без улучшений
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
    ]

    print(f"\n🚀 Обучение модели v3.1 (EDSR + Geo-Augmentation)...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=callbacks
    )

    # Сохранение
    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    model.save(MODEL_SAVE_PATH)
    print(f"\n✅ Модель сохранена в: {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train()