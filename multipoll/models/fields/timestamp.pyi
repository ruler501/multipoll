import datetime
from typing import Any, Optional, Union

from django.db import models

dt_format: str


class TimestampField(models.CharField[Union[str, float, datetime.datetime], str]):
    def db_type(self, _: Any) -> str:
        ...

    def to_python(self, value: Union[str, datetime.datetime, float]) -> Optional[str]:
        ...

    @classmethod
    def normalize_to_timestamp(cls, value: Union[str, datetime.datetime, float]) \
            -> Optional[str]:
        ...

    @staticmethod
    def normalize_to_datetime(value: Union[str, datetime.datetime, float]) \
            -> Optional[datetime.datetime]:
        ...

    def from_db_value(self, value: Union[datetime.datetime, str, float], *_: Any) \
            -> datetime.datetime:
        ...

    def get_prep_value(self, value: Union[str, datetime.datetime, float]) -> Optional[str]:
        ...