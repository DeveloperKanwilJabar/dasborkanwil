from app.core.extensions import db
from app.core.repositories.base import BaseRepository
from .models import User

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(model=User)

    def exists_username(self, username, exclude_user_id=None):
        query = self.model.query.filter(User.username == username)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return db.session.query(query.exists()).scalar()

    def exists_email(self, email, exclude_user_id=None):
        query = self.model.query.filter(User.email == email)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return db.session.query(query.exists()).scalar()

    def exists(self, username, email):
        '''Cek apakah username atau email sudah terdaftar di tabel User.'''
        # cara lama:
        # return self.model.query.filter(
        #     (self.model.username == username) | (self.model.email == email)
        # ).first() is not None
        # Gunakan .exists() untuk performa query yang lebih cepat daripada .first()
        return db.session.query(self.model.query.filter(
            (User.username == username) | (User.email == email)
        ).exists()).scalar()
