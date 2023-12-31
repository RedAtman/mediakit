
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, validator


class StateKeyEnum(IntEnum):
    running = 1
    finished = 2


class State(BaseModel):
    compress: Optional[StateKeyEnum] = Field(None, description="Error messages if any")
    trim: Optional[StateKeyEnum] = Field(None, description="Error messages if any")

    class Config:
        from_attributes = True

    def __getitem__(self, key):
        return self.__dict__.get(key)

    # @validator('compress')


if __name__ == '__main__':
    print(State.model_fields.keys())
    print('compress' in State.model_fields.keys())
