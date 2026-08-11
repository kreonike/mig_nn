import sqlite3
import flet as ft


def main(page: ft.Page):
    page.title = "Учет клиентов — Flet"
    page.window_width = 900
    page.window_height = 600
    page.padding = 20

    search_input = ft.TextField(
        label="Поиск по фамилии",
        width=300,
        on_change=lambda e: search_clients(e.control.value),
    )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("Фамилия")),
            ft.DataColumn(ft.Text("Имя")),
            ft.DataColumn(ft.Text("Отчество")),
            ft.DataColumn(ft.Text("Дата рождения")),
        ],
        rows=[],
    )

    def search_clients(query):
        table.rows.clear()
        if len(query) < 2:
            page.update()
            return

        conn = sqlite3.connect("mig_database.db")
        cursor = conn.cursor()
        # Лимитируем 50 записями для быстродействия UI
        cursor.execute(
            """
            SELECT id, Фамилия, Имя, Отчество, ДатаРождения 
            FROM Клиенты 
            WHERE Фамилия LIKE ? 
            LIMIT 50
        """,
            (f"{query}%",),
        )

        for row in cursor.fetchall():
            table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(row[0]))),
                        ft.DataCell(ft.Text(str(row[1] or ""))),
                        ft.DataCell(ft.Text(str(row[2] or ""))),
                        ft.DataCell(ft.Text(str(row[3] or ""))),
                        ft.DataCell(ft.Text(str(row[4] or ""))),
                    ]
                )
            )
        conn.close()
        page.update()

    page.add(
        ft.Row([search_input], alignment=ft.MainAxisAlignment.START),
        ft.ListView([table], expand=True),
    )


ft.app(target=main)