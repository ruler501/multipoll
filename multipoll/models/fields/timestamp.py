import datetime
from typing import Any, Optional, Union

from django.db import models

dt_format = "%Y-%m-%d %H:%M:%S.%f"


class TimestampField(models.CharField):
    def __init__(self, *args: Optional[Any], **kwargs: Optional[Any]):
        kwargs['max_length'] = 50
        super(TimestampField, self).__init__(*args, **kwargs)  # noqa: T484

    def db_type(self, connection: Any) -> str:
        return 'TIMESTAMP'

    def to_python(self, value: Union[str, datetime.datetime, float]) -> Optional[str]:
        if value == '':
            return None
        return f'{self.normalize_to_timestamp(value)}'

    @classmethod
    def normalize_to_timestamp(cls, value: Union[str, datetime.datetime, float]) -> Optional[str]:
        dt = cls.normalize_to_datetime(value)
        if dt is None:
            return None
        else:
            return f'{dt.timestamp():.6f}'

    @staticmethod
    def normalize_to_datetime(value: Union[str, datetime.datetime, float]) \
            -> Optional[datetime.datetime]:
        if value == '':
            return None
        elif isinstance(value, datetime.datetime):
            dt = value
        else:
            try:
                value = float(value)
                dt = datetime.datetime.utcfromtimestamp(value)
            except ValueError:
                dt = datetime.datetime.strptime(str(value), dt_format)
        return dt

    def from_db_value(self, value: Union[datetime.datetime, str, float],
                      *_: Any) -> Optional[datetime.datetime]:
        return self.normalize_to_datetime(value)

    def get_prep_value(self, value: Union[str, datetime.datetime, float]) -> Optional[str]:
        dt = self.normalize_to_datetime(value)
        if dt is None:
            return None
        return dt.strftime(dt_format)
