from app.physical_tables.navigator import PhysicalTablesNavigator


class AdminFilterLayoutMixin:
    def _build_ui(self) -> None:
        super()._build_ui()
        self._install_physical_tables_navigator()
        self._remove_inline_relation_map()
        self.add_relation_btn.setText('➕ Создать через карту')
        self.open_relation_map_btn.setText('🗺 Карта всех связей')
        self.relation_top.setSizes([510, 900])
        self.main_splitter.setSizes([330, 1250])
        self.main_splitter.setCollapsible(0, False)

    def _install_physical_tables_navigator(self) -> None:
        for widget in (
            self.refresh_btn,
            self.check_schema_btn,
            self.save_tables_btn,
            self.add_table_btn,
            self.delete_table_btn,
            self.table_filter_label,
            self.table_filter,
            self.tables_grid,
        ):
            widget.hide()
        navigator = PhysicalTablesNavigator(self.left_panel)
        self.left_layout.addWidget(navigator, 1)
        self.physical_tables_navigator = navigator
        self.table_filter = navigator.filter_edit
        self.tables_filter_panel = navigator.filter_edit.parentWidget()
        self.tables_filter_count_label = navigator.count_label
        navigator.tableSelected.connect(lambda *_: self._on_selected_table_changed())
        navigator.editRequested.connect(self.open_physical_tables_editor)
        navigator.refreshRequested.connect(self.reload_all)
        navigator.checkRequested.connect(self.check_admin_tables)
        navigator.fieldsRequested.connect(lambda: self.right_tabs.setCurrentWidget(self.fields_tab))
        navigator.relationsRequested.connect(lambda: self.right_tabs.setCurrentWidget(self.relations_tab))
        navigator.mapRequested.connect(self.open_relation_map)

    def _remove_inline_relation_map(self) -> None:
        self.relation_map_layout.removeWidget(self.open_relation_map_btn)
        self.open_relation_map_btn.setParent(self.relation_list_box)
        self.relation_list_toolbar.addWidget(self.open_relation_map_btn)
        self.relation_map_panel.hide()
        self.canvas_hint_label.hide()
        # self.canvas_container.hide()

    def _apply_table_filter(self) -> None:
        if hasattr(self, 'physical_tables_navigator'):
            self.physical_tables_navigator._rebuild()

    def _populate_physical_tables(self, rows) -> None:
        self.physical_tables_navigator.set_rows(rows)

    def current_table_key(self) -> str:
        return self.physical_tables_navigator.current_key

    def _select_table_key(self, table_key: str) -> None:
        self.physical_tables_navigator.select_key(table_key)

    def _select_first_table(self) -> str:
        return self.physical_tables_navigator.select_first(enabled_only=True)

    def _fallback_table_key(self, previous_key: str) -> str:
        return self.physical_tables_navigator.nearest_enabled_key(previous_key)
