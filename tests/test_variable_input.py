# -*- coding: utf-8 -*-
"""变量输入性能回归测试"""

from src.gui.widgets.variable_input import VariablesForm


class TestVariablesForm:
    """变量表单批量更新测试。"""

    def test_set_values_and_clear_all_emit_once(self, qapp):
        form = VariablesForm()
        form.set_variables([
            {"key": "case_number", "label": "案号", "type": "text"},
            {"key": "client_name", "label": "当事人", "type": "text"},
        ])

        emitted = []
        form.values_changed.connect(lambda values: emitted.append(dict(values)))

        form.set_values({
            "case_number": "（2026）皖1702民初1号",
            "client_name": "张三",
        })

        assert len(emitted) == 1
        assert emitted[-1]["case_number"] == "（2026）皖1702民初1号"
        assert emitted[-1]["client_name"] == "张三"

        form.clear_all()

        assert len(emitted) == 2
        assert emitted[-1] == {}
