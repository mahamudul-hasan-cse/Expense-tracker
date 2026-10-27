from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

# Validated money input: positive, max 2 decimals, fits NUMERIC(12, 2)
MoneyIn = Annotated[Decimal, Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)]

# Money output: serialized as a JSON number instead of Pydantic's default string
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
