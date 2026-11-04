from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt


class Expectation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["gold", "hp", "keys", "potions", "won", "dead", "doors_open"]
    value: StrictInt | StrictBool | list[str]


class TestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    requirement_ids: list[str] = Field(min_length=1, max_length=3)
    fixture: Literal["spawn", "door_no_key", "door_with_key", "shop_no_gold", "shop_with_gold"]
    actions: list[Literal["up", "down", "left", "right", "use_potion", "buy_potion", "wait"]] = Field(min_length=1, max_length=20)
    expected: list[Expectation] = Field(min_length=1, max_length=8)


class CaseBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cases: list[TestCase] = Field(min_length=1, max_length=27)
