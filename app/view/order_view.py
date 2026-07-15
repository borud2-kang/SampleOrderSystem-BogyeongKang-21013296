"""시료 주문(예약) View. 입출력만 담당하고 비즈니스 로직은 포함하지 않는다."""

from app.model.order import Order
from app.persistence.sample_repository import SampleRepository


class OrderView:
    def prompt_reservation(self, sample_repo: SampleRepository) -> dict:
        sample_id = self._prompt_existing_sample_id(sample_repo)
        customer_name = self._prompt_nonempty("고객명 > ")
        quantity = self._prompt_positive_int("주문 수량 > ")
        return {"sample_id": sample_id, "customer_name": customer_name, "quantity": quantity}

    def show_reserved(self, order: Order) -> None:
        print(
            f"[주문 접수 완료] {order.order_id} / 시료 {order.sample_id} / "
            f"고객 {order.customer_name} / 수량 {order.quantity} / 상태 {order.status.value}"
        )

    def show_error(self, message: str) -> None:
        print(f"[오류] {message}")

    # 내부 헬퍼: 잘못된 형식/미등록 ID면 오류 출력 후 같은 프롬프트 재입력
    def _prompt_existing_sample_id(self, sample_repo: SampleRepository) -> str:
        while True:
            sample_id = input("시료 ID > ").strip()
            if sample_repo.get(sample_id) is None:
                print("[오류] 존재하지 않는 시료 ID 입니다.")
                continue
            return sample_id

    def _prompt_nonempty(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("[오류] 값을 입력하세요.")

    def _prompt_positive_int(self, prompt: str) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                value = int(raw)
            except ValueError:
                print("[오류] 숫자를 입력하세요.")
                continue
            if value <= 0:
                print("[오류] 1 이상의 수량을 입력하세요.")
                continue
            return value
