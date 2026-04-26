# -*- coding: utf-8 -*-
with open('src/gui/case_manager_dialog.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

insert_idx = None
for i, line in enumerate(lines):
    if line.strip() == 'self._update_status_bar(cases)':
        insert_idx = i + 1
        break

method = (
    '\n'
    '    def _get_filtered_cases(self) -> List[Dict]:\n'
    '        if self._search_text:\n'
    '            cases = self._cm.search_cases(self._search_text)\n'
    '        elif self._current_filter == "all":\n'
    '            cases = self._cm.get_all_cases()\n'
    '        else:\n'
    '            cases = self._cm.get_cases_by_category(self._current_filter)\n'
    '\n'
    '        if self._current_filter != "all":\n'
    '            allowed_categories = self._get_filter_categories()\n'
    '            cases = [case for case in cases if case.get("category", "") in allowed_categories]\n'
    '\n'
    '        if self._current_status != "all":\n'
    '            cases = [case for case in cases if case.get("status", "active") == self._current_status]\n'
    '\n'
    '        if self._current_directory != "all":\n'
    '            cases = [case for case in cases if case.get("folder_status", "") == self._current_directory]\n'
    '\n'
    '        if self._selected_tag:\n'
    '            cases = [case for case in cases if self._selected_tag in case.get("tags", [])]\n'
    '\n'
    '        return cases\n'
)

if insert_idx:
    lines = lines[:insert_idx] + [method] + lines[insert_idx:]
    with open('src/gui/case_manager_dialog.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('Done')
else:
    print('Insert point not found')
