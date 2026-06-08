from seeder import (
    DEFAULT_HARMONISASI_FORM_CODE,
    build_harmonisasi_demo_payload,
    load_harmonisasi_rows,
)


def test_load_harmonisasi_rows_reads_workbook_fixture():
    rows = load_harmonisasi_rows()

    assert len(rows) == 104
    assert rows[0]['TanggalISO'] == '2026-01-29'
    assert rows[0]['Daerah'] == 'Kabupaten Indramayu'
    assert rows[-1]['TanggalISO'] == '2026-04-28'


def test_build_harmonisasi_demo_payload_contains_expected_summary_and_seed_specs():
    payload = build_harmonisasi_demo_payload()

    assert payload['summary']['row_count'] == 104
    assert payload['summary']['date_min'] == '2026-01-29'
    assert payload['summary']['date_max'] == '2026-04-28'
    assert payload['summary']['completion']['selesai'] == 89
    assert payload['summary']['completion']['dikembalikan'] == 15
    assert payload['summary']['top_daerah'][0] == {'label': 'Kota Banjar', 'count': 9}
    assert payload['summary']['filter_dimensions']['reporting_years'] == [2026]
    assert payload['summary']['period_metrics']['quarterly'][0] == {
        'label': '2026-Q1',
        'period_type': 'quarterly',
        'period_number': 1,
        'reporting_year': 2026,
        'total': 61,
        'selesai': 49,
        'dikembalikan': 12,
        'achievement_percentage': 80.33,
    }
    assert payload['summary']['period_metrics']['semesterly'][0] == {
        'label': '2026-S1',
        'period_type': 'semesterly',
        'period_number': 1,
        'reporting_year': 2026,
        'total': 104,
        'selesai': 89,
        'dikembalikan': 15,
        'achievement_percentage': 85.58,
    }
    assert payload['summary']['row_snapshots'][0]['quarter_label'] == '2026-Q1'
    assert payload['summary']['row_snapshots'][0]['semester_label'] == '2026-S1'

    assert payload['form']['code'] == DEFAULT_HARMONISASI_FORM_CODE
    assert payload['dataset']['dataset_key'] == 'analytics-demo-harmonisasi-submission-fact'
    assert payload['indicator']['indicator_code'] == 'ANL-HARM-01'
    assert payload['indicator_result']['measured_value'] == 85.58
    assert len(payload['submissions']) == 104
    assert payload['submissions'][0]['context']['source_ref'] == 'harmonisasi:2'
