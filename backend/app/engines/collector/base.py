import abc
from typing import List
from app.schemas.clue import ClueItem
from app.schemas.constraint import BusinessConstraint

class BaseCollectorStrategy(abc.ABC):
    """数据采集策略基类"""
    @abc.abstractmethod
    async def collect(self, constraint: BusinessConstraint, **kwargs) -> List[ClueItem]:
        pass
