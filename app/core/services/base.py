"""Fondasi service layer generik.

`BaseService` dipakai sebagai kelas dasar ringan untuk service yang hanya perlu
membungkus repository atau menyediakan helper umum lintas domain. Kelas ini
sengaja tipis agar logic bisnis tetap tinggal di service turunan masing-masing.
"""

import pandas as pd


class BaseService:
    """Blueprint minimal untuk service domain.

    Attributes:
        repository (Any | None): Repository yang menjadi pasangan service ini.

    Example:
        >>> service = BaseService(repository=my_repository)
        >>> rows = service.get_all()
    """

    def __init__(self, repository=None):
        """Simpan dependency repository pada instance service.

        Args:
            repository (Any, optional): Objek repository yang menyediakan akses
                data untuk service ini.

        Returns:
            None

        Example:
            >>> service = BaseService(repository=user_repository)
            >>> service.repository is user_repository
            True
        """
        self.repository = repository

    def get_all(self):
        """Ambil seluruh data dari repository pasangan service.

        Method ini berguna untuk service sederhana yang belum memerlukan
        filtering/transformasi tambahan sebelum data dikembalikan.

        Returns:
            Any: Hasil pemanggilan `repository.get_all()`.

        Example:
            >>> service.get_all()
            [<User ...>, <User ...>]
        """
        return self.repository.get_all()

    def to_dataframe(self, query_result):
        """Ubah koleksi model yang punya `to_dict()` menjadi DataFrame pandas.

        Helper ini berguna untuk kebutuhan analytics, export, atau eksplorasi
        data ketika hasil query SQLAlchemy ingin diproses lebih lanjut dengan
        pandas.

        Args:
            query_result (Iterable[Any]): Koleksi object model yang menyediakan
                method `to_dict()`.

        Returns:
            pandas.DataFrame: DataFrame hasil konversi object domain.

        Example:
            >>> dataframe = service.to_dataframe(query_result)
            >>> list(dataframe.columns)
            ['id', 'uuid', 'created_at']
        """
        return pd.DataFrame([row.to_dict() for row in query_result])
