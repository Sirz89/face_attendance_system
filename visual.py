import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Настройка холста высокого разрешения
fig = plt.figure(figsize=(17, 11), dpi=150)
ax = fig.add_subplot(111, aspect='equal')
ax.axis('off')

# Границы координатной сетки
plt.xlim(-0.5, 19.5)
plt.ylim(-0.5, 11.5)
plt.title("Архитектурная схема системы контроля присутствия", fontsize=18, fontweight='bold', pad=25, family='sans-serif')

# --- ФУНКЦИЯ ДЛЯ ОТРИСОВКИ ЗОН ---
def draw_zone(ax, x, y, w, h, title):
    rect = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor='#9E9E9E', facecolor='#F8F9FA', linestyle='--', zorder=1)
    ax.add_patch(rect)
    ax.text(x + 0.3, y + h - 0.4, title, ha='left', va='top', fontsize=12, color='#616161', fontweight='bold', family='sans-serif')

# --- ФУНКЦИЯ ДЛЯ БЛОКОВ (Строгие размеры без авто-паддинга) ---
def draw_block(ax, x, y, w, h, label, bg_color='#E3F2FD', border_color='#1565C0', text_color='#0D47A1', is_bold=False):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.15", 
                                  linewidth=2, edgecolor=border_color, facecolor=bg_color, zorder=10)
    ax.add_patch(rect)
    weight = 'bold' if is_bold else 'normal'
    ax.text(x + w/2, y + h/2, label, ha='center', va='center', color=text_color, 
            fontsize=10, fontweight=weight, wrap=True, zorder=11, family='sans-serif')

# --- ФУНКЦИЯ ДЛЯ ВЫРОВНЕННЫХ СТРЕЛОК ---
def draw_arrow(ax, x1, y1, x2, y2, label='', color='#424242', text_offset_y=0.15, label_pos=0.5):
    arrow = patches.FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', 
                                    mutation_scale=16, linewidth=2, edgecolor=color, facecolor=color, zorder=5)
    ax.add_patch(arrow)
    if label:
        tx = x1 + (x2 - x1) * label_pos
        ty = y1 + (y2 - y1) * label_pos + text_offset_y
        ax.text(tx, ty, label, ha='center', va='center', fontsize=9, color=color, fontweight='bold', family='sans-serif')

# === 1. РАЗМЕТКА СЕМАНТИЧЕСКИХ ЗОН ===
draw_zone(ax, 0.0, 0.5, 4.5, 10.5, "Мобильный клиент (Flet App)")
draw_zone(ax, 5.5, 0.5, 8.5, 10.5, "Серверный бэкенд (FastAPI)")
draw_zone(ax, 15.0, 4.5, 4.0, 6.5, "Слой данных (Локальный)")

# === 2. КОМПОНЕНТЫ КЛИЕНТА (Ось центрирования X=2.25) ===
draw_block(ax, 0.5, 8.5, 3.5, 1.5, "Интерфейс приложения\n(Flet UI)\n• Экран авторизации\n• Просмотр статистики", bg_color='#E8F5E9', border_color='#2E7D32', text_color='#1B5E20', is_bold=True)
draw_block(ax, 0.5, 5.5, 3.5, 1.5, "Модуль работы с медиа\n(Захват фото с камеры /\nВыбор из галереи устройства)", bg_color='#E8F5E9', border_color='#2E7D32', text_color='#1B5E20')
draw_block(ax, 0.5, 1.5, 3.5, 1.5, "Асинхронный клиент\n(HTTPX AsyncClient)", bg_color='#E8F5E9', border_color='#2E7D32', text_color='#1B5E20')

# === 3. КОМПОНЕНТЫ СЕРВЕРА ===
draw_block(ax, 6.0, 1.5, 7.5, 1.3, "FastAPI API Router\n(Обработка эндпоинта /recognize)", bg_color='#EDE7F6', border_color='#4527A0', text_color='#4A148C', is_bold=True)
draw_block(ax, 6.0, 3.5, 7.5, 1.0, "Асинхронный пул потоков\n(run_in_executor для CPU-задач)", bg_color='#EDE7F6', border_color='#4527A0', text_color='#4A148C')

# Внешний контейнер CV Пайплайна
pipeline_bg = patches.FancyBboxPatch((6.0, 5.2), 7.5, 5.4, boxstyle="round,pad=0,rounding_size=0.1", 
                                     linewidth=2, edgecolor='#C2185B', facecolor='#FCE4EC', zorder=2)
ax.add_patch(pipeline_bg)
ax.text(9.75, 10.3, "CV Пайплайн обработки снимка", ha='center', va='center', color='#C2185B', fontsize=11, fontweight='bold', family='sans-serif', zorder=3)

# Модули внутри пайплайна
draw_block(ax, 7.75, 5.6, 4.0, 1.0, "1. Детектор RetinaFace\n(Локализация всех лиц)", bg_color='#F8BBD0', border_color='#C2185B', text_color='#880E4F')
draw_block(ax, 6.3, 7.3, 3.2, 1.0, "2. Оценка качества\n(Размер лица > 40px)", bg_color='#F8BBD0', border_color='#C2185B', text_color='#880E4F')
draw_block(ax, 10.0, 7.3, 3.2, 1.0, "3. Апскейлер Real-ESRGAN\n(Восстановление лиц)", bg_color='#FFCDD2', border_color='#C62828', text_color='#B71C1C')
draw_block(ax, 7.75, 9.1, 4.0, 1.0, "4. Экстрактор ArcFace\n(Генерация 512-d вектора)", bg_color='#F8BBD0', border_color='#C2185B', text_color='#880E4F')

# === 4. КОМПОНЕНТЫ ХРАНИЛИЩА ===
draw_block(ax, 15.25, 9.1, 3.5, 1.0, "SQLAlchemy ORM\n(Менеджер сессий БД)", bg_color='#ECEFF1', border_color='#37474F', text_color='#263238')
draw_block(ax, 15.25, 5.8, 3.5, 1.6, "СУБД SQLite (Файл .db)\n\nРасширение sqlite-vec\n(Метрика: Косинусное расстояние)", bg_color='#FFF3E0', border_color='#EF6C00', text_color='#E65100', is_bold=True)

# === 5. НАПРАВЛЕНИЯ ПОТОКОВ ДАННЫХ (СТРЕЛКИ) ===
# Потоки внутри мобильного клиента
draw_arrow(ax, 2.25, 8.5, 2.25, 7.0, "Выбор фото")
draw_arrow(ax, 2.25, 5.5, 2.25, 3.0, "Передача байт")

# Сетевой асинхронный обмен (Идеально параллельные стрелки)
draw_arrow(ax, 4.0, 2.4, 6.0, 2.4, "HTTP POST ( multipart/form-data )", color='#D32F2F', text_offset_y=0.12)
draw_arrow(ax, 6.0, 1.8, 4.0, 1.8, "Ответ JSON (Список присутствующих)", color='#2E7D32', text_offset_y=-0.25)

# Внутрисерверные переходы к пайплайну
draw_arrow(ax, 9.75, 2.8, 9.75, 3.5)
draw_arrow(ax, 9.75, 4.5, 9.75, 5.6)

# Внутренний разводной пайплайн CV (Потоки условий)
draw_arrow(ax, 7.9, 6.6, 7.9, 7.3, "Нормальное качество", label_pos=0.6, text_offset_y=0.0)
draw_arrow(ax, 11.6, 6.6, 11.6, 7.3, "Низкое качество", label_pos=0.6, text_offset_y=0.0)

# Сведение результатов в ArcFace
draw_arrow(ax, 7.9, 8.3, 7.9, 9.1)
draw_arrow(ax, 11.6, 8.3, 11.6, 9.1)

# Передача вектора в слой данных
draw_arrow(ax, 11.75, 9.6, 15.25, 9.6, "512-d вектор-эмбеддинг", color='#1565C0', text_offset_y=0.15)
draw_arrow(ax, 17.0, 9.1, 17.0, 7.4, "Поиск схожих (KNN)", color='#1565C0', text_offset_y=0.0, label_pos=0.5)

# Возврат информации о найденных студентах в роутер (По свободному коридору справа)
draw_arrow(ax, 15.25, 6.3, 13.5, 2.5, "ФИО / ID найденных студентов", color='#2E7D32', text_offset_y=0.15, label_pos=0.4)

# Вывод рендера
plt.tight_layout()
plt.savefig('perfect_architecture.png', bbox_inches='tight', dpi=300)
plt.show()