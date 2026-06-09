(function () {
    const config = window.analyticsWorkspaceConfig || {};
    const reportConfig = window.analyticsReportConfig || {};
    const Plotly = window.Plotly;
    const L = window.L;

    const datasetSelect = document.getElementById('analyticsDetailDatasetSelect');
    const datasetRunsList = document.getElementById('analyticsDatasetRunsList');
    const datasetDetailSummary = document.getElementById('analyticsDatasetDetailSummary');
    const datasetMetricCards = document.getElementById('analyticsDatasetMetricCards');
    const datasetFilterReportingYear = document.getElementById('analyticsDatasetFilterReportingYear');
    const datasetFilterStatus = document.getElementById('analyticsDatasetFilterStatus');
    const datasetFilterJenis = document.getElementById('analyticsDatasetFilterJenis');
    const datasetFilterDateStart = document.getElementById('analyticsDatasetFilterDateStart');
    const datasetFilterDateEnd = document.getElementById('analyticsDatasetFilterDateEnd');
    const datasetMetricPeriodMode = document.getElementById('analyticsDatasetMetricPeriodMode');
    const datasetQuickRanges = document.getElementById('analyticsDatasetQuickRanges');
    const chartContainer = document.getElementById('analyticsDatasetChart');
    const detailTableContainer = document.getElementById('analyticsDatasetDetailTable');
    const narrativeContainer = document.getElementById('analyticsDatasetNarrative');
    const mapContainer = document.getElementById('analyticsDatasetMap');
    const mapSummary = document.getElementById('analyticsDatasetMapSummary');
    const datasetRunButton = document.getElementById('analyticsDatasetRunButton');
    const datasetRunsRefreshButton = document.getElementById('analyticsDatasetRunsRefreshButton');
    const datasetExecutionStatus = document.getElementById('analyticsDatasetExecutionStatus');
    const datasetExecutionSource = document.getElementById('analyticsDatasetExecutionSource');

    const state = {
        datasets: [],
        selectedDatasetId: config.initialDatasetId || null,
        currentDatasetDetail: null,
        currentDatasetRuns: [],
        chartRendered: false,
        map: null,
        mapLayer: null,
        filters: {
            reportingYear: '',
            status: '',
            jenis: '',
            dateStart: '',
            dateEnd: '',
            metricPeriodMode: reportConfig.default_period_mode || 'quarterly',
        },
    };

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function formatNumber(value, digits = 0) {
        const numeric = Number(value);
        if (Number.isNaN(numeric)) {
            return value ?? '-';
        }
        return new Intl.NumberFormat('id-ID', {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits,
        }).format(numeric);
    }

    function formatPercent(value) {
        const numeric = Number(value);
        if (Number.isNaN(numeric)) {
            return '-';
        }
        return `${formatNumber(numeric, 2)}%`;
    }

    function formatDateTime(value) {
        if (!value) {
            return '-';
        }
        return String(value).replace('T', ' ').replace('+00:00', ' UTC');
    }

    function fetchJson(url) {
        return fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        }).then(async function (response) {
            const payload = await response.json();
            if (!response.ok || payload.success === false) {
                throw new Error(payload.message || 'Request gagal.');
            }
            return payload.data || {};
        });
    }

    function postJson(url, body) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(body || {}),
        }).then(async function (response) {
            const payload = await response.json();
            if (!response.ok || payload.success === false) {
                throw new Error(payload.message || 'Request gagal.');
            }
            return payload.data || {};
        });
    }

    function replaceTemplate(urlTemplate, placeholder, value) {
        return String(urlTemplate || '').replace(placeholder, String(value));
    }

    function datasetMatchesRegistry(item) {
        const allowedIds = Array.isArray(config.allowedDatasetIds) ? config.allowedDatasetIds.map((value) => String(value)) : [];
        if (!allowedIds.length) {
            return true;
        }
        return allowedIds.includes(String(item && item.dataset && item.dataset.id));
    }

    function resolveRowDate(row) {
        const rawValue = row && row.tanggal ? String(row.tanggal) : '';
        if (!rawValue) {
            return null;
        }
        const parsed = new Date(`${rawValue}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    function padNumber(value) {
        return String(value).padStart(2, '0');
    }

    function formatDateInputValue(date) {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
            return '';
        }
        return `${date.getFullYear()}-${padNumber(date.getMonth() + 1)}-${padNumber(date.getDate())}`;
    }

    function getCalendarPresetRange(presetKey) {
        const today = new Date();
        const start = new Date(today);
        const end = new Date(today);

        if (presetKey === 'full_range') {
            return { start: '', end: '' };
        }
        if (presetKey === 'last_7_days') {
            start.setDate(today.getDate() - 6);
        } else if (presetKey === 'last_30_days') {
            start.setDate(today.getDate() - 29);
        } else if (presetKey === 'last_90_days') {
            start.setDate(today.getDate() - 89);
        } else if (presetKey === 'current_week') {
            const day = today.getDay();
            const diffToMonday = day === 0 ? -6 : 1 - day;
            start.setDate(today.getDate() + diffToMonday);
        } else if (presetKey === 'current_month') {
            start.setDate(1);
        } else if (presetKey === 'current_quarter') {
            start.setMonth(Math.floor(today.getMonth() / 3) * 3, 1);
        } else if (presetKey === 'current_semester') {
            start.setMonth(today.getMonth() < 6 ? 0 : 6, 1);
        } else if (presetKey === 'current_year') {
            start.setMonth(0, 1);
        } else {
            return { start: '', end: '' };
        }

        return {
            start: formatDateInputValue(start),
            end: formatDateInputValue(end),
        };
    }

    function collectFilterOptions(summaryJson) {
        const dimensions = (summaryJson && summaryJson.filter_dimensions) || {};
        return {
            reportingYears: Array.isArray(dimensions.reporting_years) ? dimensions.reporting_years : [],
            statuses: Array.isArray(dimensions.hasil_options) ? dimensions.hasil_options : [],
            jenisOptions: Array.isArray(dimensions.jenis_options) ? dimensions.jenis_options : [],
        };
    }

    function populateSelectOptions(selectEl, options, selectedValue, emptyLabel) {
        if (!selectEl) {
            return;
        }
        const currentValue = selectedValue ?? '';
        const optionHtml = [`<option value="">${escapeHtml(emptyLabel)}</option>`].concat(
            options.map(function (option) {
                const normalized = String(option ?? '');
                const selectedAttr = normalized === String(currentValue) ? ' selected' : '';
                return `<option value="${escapeHtml(normalized)}"${selectedAttr}>${escapeHtml(normalized)}</option>`;
            })
        );
        selectEl.innerHTML = optionHtml.join('');
    }

    function buildMetricCard(label, value, helper, toneClass) {
        return `
            <div class="col-md-6 col-xl-3">
                <div class="card border h-100 analytics-metric-card">
                    <div class="card-body">
                        <div class="text-muted small mb-2">${escapeHtml(label)}</div>
                        <div class="display-6 ${escapeHtml(toneClass || '')}">${escapeHtml(value)}</div>
                        <div class="text-muted fs-12 mt-2">${escapeHtml(helper || '')}</div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderMetricCards(rows, summaryJson) {
        if (!datasetMetricCards) {
            return;
        }
        const total = rows.length;
        const selesai = rows.filter((row) => String(row.hasil || '').toLowerCase() === 'selesai').length;
        const dikembalikan = rows.filter((row) => String(row.hasil || '').toLowerCase() === 'dikembalikan').length;
        const achievement = total ? (selesai / total) * 100 : 0;
        const yearSummary = state.filters.reportingYear || ((summaryJson && summaryJson.filter_dimensions && summaryJson.filter_dimensions.reporting_years || []).join(', ') || 'Semua tahun');

        datasetMetricCards.innerHTML = [
            buildMetricCard('Total Data', formatNumber(total), `Snapshot aktif untuk ${yearSummary}.`, ''),
            buildMetricCard('Selesai', formatNumber(selesai), 'Jumlah status selesai setelah filter diterapkan.', 'text-success'),
            buildMetricCard('Dikembalikan', formatNumber(dikembalikan), 'Jumlah status dikembalikan setelah filter diterapkan.', 'text-danger'),
            buildMetricCard('Achievement', formatPercent(achievement), 'Persentase selesai dari total data aktif.', 'text-primary'),
        ].join('');
    }

    function renderDatasetSummary(dataset, activeVersion, latestRun, filteredRows) {
        if (!datasetDetailSummary) {
            return;
        }
        if (!dataset) {
            datasetDetailSummary.innerHTML = '<div class="text-muted">Pilih dataset untuk melihat ringkasan.</div>';
            return;
        }
        datasetDetailSummary.innerHTML = `
            <div class="d-flex flex-column gap-3">
                <div>
                    <div class="fw-semibold">${escapeHtml(dataset.name || '-')}</div>
                    <div class="text-muted fs-12"><code>${escapeHtml(dataset.dataset_key || '-')}</code></div>
                </div>
                <div class="table-responsive">
                    <table class="table table-sm align-middle mb-0">
                        <tbody>
                            <tr><th class="text-muted">Source</th><td>${escapeHtml(dataset.source_domain || '-')} / ${escapeHtml(dataset.source_type || '-')}</td></tr>
                            <tr><th class="text-muted">Ref</th><td>${escapeHtml(dataset.primary_source_ref || '-')}</td></tr>
                            <tr><th class="text-muted">Versi Aktif</th><td>${activeVersion ? `v${escapeHtml(activeVersion.version_number)}` : '-'}</td></tr>
                            <tr><th class="text-muted">Run Terbaru</th><td>${latestRun ? escapeHtml(runStatusLabel(latestRun.status || '-')) : '-'}</td></tr>
                            <tr><th class="text-muted">Updated</th><td>${latestRun ? escapeHtml(formatDateTime(latestRun.updated_at)) : '-'}</td></tr>
                            <tr><th class="text-muted">Baris Aktif</th><td>${escapeHtml(formatNumber(filteredRows.length))}</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="alert alert-light border mb-0">${escapeHtml(dataset.description || 'Belum ada deskripsi dataset.')}</div>
            </div>
        `;
    }

    function renderDetailTable(rows) {
        if (!detailTableContainer) {
            return;
        }
        if (!rows.length) {
            detailTableContainer.innerHTML = '<div class="alert alert-light border mb-0">Belum ada baris yang cocok dengan filter aktif.</div>';
            return;
        }

        const previewRows = rows.slice(0, 8);
        detailTableContainer.innerHTML = `
            <table class="table table-sm align-middle mb-0">
                <thead>
                    <tr>
                        <th>Tanggal</th>
                        <th>Daerah</th>
                        <th>Jenis</th>
                        <th>Status</th>
                        <th>Tahun</th>
                    </tr>
                </thead>
                <tbody>
                    ${previewRows.map(function (row) {
                        return `
                            <tr>
                                <td>${escapeHtml(row.tanggal || '-')}</td>
                                <td>${escapeHtml(row.daerah || row.label || row.record_label || '-')}</td>
                                <td>${escapeHtml(row.jenis || '-')}</td>
                                <td>${escapeHtml(row.hasil || '-')}</td>
                                <td>${escapeHtml(row.reporting_year || '-')}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
            <div class="text-muted fs-12 mt-3">Menampilkan ${escapeHtml(formatNumber(previewRows.length))} dari ${escapeHtml(formatNumber(rows.length))} baris aktif.</div>
        `;
    }

    function renderNarrative(rows, summaryJson) {
        if (!narrativeContainer) {
            return;
        }
        const total = rows.length;
        const selesai = rows.filter((row) => String(row.hasil || '').toLowerCase() === 'selesai').length;
        const dikembalikan = rows.filter((row) => String(row.hasil || '').toLowerCase() === 'dikembalikan').length;
        const achievement = total ? (selesai / total) * 100 : 0;
        const activeYear = state.filters.reportingYear || ((summaryJson && summaryJson.filter_dimensions && summaryJson.filter_dimensions.reporting_years || []).join(', ') || 'semua tahun');
        const activeMode = state.filters.metricPeriodMode || reportConfig.default_period_mode || 'quarterly';
        const intro = reportConfig.meta_description || 'Narasi report belum dikurasi di builder.';
        const rangeText = state.filters.dateStart || state.filters.dateEnd
            ? `${state.filters.dateStart || 'awal data'} s.d. ${state.filters.dateEnd || 'akhir data'}`
            : 'seluruh rentang data aktif';

        narrativeContainer.innerHTML = `
            <div class="alert alert-warning-subtle border border-warning-subtle mb-0">${escapeHtml(intro)}</div>
            <div>
                <div class="fw-semibold mb-1">Ringkasan Otomatis Viewer</div>
                <p class="mb-0 text-muted">Pada mode ${escapeHtml(activeMode)}, viewer membaca ${escapeHtml(formatNumber(total))} baris untuk ${escapeHtml(activeYear)} dengan ${escapeHtml(formatNumber(selesai))} status selesai dan ${escapeHtml(formatNumber(dikembalikan))} status dikembalikan. Achievement saat ini berada di ${escapeHtml(formatPercent(achievement))} untuk rentang ${escapeHtml(rangeText)}.</p>
            </div>
        `;
    }

    function runStatusLabel(status) {
        if (status === 'succeeded') {
            return 'Berhasil';
        }
        if (status === 'failed') {
            return 'Gagal';
        }
        if (status === 'running') {
            return 'Sedang Berjalan';
        }
        return status || '-';
    }

    function renderExecutionBridge(detail, latestRun) {
        if (!datasetExecutionSource || !datasetExecutionStatus) {
            return;
        }
        const dataset = (detail && detail.dataset) || {};
        const activeVersion = (detail && (detail.published_version || detail.draft_version)) || {};
        const sourceContract = activeVersion.source_contract_json || {};
        const requestedYear = state.filters.reportingYear || sourceContract.reporting_year || '-';
        const formRefs = []
            .concat(sourceContract.form_codes || [])
            .concat(sourceContract.form_slugs || [])
            .concat(sourceContract.form_ids || [])
            .concat(sourceContract.form_code || [])
            .concat(sourceContract.form_slug || [])
            .concat(sourceContract.form_id || [])
            .filter(Boolean);

        datasetExecutionSource.innerHTML = `
            <div class="d-flex flex-column gap-2">
                <div>
                    <div class="fw-semibold">${escapeHtml(dataset.name || '-')}</div>
                    <div class="text-muted fs-12"><code>${escapeHtml(dataset.dataset_key || '-')}</code></div>
                </div>
                <div class="small text-muted">Dataset version aktif: ${activeVersion ? `v${escapeHtml(activeVersion.version_number)}` : '-'}</div>
                <div class="small text-muted">Source type: ${escapeHtml(dataset.source_domain || '-')} / ${escapeHtml(dataset.source_type || '-')}</div>
                <div class="small text-muted">Form ref: ${escapeHtml(formRefs.join(', ') || dataset.primary_source_ref || '-')}</div>
                <div class="small text-muted">Reporting year run: ${escapeHtml(requestedYear)}</div>
            </div>
        `;

        const latestStatus = latestRun ? runStatusLabel(latestRun.status) : 'Belum pernah dijalankan';
        const latestRows = latestRun ? formatNumber(latestRun.result_row_count || 0) : '0';
        const alertClass = latestRun && latestRun.status === 'succeeded'
            ? 'alert alert-success mb-0'
            : latestRun && latestRun.status === 'failed'
                ? 'alert alert-danger mb-0'
                : 'alert alert-light border mb-0';
        datasetExecutionStatus.className = alertClass;
        datasetExecutionStatus.innerHTML = `Status terakhir: <strong>${escapeHtml(latestStatus)}</strong><br />Rows materialized: <strong>${escapeHtml(latestRows)}</strong>`;

        if (datasetRunButton) {
            datasetRunButton.disabled = !(dataset && dataset.id && activeVersion && activeVersion.id);
            datasetRunButton.textContent = latestRun && latestRun.status === 'running' ? 'Run Sedang Berjalan' : 'Jalankan Dataset Sekarang';
        }
    }

    function renderRunsList(runs) {
        if (!datasetRunsList) {
            return;
        }
        if (!runs || !runs.length) {
            datasetRunsList.innerHTML = '<div class="text-muted">Belum ada dataset run untuk ditampilkan.</div>';
            return;
        }
        datasetRunsList.innerHTML = runs.map(function (run) {
            const badgeClass = run.status === 'succeeded'
                ? 'bg-success-subtle text-success'
                : run.status === 'failed'
                    ? 'bg-danger-subtle text-danger'
                    : run.status === 'running'
                        ? 'bg-warning-subtle text-warning'
                        : 'bg-secondary-subtle text-secondary';
            return `
                <div class="list-group-item px-0">
                    <div class="d-flex justify-content-between gap-2 align-items-start">
                        <div>
                            <div class="fw-semibold">${escapeHtml(run.run_key || `run-${run.id}`)}</div>
                            <div class="text-muted fs-12">${escapeHtml(run.trigger_type || '-')} · ${escapeHtml(formatDateTime(run.updated_at))}</div>
                        </div>
                        <span class="badge ${badgeClass}">${escapeHtml(run.status || '-')}</span>
                    </div>
                    <div class="text-muted fs-12 mt-2">Rows: ${escapeHtml(formatNumber(run.result_row_count || 0))}</div>
                    <div class="text-muted fs-12">Tahun: ${escapeHtml(run.requested_reporting_year || '-')}</div>
                </div>
            `;
        }).join('');
    }

    function aggregateRows(rows, periodMode) {
        const bucketMap = new Map();
        rows.forEach(function (row) {
            const date = resolveRowDate(row);
            if (!date) {
                return;
            }
            let label = row.tanggal || '-';
            if (periodMode === 'weekly') {
                const weekStart = new Date(date);
                const day = weekStart.getDay();
                const diffToMonday = day === 0 ? -6 : 1 - day;
                weekStart.setDate(weekStart.getDate() + diffToMonday);
                label = `Minggu ${formatDateInputValue(weekStart)}`;
            } else if (periodMode === 'monthly') {
                label = `${date.getFullYear()}-${padNumber(date.getMonth() + 1)}`;
            } else if (periodMode === 'quarterly') {
                label = row.quarter_label || `${date.getFullYear()}-Q${Math.floor(date.getMonth() / 3) + 1}`;
            } else if (periodMode === 'four_monthly') {
                label = `${date.getFullYear()}-C${Math.floor(date.getMonth() / 4) + 1}`;
            } else if (periodMode === 'semesterly') {
                label = row.semester_label || `${date.getFullYear()}-S${date.getMonth() < 6 ? 1 : 2}`;
            } else if (periodMode === 'yearly') {
                label = String(date.getFullYear());
            }

            const current = bucketMap.get(label) || { label, total: 0, selesai: 0, dikembalikan: 0, sortValue: date.getTime() };
            current.total += 1;
            if (String(row.hasil || '').toLowerCase() === 'selesai') {
                current.selesai += 1;
            }
            if (String(row.hasil || '').toLowerCase() === 'dikembalikan') {
                current.dikembalikan += 1;
            }
            current.sortValue = Math.min(current.sortValue, date.getTime());
            bucketMap.set(label, current);
        });

        return Array.from(bucketMap.values()).sort(function (left, right) {
            return left.sortValue - right.sortValue;
        });
    }

    function renderChart(rows) {
        if (!chartContainer || !Plotly) {
            return;
        }
        const series = aggregateRows(rows, state.filters.metricPeriodMode || 'quarterly');
        if (!series.length) {
            Plotly.react(chartContainer, [], {
                title: 'Belum ada data pada filter aktif',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
            }, { responsive: true });
            return;
        }

        Plotly.react(chartContainer, [
            {
                x: series.map((item) => item.label),
                y: series.map((item) => item.total),
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Total',
                line: { color: '#405189', width: 3 },
                marker: { size: 8 },
            },
            {
                x: series.map((item) => item.label),
                y: series.map((item) => item.selesai),
                type: 'bar',
                name: 'Selesai',
                marker: { color: '#0ab39c', opacity: 0.75 },
            },
            {
                x: series.map((item) => item.label),
                y: series.map((item) => item.dikembalikan),
                type: 'bar',
                name: 'Dikembalikan',
                marker: { color: '#f06548', opacity: 0.75 },
            },
        ], {
            barmode: 'group',
            margin: { l: 48, r: 20, t: 20, b: 48 },
            legend: { orientation: 'h' },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            xaxis: { title: 'Periode' },
            yaxis: { title: 'Jumlah' },
        }, {
            responsive: true,
            displayModeBar: false,
        });
    }

    function resolveCoordinate(row, keys) {
        for (let index = 0; index < keys.length; index += 1) {
            const value = row[keys[index]];
            const numeric = Number(value);
            if (!Number.isNaN(numeric)) {
                return numeric;
            }
        }
        return null;
    }

    function extractMapPoints(rows) {
        return rows.map(function (row) {
            const lat = resolveCoordinate(row, ['latitude', 'lat', 'Latitude']);
            const lng = resolveCoordinate(row, ['longitude', 'lng', 'lon', 'Longitude']);
            if (lat === null || lng === null) {
                return null;
            }
            return {
                lat,
                lng,
                label: row.daerah || row.label || row.record_label || row.record_key || 'Titik data',
                hasil: row.hasil || '-',
                jenis: row.jenis || '-',
                tanggal: row.tanggal || '-',
            };
        }).filter(Boolean);
    }

    function ensureMap() {
        if (!mapContainer || !L) {
            return null;
        }
        if (!state.map) {
            state.map = L.map(mapContainer, {
                scrollWheelZoom: false,
            }).setView([-2.5, 118], 4);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '&copy; OpenStreetMap contributors',
            }).addTo(state.map);
        }
        return state.map;
    }

    function renderMap(rows) {
        if (!mapSummary) {
            return;
        }
        const points = extractMapPoints(rows);
        mapSummary.innerHTML = `
            <div class="d-flex flex-column gap-3">
                <div>
                    <div class="text-muted small">Titik terpetakan</div>
                    <div class="display-6">${escapeHtml(formatNumber(points.length))}</div>
                </div>
                <div class="alert alert-light border mb-0">${escapeHtml(points.length ? 'Marker diambil dari field latitude/longitude yang lolos filter aktif.' : 'Belum ada koordinat pada data aktif, jadi peta ditampilkan sebagai empty state.')}</div>
            </div>
        `;

        const map = ensureMap();
        if (!map) {
            return;
        }
        if (state.mapLayer) {
            state.mapLayer.remove();
            state.mapLayer = null;
        }
        if (!points.length) {
            map.setView([-2.5, 118], 4);
            return;
        }

        state.mapLayer = L.layerGroup(points.map(function (point) {
            return L.marker([point.lat, point.lng]).bindPopup(`
                <strong>${escapeHtml(point.label)}</strong><br />
                Status: ${escapeHtml(point.hasil)}<br />
                Jenis: ${escapeHtml(point.jenis)}<br />
                Tanggal: ${escapeHtml(point.tanggal)}
            `);
        }));
        state.mapLayer.addTo(map);
        const bounds = L.latLngBounds(points.map((point) => [point.lat, point.lng]));
        map.fitBounds(bounds.pad(0.2));
    }

    function applyDatasetFilters(rows) {
        return rows.filter(function (row) {
            if (state.filters.reportingYear && String(row.reporting_year || '') !== String(state.filters.reportingYear)) {
                return false;
            }
            if (state.filters.status && String(row.hasil || '') !== String(state.filters.status)) {
                return false;
            }
            if (state.filters.jenis && String(row.jenis || '') !== String(state.filters.jenis)) {
                return false;
            }
            const rowDate = resolveRowDate(row);
            if (state.filters.dateStart && rowDate && rowDate.getTime() < new Date(`${state.filters.dateStart}T00:00:00`).getTime()) {
                return false;
            }
            if (state.filters.dateEnd && rowDate && rowDate.getTime() > new Date(`${state.filters.dateEnd}T23:59:59`).getTime()) {
                return false;
            }
            if ((state.filters.dateStart || state.filters.dateEnd) && !rowDate) {
                return false;
            }
            return true;
        });
    }

    function rerenderDatasetView() {
        const detail = state.currentDatasetDetail;
        if (!detail) {
            return;
        }
        const dataset = detail.dataset || {};
        const activeVersion = detail.published_version || detail.draft_version || null;
        const latestRun = (state.currentDatasetRuns || []).find((run) => run.status === 'succeeded') || state.currentDatasetRuns[0] || null;
        const summaryJson = (latestRun && latestRun.summary_json) || {};
        const rows = Array.isArray(summaryJson.row_snapshots) ? summaryJson.row_snapshots : [];
        const filteredRows = applyDatasetFilters(rows);

        renderMetricCards(filteredRows, summaryJson);
        renderDatasetSummary(dataset, activeVersion, latestRun, filteredRows);
        renderExecutionBridge(detail, latestRun);
        renderChart(filteredRows);
        renderDetailTable(filteredRows);
        renderNarrative(filteredRows, summaryJson);
        renderMap(filteredRows);
    }

    function populateFilterControls(detail, runs) {
        const successfulRun = (runs || []).find((run) => run.status === 'succeeded') || (runs || [])[0] || null;
        const summaryJson = (successfulRun && successfulRun.summary_json) || {};
        const options = collectFilterOptions(summaryJson);

        populateSelectOptions(datasetFilterReportingYear, options.reportingYears, state.filters.reportingYear, 'Semua Tahun');
        populateSelectOptions(datasetFilterStatus, options.statuses, state.filters.status, 'Semua Status');
        populateSelectOptions(datasetFilterJenis, options.jenisOptions, state.filters.jenis, 'Semua Jenis');
    }

    function loadDatasetRuns(datasetId) {
        if (!datasetId || !config.analyticsDatasetRunsUrlTemplate) {
            state.currentDatasetRuns = [];
            renderRunsList([]);
            return Promise.resolve([]);
        }
        const url = replaceTemplate(config.analyticsDatasetRunsUrlTemplate, '__DATASET_ID__', datasetId);
        return fetchJson(url).then(function (data) {
            state.currentDatasetRuns = data.runs || [];
            renderRunsList(state.currentDatasetRuns);
            return state.currentDatasetRuns;
        }).catch(function () {
            datasetRunsList.innerHTML = '<div class="text-danger">Gagal memuat dataset runs.</div>';
            state.currentDatasetRuns = [];
            return [];
        });
    }

    function loadDatasetDetail(datasetId) {
        if (!datasetId || !config.analyticsDatasetDetailUrlTemplate) {
            return;
        }
        state.selectedDatasetId = datasetId;
        const url = replaceTemplate(config.analyticsDatasetDetailUrlTemplate, '__DATASET_ID__', datasetId);
        fetchJson(url).then(function (data) {
            state.currentDatasetDetail = data;
            return loadDatasetRuns(datasetId).then(function (runs) {
                populateFilterControls(data, runs);
                rerenderDatasetView();
            });
        }).catch(function (error) {
            datasetDetailSummary.innerHTML = `<div class="text-danger">${escapeHtml(error.message || 'Gagal memuat detail dataset.')}</div>`;
            if (datasetMetricCards) {
                datasetMetricCards.innerHTML = '<div class="col-12"><div class="alert alert-light border mb-0">Belum ada data insight yang bisa ditampilkan.</div></div>';
            }
        });
    }

    function populateDatasetSelect(items) {
        if (!datasetSelect) {
            return;
        }
        if (!items.length) {
            datasetSelect.innerHTML = '<option value="">Belum ada dataset terkait</option>';
            return;
        }
        datasetSelect.innerHTML = items.map(function (item) {
            const dataset = item.dataset || {};
            const selected = String(dataset.id) === String(state.selectedDatasetId || '') ? ' selected' : '';
            return `<option value="${escapeHtml(dataset.id)}"${selected}>${escapeHtml(dataset.name || dataset.dataset_key || 'Dataset')}</option>`;
        }).join('');
    }

    function executeSelectedDatasetRun() {
        const detail = state.currentDatasetDetail;
        const dataset = detail && detail.dataset;
        const activeVersion = detail && (detail.published_version || detail.draft_version);
        if (!dataset || !activeVersion || !config.analyticsDatasetExecuteUrlTemplate) {
            return Promise.resolve();
        }

        const executeUrl = replaceTemplate(
            replaceTemplate(config.analyticsDatasetExecuteUrlTemplate, '__DATASET_ID__', dataset.id),
            '__DATASET_VERSION_ID__',
            activeVersion.id
        );

        if (datasetRunButton) {
            datasetRunButton.disabled = true;
            datasetRunButton.textContent = 'Menjalankan Dataset...';
        }
        if (datasetExecutionStatus) {
            datasetExecutionStatus.className = 'alert alert-warning mb-0';
            datasetExecutionStatus.textContent = 'Dataset run sedang dieksekusi. Tunggu sebentar...';
        }

        return postJson(executeUrl, {
            trigger_type: 'manual',
            requested_reporting_year: state.filters.reportingYear || undefined,
            requested_filters_json: {
                reporting_year: state.filters.reportingYear || undefined,
                hasil: state.filters.status || undefined,
                jenis: state.filters.jenis || undefined,
                date_start: state.filters.dateStart || undefined,
                date_end: state.filters.dateEnd || undefined,
            },
        }).then(function (data) {
            if (data && data.run) {
                state.currentDatasetRuns = [data.run].concat((state.currentDatasetRuns || []).filter((item) => String(item.id) !== String(data.run.id)));
                renderRunsList(state.currentDatasetRuns);
            }
            return loadDatasetDetail(dataset.id);
        }).catch(function (error) {
            if (datasetExecutionStatus) {
                datasetExecutionStatus.className = 'alert alert-danger mb-0';
                datasetExecutionStatus.textContent = error.message || 'Gagal menjalankan dataset.';
            }
        }).finally(function () {
            if (datasetRunButton) {
                datasetRunButton.disabled = false;
                datasetRunButton.textContent = 'Jalankan Dataset Sekarang';
            }
        });
    }

    function bindFilters() {
        if (datasetSelect) {
            datasetSelect.addEventListener('change', function (event) {
                loadDatasetDetail(event.target.value);
            });
        }
        if (datasetRunButton) {
            datasetRunButton.addEventListener('click', function () {
                executeSelectedDatasetRun();
            });
        }
        if (datasetRunsRefreshButton) {
            datasetRunsRefreshButton.addEventListener('click', function () {
                if (state.selectedDatasetId) {
                    loadDatasetDetail(state.selectedDatasetId);
                }
            });
        }
        [
            [datasetFilterReportingYear, 'reportingYear'],
            [datasetFilterStatus, 'status'],
            [datasetFilterJenis, 'jenis'],
            [datasetFilterDateStart, 'dateStart'],
            [datasetFilterDateEnd, 'dateEnd'],
            [datasetMetricPeriodMode, 'metricPeriodMode'],
        ].forEach(function (entry) {
            const element = entry[0];
            const key = entry[1];
            if (!element) {
                return;
            }
            element.addEventListener('change', function () {
                state.filters[key] = element.value || '';
                rerenderDatasetView();
            });
        });

        if (datasetQuickRanges) {
            datasetQuickRanges.querySelectorAll('[data-quick-range]').forEach(function (button) {
                button.addEventListener('click', function () {
                    const presetKey = button.getAttribute('data-quick-range');
                    const range = getCalendarPresetRange(presetKey);
                    state.filters.dateStart = range.start;
                    state.filters.dateEnd = range.end;
                    if (datasetFilterDateStart) {
                        datasetFilterDateStart.value = range.start;
                    }
                    if (datasetFilterDateEnd) {
                        datasetFilterDateEnd.value = range.end;
                    }
                    datasetQuickRanges.querySelectorAll('[data-quick-range]').forEach(function (item) {
                        item.setAttribute('data-selected', item === button ? 'true' : 'false');
                    });
                    rerenderDatasetView();
                });
            });
        }
    }

    function loadDatasets() {
        if (!config.analyticsDatasetsUrl) {
            return;
        }
        fetchJson(config.analyticsDatasetsUrl).then(function (data) {
            const allDatasets = data.datasets || [];
            state.datasets = allDatasets.filter(datasetMatchesRegistry);
            if (!state.selectedDatasetId && state.datasets[0] && state.datasets[0].dataset) {
                state.selectedDatasetId = state.datasets[0].dataset.id;
            }
            populateDatasetSelect(state.datasets);
            if (state.selectedDatasetId) {
                loadDatasetDetail(state.selectedDatasetId);
            } else {
                datasetDetailSummary.innerHTML = '<div class="text-muted">Belum ada dataset terkait untuk registry ini.</div>';
                datasetRunsList.innerHTML = '<div class="text-muted">Belum ada dataset run untuk ditampilkan.</div>';
            }
        }).catch(function (error) {
            datasetDetailSummary.innerHTML = `<div class="text-danger">${escapeHtml(error.message || 'Gagal memuat daftar dataset.')}</div>`;
            datasetRunsList.innerHTML = '<div class="text-danger">Gagal memuat dataset runs.</div>';
        });
    }

    if (datasetMetricPeriodMode && !datasetMetricPeriodMode.value) {
        datasetMetricPeriodMode.value = 'quarterly';
    }
    state.filters.metricPeriodMode = datasetMetricPeriodMode ? datasetMetricPeriodMode.value : 'quarterly';

    bindFilters();
    loadDatasets();
})();
