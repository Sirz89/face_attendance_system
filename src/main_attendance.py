import cv2
import os
import pickle
import numpy as np
import tensorflow as tf
from insightface.app import FaceAnalysis

# 1. Загрузка твоей модели SRCNN
model_path = r"C:\face_attendance_system\models\face_upscaler_v5.h5"
sr_model = tf.keras.models.load_model(model_path, compile=False)

# 2. Инициализация распознавания
insightface_folder = os.path.expanduser('~/.insightface')
app = FaceAnalysis(root=insightface_folder, providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

# 3. Загрузка базы данных
with open(r"C:\face_attendance_system\models\students_db.pkl", 'rb') as f:
    face_db = pickle.load(f)

def preprocess_face(face_img):
    """Улучшенная предобработка для SRCNN"""
    # Ресайз до 128x128 (входной размер твоей сети)
    face_resized = cv2.resize(face_img, (128, 128))
    
    # Улучшение гистограммы (чтобы тени не мешали распознаванию)
    yuv = cv2.cvtColor(face_resized, cv2.COLOR_BGR2YUV)
    yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])
    face_equ = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
    
    # Нормализация для нейросети
    face_input = face_equ.astype('float32') / 255.0
    return np.expand_dims(face_input, axis=0)

def recognize_face(embedding, db, threshold=0.55):
    max_score = -1
    detected_name = "Unknown"
    
    # Теперь db может содержать списки векторов для одного имени
    for name, saved_embs in db.items():
        # Если ты сохранил несколько фото под одним именем, saved_embs будет списком
        if not isinstance(saved_embs, list):
            saved_embs = [saved_embs]
            
        for db_emb in saved_embs:
            score = np.dot(embedding, db_emb) / (np.linalg.norm(embedding) * np.linalg.norm(db_emb))
            if score > max_score:
                max_score = score
                detected_name = name
                
    if max_score < threshold:
        return "Unknown", max_score
    return detected_name, max_score

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    faces = app.get(frame)
    
    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(int)
        
        # Берем кроп лица с небольшим отступом (+10%), чтобы захватить контуры
        h, w, _ = frame.shape
        pad = 20
        face_crop = frame[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
        
        if face_crop.size > 0:
            # Прогоняем через SRCNN
            face_input = preprocess_face(face_crop)
            sr_face = sr_model.predict(face_input, verbose=0)[0]
            
            # Распознавание (используем эмбеддинг из InsightFace)
            name, score = recognize_face(face.normed_embedding, face_db)
            
            # Отрисовка
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            label = f"{name}: {score:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imshow('Attendance System (Optimized)', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()