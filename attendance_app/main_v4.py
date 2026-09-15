import flet as ft
import flet_charts as fch  # Наш новый импорт по документации
import httpx
import os
import datetime

async def main(page: ft.Page):
    page.title = "Система посещаемости"
    
    page.window.width = 450
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    results_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    stats_container = ft.Column(spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def process_file(file_path):
        if not file_path:
            return
            
        results_list.controls.clear()
        stats_container.controls.clear()
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
            
            results_list.controls.clear()

            if response.status_code != 200:
                results_list.controls.append(
                    ft.Text(f"Ошибка сервера (Код {response.status_code}):\n{response.text[:200]}", color="red")
                )
                page.update()
                return

            try:
                data = response.json()
            except Exception:
                results_list.controls.append(
                    ft.Text(f"Сервер вернул не JSON формат:\n{response.text[:200]}", color="red")
                )
                page.update()
                return

            if data.get("status") == "success":
                students = data.get("present", [])
                if not students:
                    results_list.controls.append(ft.Text("Никто не найден", size=16))
                for name in students:
                    results_list.controls.append(
                        ft.Container(
                            content=ft.Text(f"✅ {name}", size=18, weight="bold"),
                            bgcolor="green100", 
                            padding=15,
                            border_radius=10
                        )
                    )
            else:
                results_list.controls.append(ft.Text(f"Ошибка бэкенда: {data.get('message')}", color="red"))
        
        except Exception as ex:
            results_list.controls.clear()
            results_list.controls.append(ft.Text(f"Ошибка сети/клиента: {str(ex)}", color="red"))
        
        page.update()

    login_input = ft.TextField(label="Логин", value="admin", width=300)
    pass_input = ft.TextField(label="Пароль", value="12345", password=True, width=300)

    async def handle_pick_files(e):
        files = await ft.FilePicker().pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.IMAGE
        )
        if files and len(files) > 0:
            await process_file(files[0].path)

    async def download_report(e):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        download_url = f"http://192.168.0.49:8000/export-excel?date={today}"
        await ft.UrlLauncher().launch_url(download_url)

    # --- СТАТИСТИКА ПО ОБНОВЛЕННОЙ ДОКУМЕНТАЦИИ FLET-CHARTS ---
    async def show_statistics(e):
        results_list.controls.clear()
        stats_container.controls.clear()
        stats_container.controls.append(ft.ProgressRing())
        page.update()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://192.168.0.49:8000/analytics", timeout=10.0)
                
            if response.status_code != 200:
                stats_container.controls.clear()
                stats_container.controls.append(ft.Text(f"Ошибка сервера (Код {response.status_code})", color="red"))
                page.update()
                return
                
            try:
                data = response.json()
            except Exception:
                stats_container.controls.clear()
                stats_container.controls.append(ft.Text("Ошибка парсинга JSON со статистикой", color="red"))
                page.update()
                return

            stats_container.controls.clear()
            
            # Карточки с метриками
            metrics_row = ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20,
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Сегодня", size=12, color="grey"),
                            ft.Text(str(data.get("total_today", 0)), size=24, weight="bold", color="blue")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor="blue50", padding=10, border_radius=10, width=130, height=70
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Всего в базе", size=12, color="grey"),
                            ft.Text(str(data.get("total_all_time", 0)), size=24, weight="bold", color="green")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor="green50", padding=10, border_radius=10, width=130, height=70
                    )
                ]
            )
            stats_container.controls.append(metrics_row)
            
            history = data.get("history", [])
            if history:
                stats_container.controls.append(ft.Text("Динамика посещаемости (чел.)", size=14, weight="bold"))
                
                # Заполняем группы колонок (используем свойства groups и rods из доки)
                bar_groups = []
                for index, day in enumerate(history):
                    count = day["count"]
                    bar_groups.append(
                        fch.BarChartGroup(
                            x=index,
                            rods=[
                                fch.BarChartRod(
                                    from_y=0,
                                    to_y=count,
                                    width=20,
                                    color="blue",
                                    border_radius=4,
                                    tooltip=fch.BarChartRodTooltip(f"{count} чел.")
                                )
                            ]
                        )
                    )
                
                # Создаем сам график с правильными аргументами
                chart = fch.BarChart(
                    groups=bar_groups,  # <-- Исправлено на groups
                    interactive=True,
                    left_axis=fch.ChartAxis(label_size=30),  # <-- Исправлено на label_size
                    bottom_axis=fch.ChartAxis(
                        labels=[
                            fch.ChartAxisLabel(
                                value=i, 
                                label=ft.Text(history[i]["date"][5:], size=10)
                            ) for i in range(len(history))
                        ],
                        label_size=30  # <-- Исправлено на label_size
                    ),
                    height=200,
                    width=320
                )
                stats_container.controls.append(chart)
            else:
                stats_container.controls.append(ft.Text("Данных для графика пока нет", color="grey"))
                
        except Exception as ex:
            stats_container.controls.clear()
            stats_container.controls.append(ft.Text(f"Ошибка вывода статистики: {str(ex)}", color="red"))
            
        page.update()

    async def login_click(e):
        if login_input.value == "admin" and pass_input.value == "12345":
            page.clean()
            page.add(
                ft.Text("👤 Учет посещаемости", size=25, weight="bold"),
                ft.Container(height=10),
                
                ft.Button(
                    content="📤 ВЫБРАТЬ / СДЕЛАТЬ ФОТО",
                    icon=ft.Icons.CAMERA_ALT,
                    on_click=handle_pick_files,
                    height=55, width=300,
                    style=ft.ButtonStyle(bgcolor="blue50")
                ),
                
                ft.Container(height=2),
                
                ft.Button(
                    content="📊 СКАЧАТЬ ВЕДОМОСТЬ (EXCEL)",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=download_report,
                    height=50, width=300,
                    style=ft.ButtonStyle(bgcolor="green50")
                ),
                
                ft.Container(height=2),
                
                ft.Button(
                    content="📈 ПОКАЗАТЬ СТАТИСТИКУ",
                    icon=ft.Icons.LEADERBOARD,
                    on_click=show_statistics,
                    height=50, width=300,
                    style=ft.ButtonStyle(bgcolor="orange50")
                ),
                
                ft.Divider(height=25),
                stats_container,
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
    ft.run(main)