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

    assert payload['form']['code'] == DEFAULT_HARMONISASI_FORM_CODE
    assert payload['dataset']['dataset_key'] == 'analytics-demo-harmonisasi-submission-fact'
    assert payload['indicator']['indicator_code'] == 'ANL-HARM-01'
    assert payload['indicator_result']['measured_value'] == 85.58
    assert len(payload['submissions']) == 104
    assert payload['submissions'][0]['context']['source_ref'] == 'harmonisasi:2'
