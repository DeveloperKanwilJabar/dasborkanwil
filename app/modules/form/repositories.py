"""Repository domain form.

Modul ini membungkus query SQLAlchemy untuk pencarian form, pengecekan identitas unik, dan pengelolaan version form."""

from app.core.extensions import db
from app.core.repositories.base import BaseRepository

from .models import Form, FormVersion


class FormRepository(BaseRepository):
    """Repository query untuk entity Form.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = FormRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = FormRepository()
        """

        super().__init__(model=Form)

    def exists_code(self, code, exclude_form_id=None):
        """Mengecek apakah kode form sudah dipakai form lain.

        Args:
            code (Any): Business code unik entity target.
            exclude_form_id (Any): Primary key form yang harus dikecualikan saat cek unik.

        Returns:
            bool: Hasil evaluasi atau status sukses operasi.

        Example:
            >>> repo.exists_code(code=..., exclude_form_id=...)
        """

        query = self.model.query.filter(Form.code == code)
        if exclude_form_id is not None:
            query = query.filter(Form.id != exclude_form_id)
        return db.session.query(query.exists()).scalar()

    def exists_slug(self, slug, exclude_form_id=None):
        """Mengecek apakah slug form sudah dipakai form lain.

        Args:
            slug (Any): Business slug unik entity target.
            exclude_form_id (Any): Primary key form yang harus dikecualikan saat cek unik.

        Returns:
            bool: Hasil evaluasi atau status sukses operasi.

        Example:
            >>> repo.exists_slug(slug=..., exclude_form_id=...)
        """

        query = self.model.query.filter(Form.slug == slug)
        if exclude_form_id is not None:
            query = query.filter(Form.id != exclude_form_id)
        return db.session.query(query.exists()).scalar()

    def get_by_slug(self, slug):
        """Mengambil registry berdasarkan slug bisnis unik.

        Args:
            slug (Any): Business slug unik entity target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_by_slug(slug=...)
        """

        return self.find_one_by(slug=slug)

    def get_active_by_slug(self, slug):
        """Mengambil registry aktif berdasarkan slug unik.

        Args:
            slug (Any): Business slug unik entity target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_active_by_slug(slug=...)
        """

        return self.model.query.filter(
            Form.slug == slug,
            Form.status.in_(['draft', 'published']),
            Form.deleted_at == None,
        ).first()

    def list_by_status(self, status):
        """Mengambil daftar entity berdasarkan status bisnisnya.

        Args:
            status (Any): Status bisnis yang dipakai untuk filtering data.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_by_status(status=...)
        """

        return self.find_by(status=status)


class FormVersionRepository(BaseRepository):
    """Repository query untuk entity FormVersion.

    Class ini membungkus query SQLAlchemy yang sering dipakai service
    agar logika akses data tetap terpusat dan konsisten.

    Example:
        >>> obj = FormVersionRepository()
    """

    def __init__(self):
        """Inisialisasi object dan dependency dasar yang dibutuhkan class ini.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo = FormVersionRepository()
        """

        super().__init__(model=FormVersion)

    def get_latest_version(self, form_id):
        """Mengambil versi terbaru berdasarkan nomor versi tertinggi.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_latest_version(form_id=...)
        """

        return self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.deleted_at == None,
        ).order_by(FormVersion.version_number.desc()).first()

    def get_next_version_number(self, form_id):
        """Menghitung nomor versi berikutnya untuk entity versioned.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_next_version_number(form_id=...)
        """

        latest_version = self.get_latest_version(form_id)
        if not latest_version:
            return 1
        return latest_version.version_number + 1

    def get_published_version(self, form_id):
        """Mengambil version published aktif untuk entity induk tertentu.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_published_version(form_id=...)
        """

        return self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.is_published == True,
            FormVersion.status == 'published',
            FormVersion.deleted_at == None,
        ).order_by(FormVersion.version_number.desc()).first()

    def get_draft_version(self, form_id):
        """Mengambil draft version aktif untuk entity induk tertentu.

        Args:
            form_id (Any): Primary key internal form target.

        Returns:
            Any | None: Satu object hasil query atau None bila tidak ditemukan.

        Example:
            >>> repo.get_draft_version(form_id=...)
        """

        return self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.status == 'draft',
            FormVersion.is_published == False,
            FormVersion.deleted_at == None,
        ).order_by(FormVersion.version_number.desc()).first()

    def list_versions(self, form_id, include_deleted=False):
        """Mengambil seluruh versi entity tertentu secara terurut terbaru ke lama.

        Args:
            form_id (Any): Primary key internal form target.
            include_deleted (Any): Jika True, record soft delete tetap disertakan dalam hasil query.

        Returns:
            list[Any]: Daftar object hasil query atau hasil operasi bulk.

        Example:
            >>> repo.list_versions(form_id=..., include_deleted=...)
        """

        query = self.model.query.filter(FormVersion.form_id == form_id)
        if not include_deleted:
            query = query.filter(FormVersion.deleted_at == None)
        return query.order_by(FormVersion.version_number.desc()).all()

    def unpublish_others(self, form_id, except_version_id=None):
        """Menonaktifkan flag published pada version lain dalam parent yang sama.

        Args:
            form_id (Any): Primary key internal form target.
            except_version_id (Any): Primary key version yang tidak ikut diubah saat update massal.

        Returns:
            Any: Nilai hasil operasi repository/model.

        Example:
            >>> repo.unpublish_others(form_id=..., except_version_id=...)
        """

        query = self.model.query.filter(
            FormVersion.form_id == form_id,
            FormVersion.is_published == True,
        )
        if except_version_id is not None:
            query = query.filter(FormVersion.id != except_version_id)

        versions = query.all()
        for version in versions:
            version.is_published = False
            if version.status == 'published':
                version.status = 'archived'
        return versions
