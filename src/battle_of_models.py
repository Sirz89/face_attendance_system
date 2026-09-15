import os
import sys
import cv2
import numpy as np

# 1. Окружение
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_USE_LEGACY_KERAS'] = '1'

# 2. Мост импортов
try:
    import tensorflow as tf
    import tf_keras as keras
    sys.modules['keras'] = keras
    sys.modules['tensorflow.keras'] = keras
    sys.modules['tensorflow.keras.models'] = keras.models
    sys.modules['tensorflow.keras.layers'] = keras.layers
    sys.modules['tensorflow.keras.preprocessing'] = keras.preprocessing
    print("✅ Мост tf_keras наведен!")
except ImportError:
    print("❌ Нужно установить мост: pip install tf-keras")
    sys.exit()

# 3. Импорт DeepFace
try:
    from deepface import DeepFace
    print("✅ СИСТЕМА ГОТОВА: DeepFace загружен!")
except Exception as e:
    print(f"❌ Ошибка DeepFace: {e}")
    sys.exit()

# Путь к базе
DB_PATH = r"C:\face_attendance_system\data\db"

def run_test():
    models = ["VGG-Face", "Facenet512", "ArcFace"]
    cap = cv2.VideoCapture(0)
    
    print("🚀 Стартуем! Нажми 'Q' для выхода.")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Для начала протестируем на самой легкой модели VGG-Face
        try:
            results = DeepFace.find(img_path=frame, 
                                    db_path=DB_PATH, 
                                    model_name=models[2],
                                    enforce_detection=False,
                                    detector_backend='opencv',
                                    silent=True)
            
            if len(results) > 0 and not results[0].empty:
                full_path = results[0]['identity'][0]
                name = os.path.basename(os.path.dirname(full_path))
                cv2.putText(frame, f"Found: {name}", (10, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        except Exception as e:
            cv2.putText(frame, "Loading models...", (10, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        cv2.imshow("Diploma Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_test()