"""JSON 파일을 저장소로 사용하는 범용 CRUD 리포지토리 (제네릭).

`../DataPersistence/src/persistence/json_repository.py`를 그대로 채택했다.
엔티티는 메모리에 dict(id -> entity)로 캐시되며, 변경이 있을 때마다 JSON 파일에
즉시 반영(save)되어 애플리케이션을 재시작해도 데이터가 유지된다(데이터 영속성).
"""

import json
from pathlib import Path
from typing import Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class DuplicateIdError(ValueError):
    """`create()` 호출 시 이미 존재하는 ID로 엔티티를 생성하려 할 때 발생한다.

    저장(`_save()`) 단계에서 발생하는 다른 ValueError(예: 인코딩 문제로 인한
    UnicodeEncodeError)와 구분하기 위한 전용 예외 타입이다.
    """


class JsonRepository(Generic[T]):
    def __init__(
        self,
        file_path: str,
        to_dict: Callable[[T], dict],
        from_dict: Callable[[dict], T],
        id_field: str,
    ):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._to_dict = to_dict
        self._from_dict = from_dict
        self._id_field = id_field
        self._data: Dict[str, T] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            self._data = {}
            self._save()
            return
        with open(self.file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._data = {item[self._id_field]: self._from_dict(item) for item in raw}

    def _save(self) -> None:
        raw = [self._to_dict(entity) for entity in self._data.values()]
        tmp_path = self.file_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        tmp_path.replace(self.file_path)

    def create(self, entity: T) -> T:
        entity_id = self._to_dict(entity)[self._id_field]
        if entity_id in self._data:
            raise DuplicateIdError(f"이미 존재하는 ID 입니다: {entity_id}")
        self._data[entity_id] = entity
        try:
            self._save()
        except Exception:
            # 메모리와 파일 상태가 어긋나지 않도록, 저장 실패 시 방금 넣은
            # 엔트리를 롤백한다.
            del self._data[entity_id]
            raise
        return entity

    def get(self, entity_id: str) -> Optional[T]:
        return self._data.get(entity_id)

    def get_all(self) -> List[T]:
        return list(self._data.values())

    def find(self, predicate: Callable[[T], bool]) -> List[T]:
        return [entity for entity in self._data.values() if predicate(entity)]

    def update(self, entity_id: str, entity: T) -> T:
        if entity_id not in self._data:
            raise KeyError(f"존재하지 않는 ID 입니다: {entity_id}")
        previous_entity = self._data[entity_id]
        self._data[entity_id] = entity
        try:
            self._save()
        except Exception:
            # 메모리와 파일 상태가 어긋나지 않도록, 저장 실패 시 이전 값으로
            # 롤백한다.
            self._data[entity_id] = previous_entity
            raise
        return entity

    def delete(self, entity_id: str) -> None:
        if entity_id not in self._data:
            raise KeyError(f"존재하지 않는 ID 입니다: {entity_id}")
        previous_entity = self._data.pop(entity_id)
        try:
            self._save()
        except Exception:
            # 메모리와 파일 상태가 어긋나지 않도록, 저장 실패 시 삭제를
            # 취소(복원)한다.
            self._data[entity_id] = previous_entity
            raise

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._data
