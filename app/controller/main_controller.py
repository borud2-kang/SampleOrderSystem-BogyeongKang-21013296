"""메인 메뉴 Controller. 메뉴 루프를 돌며 각 하위 Controller로 흐름을 위임한다."""

from app.model.order import OrderStatus
from app.persistence.order_repository import OrderRepository
from app.persistence.production_queue import ProductionQueue
from app.persistence.sample_repository import SampleRepository
from app.view.main_view import MainView
from app.view.sample_view import SampleView

from app.controller.approval_controller import ApprovalController
from app.controller.monitoring_controller import MonitoringController
from app.controller.order_controller import OrderController
from app.controller.production_controller import ProductionController
from app.controller.sample_controller import SampleController
from app.controller.shipment_controller import ShipmentController


class MainController:
    def __init__(self) -> None:
        self._sample_repo = SampleRepository()
        self._order_repo = OrderRepository()
        self._production_queue = ProductionQueue()

        self._view = MainView()
        self._sample_view = SampleView()

        self._sample_controller = SampleController(self._sample_repo, self._sample_view)
        self._order_controller = OrderController(self._order_repo, self._sample_repo)
        self._approval_controller = ApprovalController(
            self._order_repo, self._sample_repo, self._production_queue
        )
        self._monitoring_controller = MonitoringController(self._order_repo, self._sample_repo)
        self._production_controller = ProductionController(
            self._production_queue, self._order_repo, self._sample_repo
        )
        self._shipment_controller = ShipmentController(self._order_repo, self._sample_repo)

    def run(self) -> None:
        while True:
            self._view.show_menu(self._summary())
            choice = self._view.prompt_choice()

            if choice == "1":
                self._sample_controller.run()
            elif choice == "2":
                self._order_controller.run()
            elif choice == "3":
                self._approval_controller.run()
            elif choice == "4":
                self._monitoring_controller.run()
            elif choice == "5":
                self._production_controller.run()
            elif choice == "6":
                self._shipment_controller.run()
            elif choice == "0":
                self._view.show_message("시스템을 종료합니다.")
                return
            else:
                self._view.show_error("알 수 없는 선택입니다. 메뉴에 표시된 번호를 입력하세요.")

    def _summary(self) -> dict:
        samples = self._sample_repo.get_all()
        orders = self._order_repo.get_all()
        return {
            "sample_count": len(samples),
            "total_stock": sum(s.stock for s in samples),
            "order_count": len(orders),
            "producing_count": len(
                [o for o in orders if o.status == OrderStatus.PRODUCING]
            ),
        }
