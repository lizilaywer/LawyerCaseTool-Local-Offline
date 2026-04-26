# -*- coding: utf-8 -*-
with open('src/gui/case_manager_dialog.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = None
for i, line in enumerate(lines):
    if line.startswith('    def _load_cases(self) -> None:'):
        start_idx = i
        break

if start_idx is None:
    print('Start not found')
    exit(1)

end_idx = len(lines)
for i in range(start_idx + 1, len(lines)):
    if lines[i].startswith('    def _get_filter_categories(self)') or lines[i].startswith('    def _select_case'):
        end_idx = i
        break

new_method = (
    '    def _load_cases(self) -> None:\n'
    '        """加载案件列表，使用增量更新避免全部重建卡片。"""\n'
    '        self._refresh_tag_filters()\n'
    '        self._update_filter_summary()\n'
    '        cases = self._get_filtered_cases()\n'
    '\n'
    '        # 1. 删除旧的分组标题\n'
    '        for header in getattr(self, "_group_headers", []):\n'
    '            self._list_layout.removeWidget(header)\n'
    '            header.deleteLater()\n'
    '        self._group_headers = []\n'
    '\n'
    '        visible_ids = {case["id"] for case in cases}\n'
    '\n'
    '        # 2. 删除不再显示的卡片（而不是全部清空）\n'
    '        for cid in list(self._case_cards.keys()):\n'
    '            if cid not in visible_ids:\n'
    '                card = self._case_cards.pop(cid)\n'
    '                self._list_layout.removeWidget(card)\n'
    '                card.deleteLater()\n'
    '\n'
    '        # 3. 重建显示顺序并复用/创建卡片\n'
    '        self._case_id_order = [case["id"] for case in cases]\n'
    '        self._list_container.setUpdatesEnabled(False)\n'
    '        try:\n'
    '            insert_position = 0\n'
    '            for group_name, group_status in STATUS_GROUPS:\n'
    '                group_cases = [case for case in cases if case.get("status", "active") == group_status]\n'
    '                if not group_cases:\n'
    '                    continue\n'
    '\n'
    '                group_header = QLabel(f"  {group_name} ({len(group_cases)})")\n'
    '                group_header.setStyleSheet(f"""\n'
    '                    background: {COLORS["surface_0"]};\n'
    '                    color: {COLORS["text_secondary"]};\n'
    '                    font-size: 11px;\n'
    '                    font-weight: 600;\n'
    '                    padding: 6px 8px;\n'
    '                    border-left: 3px solid {COLORS["accent"]};\n'
    '                    border-radius: 0 6px 6px 0;\n'
    '                    margin: 4px 2px 2px 2px;\n'
    '                """)\n'
    '                self._group_headers.append(group_header)\n'
    '                self._list_layout.insertWidget(insert_position, group_header)\n'
    '                insert_position += 1\n'
    '\n'
    '                for case in group_cases:\n'
    '                    case_id = case["id"]\n'
    '                    if case_id in self._case_cards:\n'
    '                        # 复用现有卡片，刷新数据并调整位置\n'
    '                        card = self._case_cards[case_id]\n'
    '                        card.refresh(case)\n'
    '                        self._list_layout.removeWidget(card)\n'
    '                        self._list_layout.insertWidget(insert_position, card)\n'
    '                    else:\n'
    '                        card = CaseCard(case)\n'
    '                        card.selection_requested.connect(self._on_case_selection_requested)\n'
    '                        card.context_menu_requested.connect(self._on_case_context_menu)\n'
    '                        self._case_cards[case_id] = card\n'
    '                        self._list_layout.insertWidget(insert_position, card)\n'
    '                    insert_position += 1\n'
    '        finally:\n'
    '            self._list_container.setUpdatesEnabled(True)\n'
    '\n'
    '        if not cases:\n'
    '            empty = QLabel("暂无案件\\n可拖入案件文件夹，或点击上方"导入案件"添加")\n'
    '            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)\n'
    '            empty.setStyleSheet(f"""\n'
    '                background: transparent;\n'
    '                color: {COLORS["text_muted"]};\n'
    '                font-size: 13px;\n'
    '                padding: 60px 0;\n'
    '            """)\n'
    '            self._list_layout.insertWidget(0, empty)\n'
    '            self._detail_panel.clear()\n'
    '            self._selected_case_ids.clear()\n'
    '        elif self._selected_case_ids:\n'
    '            valid_selected = {cid for cid in self._selected_case_ids if cid in self._case_cards}\n'
    '            self._selected_case_ids = valid_selected\n'
    '            self._update_selection_states()\n'
    '            first_selected = next(iter(self._selected_case_ids))\n'
    '            case = self._cm.get_case(first_selected)\n'
    '            if case:\n'
    '                self._detail_panel.load_case(case)\n'
    '        else:\n'
    '            first_id = cases[0]["id"]\n'
    '            self._selected_case_ids = {first_id}\n'
    '            self._update_selection_states()\n'
    '            case = self._cm.get_case(first_id)\n'
    '            if case:\n'
    '                self._detail_panel.load_case(case)\n'
    '\n'
    '        self._update_status_bar(cases)\n'
)

lines = lines[:start_idx] + [new_method] + lines[end_idx:]
with open('src/gui/case_manager_dialog.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
