"""Bootstrap catalog for resource-scoped access policies.

Catatan:
- Ini belum evaluator ABAC penuh.
- File ini adalah kamus policy + matrix awal agar domain 2-3 punya acuan stabil.
- Saat domain 1 dan 4 matang, definisi ini bisa dipindah ke registry DB / policy engine.
"""

ORG_SCOPE_TYPES = (
    'global',
    'kanwil',
    'division',
    'unit',
    'upt',
)

BOOTSTRAP_SCOPE_REGISTRY = {
    'kanwil-jabar': {
        'type': 'kanwil',
        'code': 'kanwil-jabar',
        'name': 'Kantor Wilayah Kementerian Hukum Jawa Barat',
        'path': ['kanwil-jabar'],
    },
    'divisi-pelayanan-hukum': {
        'type': 'division',
        'code': 'divisi-pelayanan-hukum',
        'name': 'Divisi Pelayanan Hukum',
        'path': ['kanwil-jabar', 'divisi-pelayanan-hukum'],
        'parent_code': 'kanwil-jabar',
    },
    'divisi-p3h': {
        'type': 'division',
        'code': 'divisi-p3h',
        'name': 'Divisi P3H',
        'path': ['kanwil-jabar', 'divisi-p3h'],
        'parent_code': 'kanwil-jabar',
    },
    'bagian-umum-tata-usaha': {
        'type': 'division',
        'code': 'bagian-umum-tata-usaha',
        'name': 'Bagian Umum dan Tata Usaha',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha'],
        'parent_code': 'kanwil-jabar',
    },
    'ki': {
        'type': 'unit',
        'code': 'ki',
        'name': 'Kekayaan Intelektual',
        'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ki'],
        'parent_code': 'divisi-pelayanan-hukum',
    },
    'ahu': {
        'type': 'unit',
        'code': 'ahu',
        'name': 'Administrasi Hukum Umum',
        'path': ['kanwil-jabar', 'divisi-pelayanan-hukum', 'ahu'],
        'parent_code': 'divisi-pelayanan-hukum',
    },
    'perancang-ppu': {
        'type': 'unit',
        'code': 'perancang-ppu',
        'name': 'Perancang Peraturan Perundang-undangan',
        'path': ['kanwil-jabar', 'divisi-p3h', 'perancang-ppu'],
        'parent_code': 'divisi-p3h',
    },
    'jdih': {
        'type': 'unit',
        'code': 'jdih',
        'name': 'Jaringan Dokumentasi dan Informasi Hukum',
        'path': ['kanwil-jabar', 'divisi-p3h', 'jdih'],
        'parent_code': 'divisi-p3h',
    },
    'penyuluh-hukum': {
        'type': 'unit',
        'code': 'penyuluh-hukum',
        'name': 'Penyuluh Hukum',
        'path': ['kanwil-jabar', 'divisi-p3h', 'penyuluh-hukum'],
        'parent_code': 'divisi-p3h',
    },
    'bsk': {
        'type': 'unit',
        'code': 'bsk',
        'name': 'Badan Strategi Kebijakan',
        'path': ['kanwil-jabar', 'divisi-p3h', 'bsk'],
        'parent_code': 'divisi-p3h',
    },
    'kepegawaian': {
        'type': 'unit',
        'code': 'kepegawaian',
        'name': 'Kepegawaian',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'kepegawaian'],
        'parent_code': 'bagian-umum-tata-usaha',
    },
    'keuangan': {
        'type': 'unit',
        'code': 'keuangan',
        'name': 'Keuangan',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'keuangan'],
        'parent_code': 'bagian-umum-tata-usaha',
    },
    'program-pelaporan': {
        'type': 'unit',
        'code': 'program-pelaporan',
        'name': 'Program dan Pelaporan',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'program-pelaporan'],
        'parent_code': 'bagian-umum-tata-usaha',
    },
    'humas': {
        'type': 'unit',
        'code': 'humas',
        'name': 'Hubungan Masyarakat',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'humas'],
        'parent_code': 'bagian-umum-tata-usaha',
    },
    'teknologi-informasi': {
        'type': 'unit',
        'code': 'teknologi-informasi',
        'name': 'Teknologi Informasi',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'teknologi-informasi'],
        'parent_code': 'bagian-umum-tata-usaha',
    },
    'rumah-tangga': {
        'type': 'unit',
        'code': 'rumah-tangga',
        'name': 'Rumah Tangga',
        'path': ['kanwil-jabar', 'bagian-umum-tata-usaha', 'rumah-tangga'],
        'parent_code': 'bagian-umum-tata-usaha',
    },
}

ACCESS_POLICY_CATALOG = {
    'form.admin_only_authoring': {
        'resource': 'form',
        'description': 'Draft/create/update/publish hanya oleh admin lintas bagian atau superadmin.',
        'default_owner_scope_type': 'unit',
        'default_target_scope_type': 'unit',
        'actions': ['form:create', 'form:update', 'form:publish', 'form:archive'],
    },
    'form.unit_internal': {
        'resource': 'form',
        'description': 'Form dimiliki satu unit dan hanya dikonsumsi unit yang sama.',
        'default_owner_scope_type': 'unit',
        'default_target_scope_type': 'unit',
        'actions': ['form:view', 'submission:create', 'submission:view'],
    },
    'form.division_broadcast': {
        'resource': 'form',
        'description': 'Form dibuat admin untuk dikonsumsi seluruh unit pada satu divisi.',
        'default_owner_scope_type': 'unit',
        'default_target_scope_type': 'division',
        'actions': ['form:view', 'submission:create', 'submission:view'],
    },
    'form.kanwil_broadcast': {
        'resource': 'form',
        'description': 'Form untuk seluruh unit kerja di bawah kanwil.',
        'default_owner_scope_type': 'unit',
        'default_target_scope_type': 'kanwil',
        'actions': ['form:view', 'submission:create', 'submission:view'],
    },
    'form.upt_network': {
        'resource': 'form',
        'description': 'Form untuk jaringan UPT tertentu di bawah kanwil.',
        'default_owner_scope_type': 'unit',
        'default_target_scope_type': 'upt',
        'actions': ['form:view', 'submission:create', 'submission:view'],
    },
    'submission.unit_owned': {
        'resource': 'submission',
        'description': 'Submission dimiliki unit pengelola / unit yang diwakili data.',
        'owner_scope_source': 'submission.owner_scope_*',
        'actions': ['submission:view', 'submission:detail'],
    },
    'submission.division_audit': {
        'resource': 'submission',
        'description': 'Submission dapat dibaca kepala divisi untuk seluruh scope divisinya.',
        'owner_scope_source': 'submission.owner_scope_*',
        'actions': ['submission:view', 'submission:detail', 'submission:export'],
    },
    'submission.kanwil_audit': {
        'resource': 'submission',
        'description': 'Submission dapat dibaca auditor/program-pelaporan/kakanwil lintas kanwil.',
        'owner_scope_source': 'submission.owner_scope_*',
        'actions': ['submission:view', 'submission:detail', 'submission:export'],
    },
    'submission.superadmin_full': {
        'resource': 'submission',
        'description': 'Full access untuk superadmin.',
        'owner_scope_source': 'submission.owner_scope_*',
        'actions': ['submission:view', 'submission:detail', 'submission:update', 'submission:export'],
    },
}

POLICY_MATRIX = {
    'superadmin': {
        'scope': 'global',
        'allowed_actions': ['*'],
        'recommended_policies': ['submission.superadmin_full'],
    },
    'admin_lintas_bagian': {
        'scope': 'kanwil',
        'allowed_actions': [
            'form:create',
            'form:update',
            'form:publish',
            'form:archive',
            'form:view',
            'submission:view',
            'submission:detail',
            'submission:export',
        ],
        'recommended_policies': [
            'form.admin_only_authoring',
            'form.division_broadcast',
            'form.kanwil_broadcast',
            'submission.kanwil_audit',
        ],
    },
    'auditor_program_pelaporan': {
        'scope': 'kanwil',
        'allowed_actions': [
            'form:view',
            'submission:view',
            'submission:detail',
            'submission:export',
        ],
        'recommended_policies': ['submission.kanwil_audit'],
    },
    'kakanwil': {
        'scope': 'kanwil',
        'allowed_actions': [
            'form:view',
            'submission:view',
            'submission:detail',
            'submission:export',
        ],
        'recommended_policies': ['submission.kanwil_audit'],
    },
    'kepala_divisi': {
        'scope': 'division',
        'allowed_actions': [
            'form:view',
            'submission:view',
            'submission:detail',
            'submission:export',
        ],
        'recommended_policies': ['submission.division_audit'],
    },
    'pegawai_unit': {
        'scope': 'unit',
        'allowed_actions': [
            'form:view',
            'submission:create',
            'submission:view',
            'submission:detail',
        ],
        'recommended_policies': [
            'form.unit_internal',
            'form.division_broadcast',
            'form.kanwil_broadcast',
            'submission.unit_owned',
        ],
    },
    'operator_upt': {
        'scope': 'upt',
        'allowed_actions': [
            'form:view',
            'submission:create',
            'submission:view',
            'submission:detail',
        ],
        'recommended_policies': [
            'form.upt_network',
            'submission.unit_owned',
        ],
    },
}
