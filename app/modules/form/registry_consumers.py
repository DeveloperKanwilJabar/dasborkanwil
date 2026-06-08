"""Consumer preset registry untuk Form.io builder.

Service ini menyediakan preset komponen builder yang bisa langsung dipakai UI
agar pola select berantai dari data registry tidak perlu dirakit manual setiap
kali membuat form baru.
"""


class FormRegistryConsumerService:
    """Penyedia preset komponen registry untuk form builder.

    Saat ini fokus utamanya adalah preset cascading select wilayah administratif
    yang mengonsumsi published registry resource dari backend.

    Example:
        >>> service = FormRegistryConsumerService()
        >>> presets = service.list_builder_presets(base_url='https://example.com')
        >>> presets[0]['key']
        'wilayah_cascading_select'
    """

    DEFAULT_WILAYAH_REGISTRY_SLUG = 'wilayah.administratif'

    def list_builder_presets(self, base_url=None):
        """Daftar seluruh preset builder yang tersedia.

        Args:
            base_url (str | None, optional): Base URL backend untuk membangun
                endpoint data source komponen.

        Returns:
            list[dict]: Daftar preset builder siap render di UI.

        Example:
            >>> service.list_builder_presets()[0]['label']
            'Cascading Select Wilayah'
        """
        return [self.get_builder_preset('wilayah_cascading_select', base_url=base_url)]

    def get_builder_preset(self, preset_key, base_url=None):
        """Ambil definisi satu preset builder berdasarkan key.

        Args:
            preset_key (str): Key preset yang ingin diambil.
            base_url (str | None, optional): Base URL backend untuk endpoint
                options source.

        Returns:
            dict: Definisi preset builder Form.io.

        Raises:
            ValueError: Jika `preset_key` tidak dikenali.

        Example:
            >>> service.get_builder_preset('wilayah_cascading_select')['registry_slug']
            'wilayah.administratif'
        """
        if preset_key != 'wilayah_cascading_select':
            raise ValueError('Preset consumer registry tidak ditemukan.')

        registry_slug = self.DEFAULT_WILAYAH_REGISTRY_SLUG
        return {
            'key': 'wilayah_cascading_select',
            'label': 'Cascading Select Wilayah',
            'description': 'Tambah 4 select berantai provinsi -> kabupaten/kota -> kecamatan -> kelurahan/desa dari published registry wilayah.',
            'registry_slug': registry_slug,
            'components': [
                self._build_select_component(
                    key='province_code',
                    label='Provinsi',
                    admin_level='province',
                    registry_slug=registry_slug,
                    base_url=base_url,
                ),
                self._build_select_component(
                    key='city_regency_code',
                    label='Kabupaten/Kota',
                    admin_level='city_regency',
                    registry_slug=registry_slug,
                    parent_key='province_code',
                    base_url=base_url,
                ),
                self._build_select_component(
                    key='district_code',
                    label='Kecamatan',
                    admin_level='district',
                    registry_slug=registry_slug,
                    parent_key='city_regency_code',
                    base_url=base_url,
                ),
                self._build_select_component(
                    key='village_code',
                    label='Kelurahan/Desa',
                    admin_level='village',
                    registry_slug=registry_slug,
                    parent_key='district_code',
                    base_url=base_url,
                ),
            ],
        }

    def _normalize_base_url(self, base_url):
        if not base_url:
            return ''
        return str(base_url).rstrip('/')

    def _build_registry_options_url(self, registry_slug, admin_level, parent_key=None, base_url=None):
        normalized_base_url = self._normalize_base_url(base_url)
        query = f'{normalized_base_url}/api/v1/registry-resources/{registry_slug}/options?admin_level={admin_level}'
        if not normalized_base_url:
            query = f'/api/v1/registry-resources/{registry_slug}/options?admin_level={admin_level}'
        if parent_key:
            query = f'{query}&parent_code={{{{ data.{parent_key} }}}}'
        return query

    def _build_select_component(self, key, label, admin_level, registry_slug, parent_key=None, base_url=None):
        query = self._build_registry_options_url(
            registry_slug=registry_slug,
            admin_level=admin_level,
            parent_key=parent_key,
            base_url=base_url,
        )

        component = {
            'label': label,
            'widget': 'choicesjs',
            'tableView': True,
            'dataSrc': 'url',
            'data': {
                'url': query,
                'headers': [],
                'json': '',
                'values': [],
                'resource': '',
                'custom': '',
            },
            'valueProperty': 'value',
            'selectValues': 'data.items',
            'template': '<span>{{ item.label }}</span>',
            'lazyLoad': True,
            'filter': '',
            'searchEnabled': True,
            'searchField': 'q',
            'limit': 100,
            'validate': {
                'required': False,
            },
            'key': key,
            'type': 'select',
            'input': True,
            'clearOnHide': False,
            'allowCalculateOverride': False,
            'registryConsumer': {
                'registry_slug': registry_slug,
                'admin_level': admin_level,
                'parent_key': parent_key,
            },
        }
        if parent_key:
            component['refreshOn'] = parent_key
            component['clearOnRefresh'] = True
            component['disabled'] = False
        return component
