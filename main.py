import flet as ft
import httpx
import os
import datetime
import asyncio
from difflib import get_close_matches

async def main(page: ft.Page):
    page.title = "Система посещаемости"
    
    page.window.width = 450
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    page.padding = ft.padding.Padding(top=40, left=20, right=20, bottom=20)
    page.scroll = ft.ScrollMode.ADAPTIVE

    results_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    stats_container = ft.Column(spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.ADAPTIVE)
    students_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    users_list = ft.Column(spacing=10, scroll=ft.ScrollMode.ADAPTIVE)
    
    now = datetime.datetime.now()
    selected_date = now.strftime("%d.%m.%Y")
    date_text = ft.Text(f"📅 Выбрана дата: {selected_date}", size=14)
    
    preview_image = ft.Image(src="", width=300, height=300, fit=ft.BoxFit.COVER, visible=False)
    preview_text = ft.Text("", size=14, color="grey", visible=False)
    
    recognized_students = []
    edit_mode = False
    selected_group = "Все группы"
    groups_list = ["Все группы", "22ВТ-09.03.03.01-о1", "22ВТ-09.03.03.01-о2", "22ВТ-09.03.03.01-о3"]
    
    cached_students = []
    current_user = {"username": "", "role": ""}

    def create_empty_state(message, icon="📭"):
        return ft.Container(
            content=ft.Column([
                ft.Text(icon, size=60),
                ft.Text(message, size=16, color="grey", text_align=ft.TextAlign.CENTER)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=30, border_radius=15, bgcolor="grey100", width=300
        )

    def create_section_header(title, on_close):
        return ft.Row([
            ft.Text(title, size=16, weight="bold"),
            ft.IconButton(icon=ft.Icons.CLOSE, icon_size=20, icon_color="red", on_click=on_close),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def close_students_list(e=None):
        students_list.controls.clear()
        users_list.controls.clear()
        page.update()

    def close_statistics(e=None):
        stats_container.controls.clear()
        page.update()

    def close_results(e=None):
        results_list.controls.clear()
        page.update()

    async def load_groups_from_server():
        nonlocal groups_list
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://192.168.31.34:8000/groups", timeout=5.0)
                if response.status_code == 200:
                    server_groups = response.json()
                    if server_groups and len(server_groups) > 1:
                        groups_list = server_groups
        except:
            pass

    def normalize_name(name):
        parts = name.split()
        normalized_parts = []
        for part in parts:
            if part:
                normalized_parts.append(part.capitalize())
        return " ".join(normalized_parts)

    def find_similar_students(name):
        all_names = [s.get('name', '') for s in cached_students]
        matches = get_close_matches(name, all_names, n=3, cutoff=0.6)
        return matches

    def is_student_exists_full(name, students_list_data=None):
        if students_list_data is None:
            students_list_data = cached_students
        input_parts = name.lower().split()
        for student in students_list_data:
            existing_name = student.get('name', '').lower()
            existing_parts = existing_name.split()
            if len(input_parts) >= 2 and len(existing_parts) >= 2:
                if input_parts[0] == existing_parts[0] and input_parts[1] == existing_parts[1]:
                    if len(input_parts) >= 3 and len(existing_parts) >= 3:
                        if input_parts[2] == existing_parts[2]:
                            return True, student.get('name', '')
                    elif len(input_parts) == 2 and len(existing_parts) == 2:
                        return True, student.get('name', '')
                    elif len(input_parts) == 2:
                        return True, student.get('name', '')
        return False, None

    def is_student_exists_partial(name, students_list_data=None):
        if students_list_data is None:
            students_list_data = cached_students
        input_parts = name.lower().split()
        if len(input_parts) < 2:
            return False, None
        input_lastname = input_parts[0]
        input_firstname = input_parts[1]
        for student in students_list_data:
            existing_name = student.get('name', '').lower()
            existing_parts = existing_name.split()
            if len(existing_parts) >= 2:
                if input_lastname == existing_parts[0] and input_firstname == existing_parts[1]:
                    return True, student.get('name', '')
        return False, None

    def show_student_exists_dialog(full_name, similar_students=None):
        message = f"Студент «{full_name}» уже есть в базе данных."
        content_controls = [ft.Text(message, size=16)]
        if similar_students:
            content_controls.append(ft.Container(height=10))
            content_controls.append(ft.Text("Возможно, вы имели в виду:", size=14, color="grey"))
            for s in similar_students[:3]:
                content_controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"• {s}", size=14),
                            ft.TextButton("Выбрать", on_click=lambda e, name=s: select_similar(name)),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.only(left=10)
                    )
                )
        
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        def select_similar(name):
            dialog.open = False
            page.update()
            page.snack_bar = ft.SnackBar(ft.Text(f"Выбран студент: {name}"), bgcolor="blue")
            page.snack_bar.open = True
            page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ Студент уже существует"),
            content=ft.Column(content_controls, width=300),
            actions=[ft.TextButton("Понятно", on_click=close_dialog)],
            open=True
        )
        page.overlay.append(dialog)
        page.update()

    async def process_file(file_path):
        nonlocal recognized_students, edit_mode
        if not file_path:
            return
        results_list.controls.clear()
        stats_container.controls.clear()
        students_list.controls.clear()
        users_list.controls.clear()
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
                    response = await client.post("http://192.168.31.34:8000/recognize", files={"file": f}, timeout=180.0)
            
            results_list.controls.clear()

            if response.status_code != 200:
                results_list.controls.append(ft.Text(f"Ошибка сервера (Код {response.status_code})", color="red"))
                page.update()
                return

            data = response.json()

            if data.get("status") == "success":
                recognized_students = data.get("present", [])
                edit_mode = False
                results_list.controls.append(create_section_header("Результаты распознавания", close_results))
                if not recognized_students:
                    results_list.controls.append(create_empty_state("Никто не найден на этом фото", "👤"))
                else:
                    show_recognized_students()
            else:
                results_list.controls.append(ft.Text(f"Ошибка бэкенда: {data.get('message')}", color="red"))
        except Exception as ex:
            results_list.controls.clear()
            results_list.controls.append(ft.Text(f"Ошибка: {str(ex)}", color="red"))
        
        preview_image.visible = False
        preview_text.visible = False
        page.update()

    def show_recognized_students():
        while len(results_list.controls) > 1:
            results_list.controls.pop()
        
        results_list.controls.append(ft.Text(f"✅ Найдено: {len(recognized_students)} чел.", size=16, weight="bold"))
        
        for name in recognized_students:
            controls_row = [ft.Text(f"✅ {name}", size=18, weight="bold")]
            if edit_mode:
                controls_row.append(ft.IconButton(icon=ft.Icons.DELETE, icon_size=20, icon_color="red", on_click=lambda e, n=name: remove_student(n)))
            results_list.controls.append(ft.Container(content=ft.Row(controls_row, alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor="green100", padding=15, border_radius=10))
        
        if not edit_mode:
            edit_btn = ft.ElevatedButton("✏️ РЕДАКТИРОВАТЬ", on_click=lambda e: toggle_edit_mode(), height=45, style=ft.ButtonStyle(bgcolor="orange50"))
            save_btn = ft.ElevatedButton("💾 СОХРАНИТЬ", on_click=lambda e: asyncio.create_task(save_to_database()), height=45, style=ft.ButtonStyle(bgcolor="green50"))
            results_list.controls.append(ft.Row([edit_btn, save_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=10))
        else:
            lastname_field = ft.TextField(label="Фамилия", width=200, height=40)
            firstname_field = ft.TextField(label="Имя", width=200, height=40)
            middlename_field = ft.TextField(label="Отчество", width=200, height=40)
            
            def add_from_fields(e):
                lastname = lastname_field.value.strip()
                firstname = firstname_field.value.strip()
                middlename = middlename_field.value.strip()
                if lastname and firstname:
                    full_name = normalize_name(f"{lastname} {firstname} {middlename}".strip())
                    if full_name.lower() in [s.lower() for s in recognized_students]:
                        page.snack_bar = ft.SnackBar(ft.Text("❌ Этот студент уже в списке"))
                        page.snack_bar.open = True
                        page.update()
                        return
                    add_student(full_name)
                    lastname_field.value = ""
                    firstname_field.value = ""
                    middlename_field.value = ""
                    lastname_field.update()
                    firstname_field.update()
                    middlename_field.update()
            
            results_list.controls.append(ft.Column([
                lastname_field, ft.Container(height=5),
                firstname_field, ft.Container(height=5),
                middlename_field, ft.Container(height=10),
                ft.ElevatedButton("➕ ДОБАВИТЬ", on_click=add_from_fields, height=40, width=200),
                ft.Container(height=10),
                ft.ElevatedButton("✅ ГОТОВО", on_click=lambda e: toggle_edit_mode(), height=45, style=ft.ButtonStyle(bgcolor="blue50")),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
        page.update()

    def toggle_edit_mode():
        nonlocal edit_mode
        edit_mode = not edit_mode
        show_recognized_students()

    def remove_student(name):
        nonlocal recognized_students
        recognized_students = [s for s in recognized_students if s != name]
        show_recognized_students()

    def add_student(name):
        nonlocal recognized_students
        if name and name not in recognized_students:
            recognized_students.append(name)
            show_recognized_students()

    async def save_to_database():
        try:
            if not recognized_students:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Нет студентов для сохранения"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return
            
            date_for_server = datetime.datetime.strptime(selected_date, "%d.%m.%Y").strftime("%Y-%m-%d")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://192.168.31.34:8000/save-attendance",
                    json={"students": recognized_students, "group": selected_group if selected_group != "Все группы" else "", "date": date_for_server},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        page.snack_bar = ft.SnackBar(ft.Text(f"✅ {data.get('message', 'Сохранено')}"), bgcolor="green")
                    else:
                        page.snack_bar = ft.SnackBar(ft.Text(f"❌ {data.get('message')}"), bgcolor="red")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text(f"❌ Ошибка сервера ({response.status_code})"), bgcolor="red")
                page.snack_bar.open = True
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
        page.update()

    async def pick_photo(e):
        files = await ft.FilePicker().pick_files(allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE)
        if files and len(files) > 0:
            file_path = files[0].path
            preview_image.src = file_path
            preview_image.visible = True
            preview_text.value = f"📁 {os.path.basename(file_path)}"
            preview_text.visible = True
            page.update()
            await process_file(file_path)

    async def download_report(e):
        nonlocal selected_date
        date_for_server = datetime.datetime.strptime(selected_date, "%d.%m.%Y").strftime("%Y-%m-%d")
        group_param = selected_group if selected_group != "Все группы" else ""
        download_url = f"http://192.168.31.34:8000/export-excel?date={date_for_server}&group={group_param}"
        await page.launch_url(download_url)

    async def show_statistics(e):
        nonlocal selected_date
        results_list.controls.clear()
        students_list.controls.clear()
        users_list.controls.clear()
        stats_container.controls.clear()
        stats_container.controls.append(ft.ProgressRing())
        page.update()
        
        date_for_server = datetime.datetime.strptime(selected_date, "%d.%m.%Y").strftime("%Y-%m-%d")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://192.168.31.34:8000/analytics?date={date_for_server}", timeout=10.0)
                
            if response.status_code != 200:
                stats_container.controls.clear()
                stats_container.controls.append(ft.Text("Ошибка сервера", color="red"))
                page.update()
                return
                
            data = response.json()
            stats_container.controls.clear()
            stats_container.controls.append(create_section_header(f"📊 Статистика на {selected_date}", close_statistics))
            
            total_today = data.get("total_today", 0)
            total_all = data.get("total_all_time", 0)
            
            if total_today == 0 and total_all == 0:
                stats_container.controls.append(create_empty_state("За выбранную дату данных нет", "📅"))
            else:
                stats_container.controls.append(ft.Row([
                    ft.Container(content=ft.Column([ft.Text("За дату", size=12, color="grey"), ft.Text(str(total_today), size=24, weight="bold", color="blue")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="blue50", padding=10, border_radius=10, width=130, height=70),
                    ft.Container(content=ft.Column([ft.Text("Всего в базе", size=12, color="grey"), ft.Text(str(total_all), size=24, weight="bold", color="green")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="green50", padding=10, border_radius=10, width=130, height=70)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20))
                
                history = data.get("history", [])
                if history:
                    stats_container.controls.append(ft.Text("Динамика посещаемости (чел.)", size=14, weight="bold"))
                    max_count = max(day["count"] for day in history) if history else 1
                    chart_columns = []
                    for day in history:
                        count = day["count"]
                        day_date = datetime.datetime.strptime(day["date"], "%Y-%m-%d")
                        date_label = day_date.strftime("%d.%m")
                        height = max(20, int((count / max_count) * 150)) if max_count > 0 else 20
                        chart_columns.append(ft.Column([ft.Text(str(count), size=12, weight="bold"), ft.Container(bgcolor="blue", width=30, height=height, border_radius=4), ft.Text(date_label, size=10, color="grey")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER))
                    stats_container.controls.append(ft.Container(content=ft.Row(chart_columns, alignment=ft.MainAxisAlignment.CENTER, spacing=10), bgcolor="white", padding=20, border_radius=10, width=320))
                else:
                    stats_container.controls.append(create_empty_state("Данных для графика пока нет", "📈"))
        except Exception as ex:
            stats_container.controls.clear()
            stats_container.controls.append(ft.Text(f"Ошибка: {str(ex)}", color="red"))
        page.update()

    async def delete_student_from_server(student_id):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"http://192.168.31.34:8000/students/{student_id}", timeout=10.0)
                if response.status_code == 200:
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Студент удален"), bgcolor="green")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Ошибка удаления"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                await refresh_students_list()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    async def refresh_students_list():
        nonlocal cached_students
        students_list.controls.clear()
        students_list.controls.append(ft.ProgressRing())
        page.update()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://192.168.31.34:8000/students", timeout=10.0)
                
            if response.status_code != 200:
                students_list.controls.clear()
                students_list.controls.append(ft.Text("Ошибка загрузки", color="red"))
                page.update()
                return
                
            data = response.json()
            cached_students = data
            students_list.controls.clear()
            students_list.controls.append(create_section_header(f"📋 Студенты ({len(data)} чел.)", close_students_list))
            
            if not data:
                students_list.controls.append(create_empty_state("Список студентов пуст", "📋"))
            else:
                for student in data:
                    student_id = student.get('id')
                    delete_btn = ft.IconButton(icon=ft.Icons.DELETE, icon_size=20, icon_color="red", data=student_id, on_click=lambda e: asyncio.create_task(delete_student_from_server(e.control.data)))
                    students_list.controls.append(ft.Container(content=ft.Row([ft.Column([ft.Text(f"👤 {student.get('name', '')}", size=16, weight="bold"), ft.Text(f"Группа: {student.get('group', 'Не указана')}", size=12, color="grey")], expand=True), delete_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor="white", padding=15, border_radius=10, border=ft.Border(left=ft.BorderSide(1, "grey200"), right=ft.BorderSide(1, "grey200"), top=ft.BorderSide(1, "grey200"), bottom=ft.BorderSide(1, "grey200"))))
        except Exception as ex:
            students_list.controls.clear()
            students_list.controls.append(ft.Text(f"Ошибка: {str(ex)}", color="red"))
        page.update()

    async def show_students_list(e):
        await refresh_students_list()

    async def show_audit_log(e):
        students_list.controls.clear()
        stats_container.controls.clear()
        results_list.controls.clear()
        users_list.controls.clear()
        users_list.controls.append(ft.ProgressRing())
        page.update()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://192.168.31.34:8000/audit?limit=30", timeout=10.0)
                
            if response.status_code == 200:
                logs = response.json()
                users_list.controls.clear()
                users_list.controls.append(create_section_header("📝 Журнал действий", close_students_list))
                
                if not logs:
                    users_list.controls.append(create_empty_state("Журнал пуст", "📝"))
                else:
                    for log in logs:
                        users_list.controls.append(ft.Container(content=ft.Column([ft.Row([ft.Text(f"👤 {log['user_name']}", size=14, weight="bold"), ft.Text(log['timestamp'], size=10, color="grey")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Text(log['action'], size=13), ft.Text(log.get('details', ''), size=11, color="grey") if log.get('details') else ft.Text("")]), bgcolor="white", padding=10, border_radius=10, border=ft.Border(left=ft.BorderSide(1, "grey200"), right=ft.BorderSide(1, "grey200"), top=ft.BorderSide(1, "grey200"), bottom=ft.BorderSide(1, "grey200"))))
        except:
            users_list.controls.clear()
            users_list.controls.append(ft.Text("Ошибка загрузки журнала", color="red"))
        page.update()

    def add_new_student(e):
        group_options = [g for g in groups_list if g != "Все группы"]
        lastname_field = ft.TextField(label="Фамилия", width=280)
        firstname_field = ft.TextField(label="Имя", width=280)
        middlename_field = ft.TextField(label="Отчество (необязательно)", width=280)
        group_dropdown = ft.Dropdown(label="Выберите группу", width=280, options=[ft.dropdown.Option(g) for g in group_options])
        if group_options:
            group_dropdown.value = group_options[0] if selected_group == "Все группы" else selected_group
        
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        def save_student(e):
            lastname = lastname_field.value.strip()
            firstname = firstname_field.value.strip()
            middlename = middlename_field.value.strip()
            group = group_dropdown.value
            
            if not lastname or not firstname:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Фамилия и Имя обязательны"))
                page.snack_bar.open = True
                page.update()
                return
            
            full_name = normalize_name(f"{lastname} {firstname} {middlename}".strip())
            
            exists_full, _ = is_student_exists_full(full_name)
            if exists_full:
                dialog.open = False
                page.update()
                show_student_exists_dialog(full_name)
                return
            
            exists_partial, _ = is_student_exists_partial(full_name)
            if exists_partial:
                similar = find_similar_students(full_name)
                dialog.open = False
                page.update()
                show_student_exists_dialog(full_name, similar)
                return
            
            async def send_to_server():
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post("http://192.168.31.34:8000/students", json={"name": full_name, "group": group if group else ""}, timeout=10.0)
                        if response.status_code == 200:
                            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Студент {full_name} добавлен"), bgcolor="green")
                            page.snack_bar.open = True
                            page.update()
                            await load_groups_from_server()
                            if students_list.controls:
                                await refresh_students_list()
                        else:
                            error_data = response.json()
                            page.snack_bar = ft.SnackBar(ft.Text(f"❌ {error_data.get('message', 'Ошибка')}"), bgcolor="red")
                            page.snack_bar.open = True
                            page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
                dialog.open = False
                page.update()
            
            asyncio.create_task(send_to_server())
        
        dialog = ft.AlertDialog(title=ft.Text("Добавить студента"), content=ft.Column([lastname_field, ft.Container(height=10), firstname_field, ft.Container(height=10), middlename_field, ft.Container(height=10), group_dropdown], width=300), actions=[ft.TextButton("Отмена", on_click=close_dialog), ft.ElevatedButton("Сохранить", on_click=save_student)], open=True)
        page.overlay.append(dialog)
        page.update()

    def add_new_user(e):
        username_field = ft.TextField(label="Логин", width=280)
        password_field = ft.TextField(label="Пароль", width=280, password=True)
        role_dropdown = ft.Dropdown(label="Роль", width=280, options=[ft.dropdown.Option("teacher", "Преподаватель"), ft.dropdown.Option("headman", "Староста")], value="teacher")
        
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        def save_user(e):
            if not username_field.value.strip() or not password_field.value.strip():
                page.snack_bar = ft.SnackBar(ft.Text("❌ Все поля обязательны"))
                page.snack_bar.open = True
                page.update()
                return
            
            async def send_to_server():
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post("http://192.168.31.34:8000/users", json={"username": username_field.value.strip(), "password": password_field.value.strip(), "role": role_dropdown.value}, timeout=10.0)
                        if response.status_code == 200:
                            data = response.json()
                            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Пользователь добавлен" if data.get("status") == "success" else f"❌ {data.get('message')}"), bgcolor="green" if data.get("status") == "success" else "red")
                            page.snack_bar.open = True
                            page.update()
                except Exception as ex:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
                dialog.open = False
                page.update()
            
            asyncio.create_task(send_to_server())
        
        dialog = ft.AlertDialog(title=ft.Text("Добавить пользователя"), content=ft.Column([username_field, ft.Container(height=10), password_field, ft.Container(height=10), role_dropdown], width=300), actions=[ft.TextButton("Отмена", on_click=close_dialog), ft.ElevatedButton("Сохранить", on_click=save_user)], open=True)
        page.overlay.append(dialog)
        page.update()

    async def show_users_list(e):
        students_list.controls.clear()
        stats_container.controls.clear()
        results_list.controls.clear()
        users_list.controls.clear()
        users_list.controls.append(ft.ProgressRing())
        page.update()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://192.168.31.34:8000/users", timeout=10.0)
            if response.status_code == 200:
                users = response.json()
                users_list.controls.clear()
                users_list.controls.append(create_section_header(f"👥 Пользователи ({len(users)} чел.)", close_students_list))
                for user in users:
                    role_text = {"admin": "Администратор", "teacher": "Преподаватель", "headman": "Староста"}.get(user['role'], user['role'])
                    delete_btn = ft.IconButton(icon=ft.Icons.DELETE, icon_size=20, icon_color="red", data=user['id'], on_click=lambda e: asyncio.create_task(delete_user_from_server(e.control.data)), visible=user['role'] != "admin")
                    users_list.controls.append(ft.Container(content=ft.Row([ft.Column([ft.Text(f"👤 {user['username']}", size=14, weight="bold"), ft.Text(f"Роль: {role_text}", size=12, color="grey")], expand=True), delete_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor="white", padding=15, border_radius=10, border=ft.Border(left=ft.BorderSide(1, "grey200"), right=ft.BorderSide(1, "grey200"), top=ft.BorderSide(1, "grey200"), bottom=ft.BorderSide(1, "grey200"))))
        except:
            users_list.controls.clear()
            users_list.controls.append(ft.Text("Ошибка загрузки пользователей", color="red"))
        page.update()

    async def delete_user_from_server(user_id):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"http://192.168.31.34:8000/users/{user_id}", timeout=10.0)
                if response.status_code == 200:
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Пользователь удален"), bgcolor="green")
                    page.snack_bar.open = True
                    page.update()
                    await show_users_list(None)
                else:
                    data = response.json()
                    page.snack_bar = ft.SnackBar(ft.Text(f"❌ {data.get('message', 'Ошибка')}"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    async def clear_attendance_for_date():
        date_for_server = datetime.datetime.strptime(selected_date, "%d.%m.%Y").strftime("%Y-%m-%d")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"http://192.168.31.34:8000/clear-attendance?date={date_for_server}", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    page.snack_bar = ft.SnackBar(ft.Text(f"✅ {data.get('message', 'Данные очищены')}"), bgcolor="green")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Ошибка очистки"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    def show_clear_all_dialog():
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        def confirm_clear(e):
            dialog.open = False
            page.update()
            asyncio.create_task(clear_all_data())
        
        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ Полная очистка данных"),
            content=ft.Text("Вы уверены? Будут удалены:\n• Все записи посещаемости\n• Список студентов\n• Журнал действий\n\nЭто действие нельзя отменить!", size=14),
            actions=[ft.TextButton("Отмена", on_click=close_dialog), ft.ElevatedButton("Удалить всё", on_click=confirm_clear, style=ft.ButtonStyle(bgcolor="red", color="white"))],
            open=True
        )
        page.overlay.append(dialog)
        page.update()

    async def clear_all_data():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete("http://192.168.31.34:8000/clear-all", timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    page.snack_bar = ft.SnackBar(ft.Text(f"✅ {data.get('message', 'Данные очищены')}"), bgcolor="green")
                    page.snack_bar.open = True
                    page.update()
                    await refresh_students_list()
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Ошибка очистки"), bgcolor="red")
                    page.snack_bar.open = True
                    page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {str(ex)}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    async def show_main_screen():
        page.clean()
        
        # Загружаем группы с сервера
        await load_groups_from_server()
        
        def on_date_change(e):
            nonlocal selected_date
            if e.control.value:
                picked = e.control.value
                corrected = picked + datetime.timedelta(days=1)
                today = datetime.datetime.now().date()
                if corrected.date() > today:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Нельзя выбрать будущую дату"))
                    page.snack_bar.open = True
                    page.update()
                    return
                selected_date = corrected.strftime("%d.%m.%Y")
                date_text.value = f"📅 Выбрана дата: {selected_date}"
                page.update()
        
        date_picker = ft.DatePicker(first_date=datetime.datetime(2020, 1, 1), last_date=datetime.datetime.now(), on_change=on_date_change)
        page.overlay.append(date_picker)
        
        def open_date_picker(e):
            date_picker.open = True
            page.update()
        
        def on_group_change(e):
            nonlocal selected_group
            selected_group = group_dropdown.value
            page.update()
        
        group_dropdown = ft.Dropdown(
            label="Выберите группу",
            width=300,
            value=selected_group,
            options=[ft.dropdown.Option(group) for group in groups_list],
        )
        group_dropdown.on_change = on_group_change
        
        main_column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        main_column.controls.extend([
            ft.Container(height=20),
            ft.Row([ft.Text(f"👤 {current_user['username']}", size=14, color="grey"), ft.TextButton("Выйти", on_click=logout_click)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text("👤 Учет посещаемости", size=25, weight="bold"),
            ft.Container(height=20),
            group_dropdown,
            ft.Container(height=15),
            ft.ElevatedButton("📤 ВЫБРАТЬ ФОТО / СДЕЛАТЬ СНИМОК", on_click=pick_photo, height=60, width=300, style=ft.ButtonStyle(bgcolor="blue50")),
            ft.Container(height=15),
            preview_text,
            preview_image,
            ft.Container(height=15), ft.Divider(), ft.Container(height=15),
            ft.ElevatedButton("📅 ВЫБРАТЬ ДАТУ", on_click=open_date_picker, height=45, width=300),
            date_text,
            ft.Container(height=15),
            ft.ElevatedButton("📊 СКАЧАТЬ ВЕДОМОСТЬ (EXCEL)", on_click=download_report, height=50, width=300, style=ft.ButtonStyle(bgcolor="green50")),
            ft.Container(height=5),
            ft.ElevatedButton("📈 ПОКАЗАТЬ СТАТИСТИКУ", on_click=lambda e: asyncio.create_task(show_statistics(e)), height=50, width=300, style=ft.ButtonStyle(bgcolor="orange50")),
            ft.Container(height=5),
            ft.ElevatedButton("📋 СПИСОК СТУДЕНТОВ", on_click=lambda e: asyncio.create_task(show_students_list(e)), height=50, width=300, style=ft.ButtonStyle(bgcolor="purple50")),
            ft.Container(height=5),
            ft.ElevatedButton("➕ ДОБАВИТЬ СТУДЕНТА", on_click=lambda e: add_new_student(e), height=50, width=300, style=ft.ButtonStyle(bgcolor="teal50")),
        ])
        
        if current_user.get("role") == "admin":
            main_column.controls.extend([
                ft.Container(height=5),
                ft.ElevatedButton("👥 ПОЛЬЗОВАТЕЛИ", on_click=lambda e: asyncio.create_task(show_users_list(e)), height=50, width=300, style=ft.ButtonStyle(bgcolor="bluegrey50")),
                ft.Container(height=5),
                ft.ElevatedButton("➕ ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ", on_click=lambda e: add_new_user(e), height=50, width=300, style=ft.ButtonStyle(bgcolor="bluegrey100")),
                ft.Container(height=5),
                ft.ElevatedButton("📝 ЖУРНАЛ ДЕЙСТВИЙ", on_click=lambda e: asyncio.create_task(show_audit_log(e)), height=50, width=300, style=ft.ButtonStyle(bgcolor="brown50")),
                ft.Container(height=5),
                ft.ElevatedButton("🗑️ ОЧИСТИТЬ СТАТИСТИКУ ЗА ДАТУ", on_click=lambda e: asyncio.create_task(clear_attendance_for_date()), height=50, width=300, style=ft.ButtonStyle(bgcolor="red100")),
                ft.Container(height=5),
                ft.ElevatedButton("⚠️ ПОЛНАЯ ОЧИСТКА ВСЕХ ДАННЫХ", on_click=lambda e: show_clear_all_dialog(), height=50, width=300, style=ft.ButtonStyle(bgcolor="red200")),
            ])
        
        main_column.controls.append(ft.Divider(height=25))
        main_column.controls.append(stats_container)
        main_column.controls.append(students_list)
        main_column.controls.append(users_list)
        main_column.controls.append(results_list)
        
        page.add(main_column)
        page.update()

    async def login_click(e):
        nonlocal current_user
        if login_input.value == "admin" and pass_input.value == "admin123":
            current_user = {"username": "admin", "role": "admin"}
            await load_groups_from_server()
            await show_main_screen()
            return
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post("http://192.168.31.34:8000/login", json={"username": login_input.value, "password": pass_input.value}, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        current_user = data["user"]
                        await load_groups_from_server()
                        await show_main_screen()
                    else:
                        page.snack_bar = ft.SnackBar(ft.Text(f"❌ {data.get('message', 'Ошибка входа')}"))
                        page.snack_bar.open = True
                        page.update()
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Ошибка соединения с сервером"))
                    page.snack_bar.open = True
                    page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Ошибка подключения: {str(ex)}"))
            page.snack_bar.open = True
            page.update()

    async def logout_click(e):
        nonlocal current_user
        current_user = {"username": "", "role": ""}
        page.clean()
        page.add(ft.Container(height=20), ft.Text("👤", size=80), ft.Text("Вход в систему", size=30, weight="bold"), login_input, pass_input, ft.FilledButton("🔑 ВОЙТИ", on_click=login_click, width=300, height=50))
        page.update()

    login_input = ft.TextField(label="Логин", value="admin", width=300)
    pass_input = ft.TextField(label="Пароль", value="admin123", password=True, width=300)

    page.add(ft.Container(height=20), ft.Text("👤", size=80), ft.Text("Вход в систему", size=30, weight="bold"), login_input, pass_input, ft.FilledButton("🔑 ВОЙТИ", on_click=login_click, width=300, height=50))

if __name__ == "__main__":
    ft.run(main)