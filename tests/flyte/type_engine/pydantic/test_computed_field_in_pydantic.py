import msgpack
import pytest
from pydantic import BaseModel, ConfigDict, computed_field

import flyte.types._type_engine as type_engine
from flyte.types import TypeEngine


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_days: int = 30

    @computed_field
    @property
    def n_weeks(self) -> int:
        return self.n_days // 7


class Wrapper(BaseModel):
    model_config = ConfigDict(extra="forbid")

    params: Params
    label: str = "x"

    @computed_field
    @property
    def tag(self) -> str:
        return f"{self.label}-{self.params.n_weeks}"


@pytest.mark.asyncio
async def test_computed_field_with_extra_forbid_roundtrip():
    lt = TypeEngine.to_literal_type(Params)
    lv = await TypeEngine.to_literal(Params(n_days=15), Params, lt)

    assert msgpack.loads(lv.scalar.binary.value) == {"n_days": 15}

    pv = await TypeEngine.to_python_value(lv, Params)
    assert pv == Params(n_days=15)
    assert pv.n_weeks == 2


@pytest.mark.asyncio
async def test_nested_computed_fields_with_extra_forbid_roundtrip():
    if not type_engine._PYDANTIC_HAS_EXCLUDE_COMPUTED_FIELDS:
        pytest.skip("nested computed fields are only excluded on pydantic >= 2.12")

    value = Wrapper(params=Params(n_days=21), label="run")
    lt = TypeEngine.to_literal_type(Wrapper)
    lv = await TypeEngine.to_literal(value, Wrapper, lt)

    assert msgpack.loads(lv.scalar.binary.value) == {"params": {"n_days": 21}, "label": "run"}

    pv = await TypeEngine.to_python_value(lv, Wrapper)
    assert pv == value
    assert pv.tag == "run-3"


@pytest.mark.asyncio
async def test_computed_field_excluded_without_exclude_computed_fields(monkeypatch):
    monkeypatch.setattr(type_engine, "_PYDANTIC_HAS_EXCLUDE_COMPUTED_FIELDS", False)

    lt = TypeEngine.to_literal_type(Params)
    lv = await TypeEngine.to_literal(Params(n_days=15), Params, lt)

    assert msgpack.loads(lv.scalar.binary.value) == {"n_days": 15}
    assert await TypeEngine.to_python_value(lv, Params) == Params(n_days=15)
