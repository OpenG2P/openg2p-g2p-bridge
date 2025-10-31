from typing import Optional

from .bridge_schemas import SyncResponse

class AccountStatementResponse(SyncResponse):
    statement_id: Optional[str] = None
    response_error_code: Optional[str] = None
