"""SampleView 입력 검증(재입력 루프) 테스트. builtins.input을 monkeypatch로 시퀀스 대체."""

import builtins

import pytest

from app.view.sample_view import SampleView


def _make_input_sequence(values):
    it = iter(values)

    def fake_input(prompt=""):
        return next(it)

    return fake_input


@pytest.fixture
def view():
    return SampleView()


def test_prompt_nonempty_reprompts_on_blank(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["", "   ", "실리콘 웨이퍼"]))
    result = view._prompt_nonempty("시료명 > ")
    assert result == "실리콘 웨이퍼"


def test_prompt_positive_float_reprompts_on_non_numeric(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["abc", "0.5"]))
    result = view._prompt_positive_float("평균 생산시간 > ")
    assert result == 0.5


def test_prompt_positive_float_reprompts_on_non_positive(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["0", "-1", "2.5"]))
    result = view._prompt_positive_float("평균 생산시간 > ")
    assert result == 2.5


def test_prompt_yield_rate_reprompts_on_non_numeric(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["xyz", "0.9"]))
    result = view._prompt_yield_rate("수율 > ")
    assert result == 0.9


def test_prompt_yield_rate_reprompts_on_zero(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["0", "0.5"]))
    result = view._prompt_yield_rate("수율 > ")
    assert result == 0.5


def test_prompt_yield_rate_reprompts_on_out_of_range(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["1.5", "-0.3", "1"]))
    result = view._prompt_yield_rate("수율 > ")
    assert result == 1.0


def test_prompt_yield_rate_accepts_exact_one(monkeypatch, view):
    monkeypatch.setattr(builtins, "input", _make_input_sequence(["1"]))
    result = view._prompt_yield_rate("수율 > ")
    assert result == 1.0


def test_prompt_registration_full_flow_with_reinput(monkeypatch, view):
    # 시료명: 공백 -> 정상, 평균생산시간: 문자열 -> 정상, 수율: 0 -> 문자열 -> 정상
    monkeypatch.setattr(
        builtins,
        "input",
        _make_input_sequence(["", "실리콘 웨이퍼-8인치", "notanumber", "0.5", "0", "bad", "0.9"]),
    )
    result = view.prompt_registration()
    assert result == {
        "name": "실리콘 웨이퍼-8인치",
        "avg_process_time": 0.5,
        "yield_rate": 0.9,
    }
