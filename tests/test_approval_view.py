"""ApprovalView 입력 검증(재입력 루프) 테스트. builtins.input을 monkeypatch로 시퀀스 대체."""

import builtins

import pytest

from app.view.approval_view import ApprovalView


def _make_input_sequence(values):
    it = iter(values)

    def fake_input(prompt=""):
        return next(it)

    return fake_input


@pytest.fixture
def view():
    return ApprovalView()


def test_prompt_decision_reprompts_on_invalid_input(monkeypatch, view):
    monkeypatch.setattr(
        builtins, "input", _make_input_sequence(["x", "yes", "", "Y"])
    )
    result = view.prompt_decision()
    assert result == "Y"


def test_prompt_decision_accepts_lowercase_y_and_n(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["y"]))
    assert view.prompt_decision() == "Y"

    monkeypatch.setattr(builtins, "input", _make_input_sequence(["n"]))
    assert view.prompt_decision() == "N"


def test_prompt_order_id_strips_whitespace(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["  ORD-0001  "]))
    assert view.prompt_order_id() == "ORD-0001"
