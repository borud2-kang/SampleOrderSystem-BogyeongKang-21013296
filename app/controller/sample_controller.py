"""시료 관리 Controller. 등록/목록 조회/이름 검색 하위 메뉴를 처리한다."""

from app.model.sample import Sample
from app.persistence.json_repository import DuplicateIdError
from app.persistence.sample_repository import SampleRepository
from app.view.sample_view import SampleView


class SampleController:
    def __init__(self, sample_repo: SampleRepository, view: SampleView) -> None:
        self._sample_repo = sample_repo
        self._view = view

    def run(self) -> None:
        while True:
            self._view.show_menu()
            choice = self._view.prompt_choice()
            if choice == "1":
                self._register()
            elif choice == "2":
                self._list()
            elif choice == "3":
                self._search()
            elif choice == "0":
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")

    def _register(self) -> None:
        data = self._view.prompt_registration()
        sample = Sample(
            sample_id=self._sample_repo.next_id(),
            name=data["name"],
            avg_process_time=data["avg_process_time"],
            yield_rate=data["yield_rate"],
        )
        try:
            self._sample_repo.create(sample)
        except DuplicateIdError:
            self._view.show_duplicate_error(sample.sample_id)
            return
        self._view.show_registered(sample)

    def _list(self) -> None:
        samples = self._sample_repo.get_all()
        self._view.show_list(samples)

    def _search(self) -> None:
        keyword = self._view.prompt_search_keyword()
        samples = self._sample_repo.find(lambda sample: keyword in sample.name)
        self._view.show_search_result(samples)
