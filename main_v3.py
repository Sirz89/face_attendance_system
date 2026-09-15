import flet as ft
import httpx
import os

async def main(page: ft.Page):
    page.title = "Система посещаемости"
    
    page.window.width = 450
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    results_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)

    async def process_file(file_path):
        if not file_path:
            results_list.controls.clear()
            results_list.controls.append(ft.Text("Укажите путь к файлу", color="red"))
            page.update()
            return
            
        results_list.controls.clear()
        results_list.controls.append(ft.ProgressRing())
        page.update()

        try:
            if not os.path.exists(file_path):
                results_list.controls.clear()
                results_list.controls.append(ft.Text("Файл не найден", color="red"))
                page.update()
                return

            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    response = await client.post(
                        "http://192.168.0.49:8000/recognize", 
                        files={"file": f},
                        timeout=180.0 
                    )
            
            data = response.json()
            results_list.controls.clear()

            if data.get("status") == "success":
                students = data.get("present", [])
                if not students:
                    results_list.controls.append(ft.Text("Никто не найден", size=16))
                for name in students:
                    results_list.controls.append(
                        ft.Container(
                            content=ft.Text(f"✅ {name}", size=18, weight="bold"),
                            bgcolor=ft.colors.GREEN_100,
                            padding=15,
                            border_radius=10
                        )
                    )
            else:
                results_list.controls.append(ft.Text(f"Ошибка: {data.get('message')}", color="red"))
        
        except Exception as ex:
            results_list.controls.clear()
            results_list.controls.append(ft.Text(f"Ошибка: {str(ex)}", color="red"))
        
        page.update()

    login_input = ft.TextField(label="Логин", value="admin", width=300)
    pass_input = ft.TextField(label="Пароль", value="12345", password=True, width=300)
    
    file_path_input = ft.TextField(
        label="Путь к фото", 
        width=300,
        hint_text="C:/Users/.../photo.jpg"
    )

    async def login_click(e):
        if login_input.value == "admin" and pass_input.value == "12345":
            page.clean()
            page.add(
                ft.Text("👤 Учет посещаемости", size=25, weight="bold"),
                ft.Container(height=20),
                
                ft.Text("📋 Выберите способ загрузки:", size=16, weight="bold"),
                ft.Container(height=10),
                
                ft.Text("📁 Для готового фото:", size=14),
                ft.Text("   Скопируйте путь к файлу и вставьте ниже", size=12, color="grey"),
                
                ft.Container(height=5),
                
                ft.Text("📸 Для фото с камеры:", size=14),
                ft.Text("   Сделайте снимок и укажите путь к файлу", size=12, color="grey"),
                
                ft.Container(height=15),
                
                file_path_input,
                
                ft.Container(height=10),
                
                ft.ElevatedButton(
                    "📤 ОТПРАВИТЬ НА РАСПОЗНАВАНИЕ",
                    on_click=lambda e: process_file(file_path_input.value),
                    height=60, width=300
                ),
                
                ft.Divider(height=40),
                results_list
            )
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Неверный пароль"))
            page.snack_bar.open = True
            page.update()

    page.add(
        ft.Text("👤", size=80),
        ft.Text("Вход в систему", size=30, weight="bold"),
        login_input,
        pass_input,
        ft.FilledButton("🔑 ВОЙТИ", on_click=login_click, width=300, height=50),
    )

if __name__ == "__main__":
    ft.app(target=main)