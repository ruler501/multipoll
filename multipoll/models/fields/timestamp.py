import datetime

from typing import Union, Any, Optional

from django.db import models


class TimestampField(models.CharField):
    def __init__(self, **kwargs: Optional[Any]):
        kwargs['max_length'] = 50
        super(TimestampField, self).__init__(**kwargs)

    def db_type(self, connection):
        return 'TIMESTAMP'

    @staticmethod
    def to_python_static(value: Union[str, datetime.datetime, float]) -> str:
        if isinstance(value, str):
            try:
                fl = float(value)
            except ValueError:
                # TODO: Investigate type checker saying fromisoformat doesn't exist.
                fl = datetime.datetime.fromisoformat(value).replace(tzinfo=datetime.timezone.utc).timestamp()
        elif isinstance(value, datetime.datetime):
            fl = value.replace(tzinfo=datetime.timezone.utc).timestamp()
        elif isinstance(value, float):
            fl = value
        else:
            raise TypeError("value was not a recognized type")
        return f'{fl:.6f}'

    def to_python(self, value):
        return self.to_python_static(value)

    @staticmethod
    def from_db_value_static(value) -> datetime.datetime:
        if isinstance(value, str):
            try:
                # noinspection SpellCheckingInspection
                fvalue = float(value)
                return datetime.datetime.utcfromtimestamp(fvalue)
            except ValueError:
                # TODO: Investigate type checker saying fromisoformat doesn't exist.
                return datetime.datetime.fromisoformat(value).replace(tzinfo=datetime.timezone.utc)
        elif isinstance(value, datetime.datetime):
            # TODO: Figure out why type checker says we're missing positional arguments for replace
            return value.replace(tzinfo=datetime.timezone.utc)
        elif isinstance(value, float):
            # TODO: Figure out why type checker says we're missing positional arguments for replace
            # noinspection PyArgumentList
            return datetime.datetime.replace(tzinfo=datetime.timezone.utc)

        raise TypeError("value was not a recognized type")

    # noinspection PyUnusedLocal
    def from_db_value(self, value, expression, connection, context):
        return self.from_db_value_static(value)

    @staticmethod
    def get_prep_value_static(value: Union[str, datetime.datetime, float]) -> str:
        if isinstance(value, datetime.datetime):
            dt = value
        else:
            try:
                dt = datetime.datetime.utcfromtimestamp(float(value))
            except ValueError:
                return value
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_prep_value(self, value: Union[str, datetime.datetime, float]) -> str:
        return self.get_prep_value_static(value)
