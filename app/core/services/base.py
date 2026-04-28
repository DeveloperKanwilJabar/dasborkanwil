import pandas as pd
from datetime import datetime

class BaseService:
    """Blueprint untuk semua service di dalam modul."""

    def __init__(self, repository=None):
        self.repository = repository

    def get_all(self):
        """Method generik untuk ambil semua data dari repository."""
        return self.repository.query.all()

    def to_dataframe(self, query_result):
        """Helper global untuk mengubah hasil query SQLAlchemy ke Dataframe."""
        # data = [{k: v for k, v in item.__dict__.items() if k != '_sa_instance_state'} for item in query_result]
        return pd.DataFrame([r.to_dict() for r in query_result])
