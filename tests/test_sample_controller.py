"""SampleController 단위 테스트. SampleView를 테스트 더블로 대체해 stdin 시뮬레이션 없이 검증한다."""

import pytest

from app.controller.sample_controller import SampleController
from app.persistence.sample_repository import SampleRepository


class FakeSampleView:
    """SampleView 대신 사용하는 테스트 더블. 미리 지정된 값을 반환하고 호출을 기록한다."""

    def __init__(self, registration=None, search_keyword=None):
        self._registration = registration
        self._search_keyword = search_keyword
        self.registered = None
        self.duplicate_error_id = None
        self.listed_samples = None
        self.search_results = None

    def prompt_registration(self):
        return self._registration

    def show_registered(self, sample):
        self.registered = sample

    def show_duplicate_error(self, sample_id):
        self.duplicate_error_id = sample_id

    def show_list(self, samples):
        self.listed_samples = samples

    def prompt_search_keyword(self):
        return self._search_keyword

    def show_search_result(self, samples):
        self.search_results = samples

    def show_error(self, message):
        pass


@pytest.fixture
def sample_file_path(tmp_path):
    return str(tmp_path / "samples.json")


@pytest.fixture
def repo(sample_file_path):
    return SampleRepository(sample_file_path)


def test_register_uses_next_id_and_saves(repo):
    view = FakeSampleView(
        registration={"name": "실리콘 웨이퍼-8인치", "avg_process_time": 0.5, "yield_rate": 0.9}
    )
    controller = SampleController(repo, view)

    controller._register()

    assert view.registered is not None
    assert view.registered.sample_id == "S-001"
    assert view.registered.name == "실리콘 웨이퍼-8인치"
    saved = repo.get("S-001")
    assert saved is not None
    assert saved.name == "실리콘 웨이퍼-8인치"
    assert saved.avg_process_time == 0.5
    assert saved.yield_rate == 0.9


def test_register_multiple_ids_do_not_collide(repo):
    view1 = FakeSampleView(registration={"name": "A", "avg_process_time": 1, "yield_rate": 1})
    view2 = FakeSampleView(registration={"name": "B", "avg_process_time": 2, "yield_rate": 0.5})
    controller = SampleController(repo, view1)
    controller._register()
    controller = SampleController(repo, view2)
    controller._register()

    ids = {s.sample_id for s in repo.get_all()}
    assert ids == {"S-001", "S-002"}


def test_register_allows_duplicate_name(repo):
    view1 = FakeSampleView(registration={"name": "동일이름", "avg_process_time": 1, "yield_rate": 0.9})
    view2 = FakeSampleView(registration={"name": "동일이름", "avg_process_time": 2, "yield_rate": 0.8})
    controller = SampleController(repo, view1)
    controller._register()
    controller = SampleController(repo, view2)
    controller._register()

    names = [s.name for s in repo.get_all()]
    assert names == ["동일이름", "동일이름"]
    assert view1.duplicate_error_id is None
    assert view2.duplicate_error_id is None
    assert len(repo.get_all()) == 2


def test_list_includes_stock_field(repo):
    view = FakeSampleView(
        registration={"name": "실리콘 웨이퍼-8인치", "avg_process_time": 0.5, "yield_rate": 0.9}
    )
    controller = SampleController(repo, view)
    controller._register()

    controller._list()

    assert view.listed_samples is not None
    assert len(view.listed_samples) == 1
    assert hasattr(view.listed_samples[0], "stock")
    assert view.listed_samples[0].stock == 0


def test_search_returns_partial_match_only(repo):
    view = FakeSampleView(
        registration={"name": "실리콘 웨이퍼-8인치", "avg_process_time": 0.5, "yield_rate": 0.9}
    )
    controller = SampleController(repo, view)
    controller._register()

    view2 = FakeSampleView(
        registration={"name": "GaN 에피텍셜-4인치", "avg_process_time": 0.3, "yield_rate": 0.78}
    )
    controller2 = SampleController(repo, view2)
    controller2._register()

    search_view = FakeSampleView(search_keyword="웨이퍼")
    search_controller = SampleController(repo, search_view)
    search_controller._search()

    assert len(search_view.search_results) == 1
    assert search_view.search_results[0].name == "실리콘 웨이퍼-8인치"


def test_search_no_match_returns_empty_list(repo):
    view = FakeSampleView(
        registration={"name": "실리콘 웨이퍼-8인치", "avg_process_time": 0.5, "yield_rate": 0.9}
    )
    controller = SampleController(repo, view)
    controller._register()

    search_view = FakeSampleView(search_keyword="존재하지않음")
    search_controller = SampleController(repo, search_view)
    search_controller._search()

    assert search_view.search_results == []
