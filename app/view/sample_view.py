"""시료 관리 View. 입출력만 담당하고 비즈니스 로직은 포함하지 않는다."""

from app.model.sample import Sample


class SampleView:
    def show_menu(self) -> None:
        print("-" * 60)
        print(" [시료 관리]")
        print(" [1] 시료 등록  [2] 목록 조회  [3] 이름 검색")
        print(" [0] 뒤로 가기")
        print("-" * 60)

    def prompt_choice(self) -> str:
        return input("선택 > ").strip()

    def prompt_registration(self) -> dict:
        """이름/평균 생산시간/수율을 입력받는다. 형식이 잘못되면 같은 항목을 재입력받는다."""
        name = self._prompt_nonempty("시료명 > ")
        avg_time = self._prompt_positive_float("평균 생산시간(분/개) > ")
        yield_rate = self._prompt_yield_rate("수율(0 초과 1 이하) > ")
        return {"name": name, "avg_process_time": avg_time, "yield_rate": yield_rate}

    def show_registered(self, sample: Sample) -> None:
        print(
            f"[등록 완료] {sample.sample_id} / {sample.name} "
            f"(평균 생산시간 {sample.avg_process_time}, 수율 {sample.yield_rate})"
        )

    def show_duplicate_error(self, sample_id: str) -> None:
        print(f"[오류] 이미 존재하는 시료 ID 입니다: {sample_id}")

    def show_list(self, samples: list) -> None:
        if not samples:
            print("등록된 시료가 없습니다.")
            return
        print(f"{'ID':<8} {'이름':<20} {'평균생산시간':>10} {'수율':>6} {'재고':>6}")
        for sample in samples:
            print(
                f"{sample.sample_id:<8} {sample.name:<20} "
                f"{sample.avg_process_time:>10} {sample.yield_rate:>6} {sample.stock:>6}"
            )

    def prompt_search_keyword(self) -> str:
        return input("검색할 시료명(부분 일치) > ").strip()

    def show_search_result(self, samples: list) -> None:
        if not samples:
            print("검색 결과가 없습니다.")
            return
        self.show_list(samples)

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    # 내부 헬퍼: 잘못된 형식이면 오류 출력 후 같은 프롬프트 재입력
    def _prompt_nonempty(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("[오류] 값을 입력하세요.")

    def _prompt_positive_float(self, prompt: str) -> float:
        while True:
            raw = input(prompt).strip()
            try:
                value = float(raw)
            except ValueError:
                print("[오류] 숫자를 입력하세요.")
                continue
            if value <= 0:
                print("[오류] 0보다 큰 값을 입력하세요.")
                continue
            return value

    def _prompt_yield_rate(self, prompt: str) -> float:
        while True:
            raw = input(prompt).strip()
            try:
                value = float(raw)
            except ValueError:
                print("[오류] 숫자를 입력하세요.")
                continue
            if not (0 < value <= 1):
                print("[오류] 수율은 0을 초과하고 1 이하인 값이어야 합니다.")
                continue
            return value
