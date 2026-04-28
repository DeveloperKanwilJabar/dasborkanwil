from app.core.extensions import db
from app.core.repositories.base import BaseRepository
from .models import Employee

class EmployeeRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=Employee)
