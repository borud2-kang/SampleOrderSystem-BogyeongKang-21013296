"""OrderView 입력 검증(재입력 루프) 테스트. builtins.input을 monkeypatch로 시퀀스 대체."""

import builtins

import pytest

from app.model.sample import Sample
from app.persistence.sample_repository import SampleRepository
from app.view.order_view import OrderView


def _make_input_sequence(values):
    it = iter(values)

    def fake_input(prompt=""):
        return next(it)

    return fake_input


@pytest.fixture
def view():
    return OrderView()


@pytest.fixture
def sample_repo(tmp_path):
    repo = SampleRepository(str(tmp_path / "samples.json"))
    sample = Sample(
        sample_id=repo.next_id(),
        name="실리콘 웨이퍼-8인치",
        avg_process_time=0.5,
        yield_rate=0.9,
    )
    repo.create(sample)
    return repo


def test_prompt_existing_sample_id_reprompts_on_unregistered_id(monkeypatch, view, sample_repo):
    monkeypatch.setattr(
        builtins, "input", _make_input_sequence(["S-999", "S-001"])
    )
    result = view._prompt_existing_sample_id(sample_repo)
    assert result == "S-001"


def test_prompt_positive_int_reprompts_on_string_zero_negative(monkeypatch, view):
    monkeypatch.setattr(
        builtins, "input", _make_input_sequence(["abc", "0", "-5", "10"])
    )
    result = view._prompt_positive_int("주문 수량 > ")
    assert result == 10


def test_prompt_reservation_full_flow_with_reinput(monkeypatch, view, sample_repo):
    monkeypatch.setattr(
        builtins,
        "input",
        _make_input_sequence(
            ["S-999", "S-001", "", "홍길동", "abc", "0", "-3", "10"]
        ),
    )
    result = view.prompt_reservation(sample_repo)
    assert result == {
        "sample_id": "S-001",
        "customer_name": "홍길동",
        "quantity": 10,
    }
