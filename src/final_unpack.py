import os
import tqdm

def stream_unpack(rec_path, output_dir, chunk_size=1024*1024*100): # Читаем по 100 МБ
    print(f"--- Потоковая распаковка (Безопасно для RAM) ---")
    os.makedirs(output_dir, exist_ok=True)
    
    JPEG_START = b'\xff\xd8\xff'
    JPEG_END = b'\xff\xd9'
    
    file_size = os.path.getsize(rec_path)
    count = 0
    buffer = b""
    
    pbar = tqdm.tqdm(total=file_size, unit='B', unit_scale=True, desc="Обработка")
    
    with open(rec_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            
            buffer += chunk
            pbar.update(len(chunk))
            
            while True:
                start_idx = buffer.find(JPEG_START)
                if start_idx == -1:
                    # Оставляем только хвост, который может быть началом следующего JPEG
                    buffer = buffer[-4:] 
                    break
                
                end_idx = buffer.find(JPEG_END, start_idx)
                if end_idx == -1:
                    # Если нашли начало, но конца еще нет в буфере — читаем следующий чанк
                    buffer = buffer[start_idx:]
                    break
                
                # Извлекаем и сохраняем
                img_data = buffer[start_idx : end_idx + 2]
                
                # Сортируем по подпапкам (по 1000 штук), чтобы Windows не тормозил
                sub_folder = os.path.join(output_dir, str(count // 1000))
                if count % 1000 == 0:
                    os.makedirs(sub_folder, exist_ok=True)
                
                with open(os.path.join(sub_folder, f"face_{count}.jpg"), 'wb') as img_f:
                    img_f.write(img_data)
                
                count += 1
                # Удаляем обработанную часть из буфера
                buffer = buffer[end_idx + 2:]
                
                # Тестовая остановка, чтобы ты убедился, что РАБОТАЕТ
                if count == 1000:
                    print(f"\n✅ УРА! Первые 1000 фото в папке {output_dir}/0/")
                    print("Можешь остановить скрипт (Ctrl+C) или подождать завершения.")

    pbar.close()

if __name__ == "__main__":
    REC = r"C:\face_attendance_system\data\raw\faces_vgg_112x112\train.rec"
    OUT = r"C:\face_attendance_system\data\raw\vgg_images_extracted"
    stream_unpack(REC, OUT)