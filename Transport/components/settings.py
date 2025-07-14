import flet as ft

class LeftNavigationMenu(ft.Column):
    def __init__(self,ref:ft.Ref|None,visible=True):
        super().__init__()

        self.dark_light_text = ft.Text("Световая тема")
        self.dark_light_icon = ft.IconButton(
            icon=ft.Icons.BRIGHTNESS_2_OUTLINED,
            tooltip="Выбрать тему",
            on_click=self.theme_changed,
        )

        self.controls = [

            ft.Column(
                expand=1,
                controls=[
                    ft.Row(
                        controls=[
                            self.dark_light_icon,
                            self.dark_light_text,
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.PopupMenuButton(
                                icon=ft.Icons.COLOR_LENS_OUTLINED,
                                items=[
                                    PopupColorItem(color="deeppurple", name="Тёмно-фиолетовый"),
                                    PopupColorItem(color="indigo", name="Индиго"),
                                    PopupColorItem(color="blue", name="Синий (по умолчанию)"),
                                    PopupColorItem(color="teal", name="Бирюзовый"),
                                    PopupColorItem(color="green", name="Зелёный"),
                                    PopupColorItem(color="yellow", name="Жёлтый"),
                                    PopupColorItem(color="orange", name="Оранжевый"),
                                    PopupColorItem(color="deeporange", name="Тёмно-оранжевый"),
                                    PopupColorItem(color="pink", name="Розовый"),
                                ],
                            ),
                            ft.Text("Цветовая тема"),
                        ]
                    ),
                ],ref=ref,visible=visible,

            ),
        ]

    def theme_changed(self, e):
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.dark_light_text.value = "Темная тема"
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_HIGH
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.dark_light_text.value = "Светлая тема"
            self.dark_light_icon.icon = ft.Icons.BRIGHTNESS_2
        self.page.data.Data_user.update_theme_mode(self.page.theme_mode)
        self.page.update()

class PopupColorItem(ft.PopupMenuItem):
    def __init__(self, color, name):
        super().__init__()
        self.content = ft.Row(
            controls=[
                ft.Icon(name=ft.Icons.COLOR_LENS_OUTLINED, color=color),
                ft.Text(name),
            ],
        )
        self.on_click = self.seed_color_changed
        self.data = color

    def seed_color_changed(self, e):
        self.page.theme = self.page.dark_theme = ft.Theme(color_scheme_seed=self.data)
        self.page.data.Data_user.update_theme_color(self.page.theme.color_scheme_seed)
        self.page.update()