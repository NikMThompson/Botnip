from __future__ import annotations

import logging
from typing import Any, Dict, Generator, Optional

import pydantic
from pydantic import validator

from meta import MetaModel
from multi import MultiModel
from ttime import TimePeriod

from plots import plot_models_range_interactive


class Base(pydantic.BaseModel):
    class Config:
        extra = 'forbid'


class IslandModel(Base):
    timeline: Dict[TimePeriod, Optional[int]]

    @validator('timeline', pre=True)
    def normalize(cls, value: Any) -> Any:
        if isinstance(value, Dict):
            return {
                TimePeriod.normalize(key): price
                for key, price in value.items()
            }
        return value

    @property
    def base_price(self) -> Optional[int]:
        return self.timeline.get(TimePeriod.Sunday_AM, None)


class ArchipelagoModel(Base):
    islands: Dict[str, IslandModel]


class Island:
    def __init__(self, name: str, data: IslandModel):
        self._name = name
        self._data = data
        self._models: Optional[MultiModel] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def base_price(self) -> int:
        return self._data.base_price

    @property
    def model_group(self) -> MultiModel:
        if self._models is None:
            self.process()
            assert self._models is not None
        return self._models

    def process(self) -> None:
        logging.info(f" == {self.name} island == ")

        base = self._data.base_price
        self._models = MetaModel.blank(base)

        logging.info(f"  (%d models)  ", len(self._models))

        for time, price in self._data.timeline.items():
            if price is None:
                continue
            if time.value < TimePeriod.Monday_AM.value:
                continue
            logging.info(f"[{time.name}]: fixing price @ {price}")
            self._models.fix_price(time, price)

    def plot(self):
        return plot_models_range_interactive(
            self.name,
            list(self.model_group.models)
        )

    @property
    def data(self):
        return self._data


class Archipelago:
    def __init__(self, data: ArchipelagoModel):
        self._data = data
        self._islands = {name: Island(name, idata) for name, idata
                         in self._data.islands.items()}

    @classmethod
    def load_file(cls, filename: str) -> Archipelago:
        return cls(ArchipelagoModel.parse_file(filename))

    @property
    def groups(self) -> Generator[MultiModel, None, None]:
        for island in self._islands.values():
            yield island.model_group

    @property
    def islands(self) -> Generator[Island, None, None]:
        for island in self._islands.values():
            yield island

    def summary(self) -> None:
        for island in self.islands:
            print(f"{island.name}")
            print('-' * len(island.model_group))
            print('')
            island.model_group.report()
            print('')

        archipelago = MetaModel(-1, self.groups)
        archipelago.summary()
        print('-' * 80)

    def plot(self) -> None:
        for island in self.islands:
            plot_models_range_interactive(island.name,
                                          island.data.base_price,
                                          list(island.model_group.models)
                                          )
