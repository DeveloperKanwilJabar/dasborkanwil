(function () {
    const config = window.analyticsWorkspaceConfig || {};
    const Grid = window.gridjs && window.gridjs.Grid;
    const Plotly = window.Plotly;

    const reportGridContainer = document.getElementById('analyticsReportsGrid');
    const indicatorGridContainer = document.getElementById('analyticsIndicatorsGrid');
    const resultsTableBody = document.querySelector('#analyticsResultsTable tbody');
    const resultsFilterReportingYear = document.getElementById('analyticsResultsFilterReportingYear');
    const resultsFilterStatus = document.getElementById('analyticsResultsFilterStatus');
    const datasetRunsList = document.getElementById('analyticsDatasetRunsList');
    const datasetDetailPanel = document.getElementById('analyticsDatasetDetailPanel');
    const datasetFilterReportingYear = document.getElementById('analyticsDatasetFilterReportingYear');
    const datasetFilterStatus = document.getElementById('analyticsDatasetFilterStatus');
    const datasetFilterJenis = document.getElementById('analyticsDatasetFilterJenis');
    const datasetFilterDateStart = document.getElementById('analyticsDatasetFilterDateStart');
    const datasetFilterDateEnd = document.getElementById('analyticsDatasetFilterDateEnd');
    const datasetMetricPeriodMode = document.getElementById('analyticsDatasetMetricPeriodMode');
    const datasetQuickRanges = document.getElementById('analyticsDatasetQuickRanges');
    const datasetInsightPanel = document.getElementById('analyticsDatasetInsightPanel');
    const reportDetailPanel = document.getElementById('analyticsReportDetailPanel');
    const indicatorDetailPanel = document.getElementById('analyticsIndicatorDetailPanel');
    const indicatorTabNavigation = document.getElementById('indicatorDetailTabNavigation');

    const state = {
        reports: [],
        indicators: [],
        results: [],
        datasets: [],
        reportGrid: null,
        indicatorGrid: null,
        activeIndicatorTab: 'definition',
        selectedReportId: null,
        selectedIndicatorId: null,
        selectedIndicatorVersionId: null,
        selectedDatasetId: null,
        currentDatasetDetail: null,
        charts: {},
        resultFilters: {
            reportingYear: '',
            status: '',
        },
        datasetFilters: {
            reportingYear: '',
            status: '',
            jenis: '',
            dateStart: '',
            dateEnd: '',
            metricPeriodMode: 'quarterly',
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

    function formatJsonBlock(value, emptyMessage) {
        if (!value || (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) || (Array.isArray(value) && !value.length)) {
            return `<div class="text-muted">${escapeHtml(emptyMessage)}</div>`;
        }
        return `<pre class="bg-white border rounded p-3 mb-0">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }

    function buildMetaDescription(metaDescription, emptyMessage) {
        return metaDescription
            ? `<pre class="bg-white border rounded p-3 mb-0">${escapeHtml(metaDescription)}</pre>`
            : `<div class="text-muted">${escapeHtml(emptyMessage)}</div>`;
    }

    async function fetchJson(url) {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const payload = await response.json();
        if (!response.ok || payload.success === false) {
            throw new Error(payload.message || 'Request gagal.');
        }
        return payload.data || {};
    }

    function setSummaryValue(key, value) {
        const el = document.querySelector(`[data-summary-value="${key}"]`);
        if (el) {
            el.textContent = String(value ?? 0);
        }
    }

    function formatNumber(value) {
        const numeric = Number(value);
        if (Number.isNaN(numeric)) {
            return value ?? '-';
        }
        return new Intl.NumberFormat('id-ID').format(numeric);
    }

    function formatDateTime(value) {
        if (!value) {
            return '-';
        }
        return String(value).replace('T', ' ').replace('+00:00', ' UTC');
    }

    function resolveRunStatusTone(status) {
        if (status === 'succeeded') {
            return { bg: 'success', text: 'success' };
        }
        if (status === 'failed') {
            return { bg: 'danger', text: 'danger' };
        }
        if (status === 'running') {
            return { bg: 'warning', text: 'warning' };
        }
        return { bg: 'secondary', text: 'secondary' };
    }

    function findIndicatorWorkspaceByVersionId(indicatorVersionId) {
        return state.indicators.find((item) => (item.published_version && item.published_version.id === indicatorVersionId) || (item.draft_version && item.draft_version.id === indicatorVersionId));
    }

    function findReportWorkspaceByIndicatorVersionId(indicatorVersionId) {
        return state.reports.find((item) => (item.indicator_mappings || []).some((mapping) => mapping.indicator_version && mapping.indicator_version.id === indicatorVersionId));
    }

    function findDatasetWorkspaceById(datasetId) {
        return state.datasets.find((item) => item.dataset && item.dataset.id === datasetId);
    }

    function destroyChart(key) {
        const chartState = state.charts[key];
        if (!chartState) {
            return;
        }
        if (chartState.library === 'plotly' && Plotly && chartState.element) {
            Plotly.purge(chartState.element);
        }
        delete state.charts[key];
    }

    function toChartSeriesMap(value) {
        if (!value || typeof value !== 'object') {
            return [];
        }
        return Object.entries(value).map(([label, count]) => ({ label, count: Number(count || 0) }));
    }

    function mapMetricPeriodModeLabel(mode) {
        const labels = {
            daily: 'Harian',
            weekly: 'Mingguan',
            monthly: 'Bulanan',
            quarterly: 'Triwulan',
            four_monthly: 'Caturwulan',
            semesterly: 'Semester',
            yearly: 'Tahunan',
            fiscal_year: 'Tahun Anggaran',
        };
        return labels[mode] || mode || 'Triwulan';
    }

    function toRomanNumeral(value) {
        const numerals = {
            1: 'I',
            2: 'II',
            3: 'III',
            4: 'IV',
            5: 'V',
            6: 'VI',
            7: 'VII',
            8: 'VIII',
            9: 'IX',
            10: 'X',
            11: 'XI',
            12: 'XII',
        };
        return numerals[value] || String(value || '-');
    }

    function getIndonesianMonthName(monthNumber) {
        const monthNames = [
            'Januari',
            'Februari',
            'Maret',
            'April',
            'Mei',
            'Juni',
            'Juli',
            'Agustus',
            'September',
            'Oktober',
            'November',
            'Desember',
        ];
        return monthNames[Math.max(0, Number(monthNumber || 1) - 1)] || '-';
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

    function resolveRowDate(row) {
        const rawValue = row && row.tanggal ? String(row.tanggal) : '';
        if (!rawValue) {
            return null;
        }
        const parsed = new Date(`${rawValue}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    function resolveDateRange(summaryJson) {
        const rowSnapshots = Array.isArray(summaryJson && summaryJson.row_snapshots) ? summaryJson.row_snapshots : [];
        const dates = rowSnapshots
            .map((row) => resolveRowDate(row))
            .filter(Boolean)
            .sort((left, right) => left.getTime() - right.getTime());
        return {
            min: dates[0] || null,
            max: dates[dates.length - 1] || null,
        };
    }

    function clampDateToRange(date, range, side = 'both') {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
            return null;
        }
        let nextDate = new Date(date);
        if ((side === 'both' || side === 'min') && range && range.min && nextDate.getTime() < range.min.getTime()) {
            nextDate = new Date(range.min);
        }
        if ((side === 'both' || side === 'max') && range && range.max && nextDate.getTime() > range.max.getTime()) {
            nextDate = new Date(range.max);
        }
        return nextDate;
    }

    function resolvePresetAnchorDate(summaryJson, presetKey) {
        const range = resolveDateRange(summaryJson);
        if (presetKey === 'full_range') {
            return range.max ? new Date(range.max) : null;
        }
        const calendarPresets = new Set([
            'last_7_days',
            'last_30_days',
            'last_90_days',
            'current_week',
            'current_month',
            'current_quarter',
            'current_semester',
            'current_year',
        ]);
        if (calendarPresets.has(presetKey)) {
            return new Date();
        }
        return range.max ? new Date(range.max) : null;
    }

    function getIsoWeekInfo(date) {
        const workingDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        workingDate.setUTCDate(workingDate.getUTCDate() + 4 - (workingDate.getUTCDay() || 7));
        const yearStart = new Date(Date.UTC(workingDate.getUTCFullYear(), 0, 1));
        const week = Math.ceil((((workingDate - yearStart) / 86400000) + 1) / 7);
        return {
            year: workingDate.getUTCFullYear(),
            week,
        };
    }

    function resolvePresetDateRange(summaryJson, presetKey) {
        const range = resolveDateRange(summaryJson);
        const anchorDate = resolvePresetAnchorDate(summaryJson, presetKey);
        if (!anchorDate) {
            return { start: '', end: '' };
        }
        if (presetKey === 'full_range') {
            return {
                start: formatDateInputValue(range.min),
                end: formatDateInputValue(range.max),
            };
        }
        const end = new Date(anchorDate);
        const start = new Date(anchorDate);
        if (presetKey === 'last_7_days') {
            start.setDate(start.getDate() - 6);
        } else if (presetKey === 'last_30_days') {
            start.setDate(start.getDate() - 29);
        } else if (presetKey === 'last_90_days') {
            start.setDate(start.getDate() - 89);
        } else if (presetKey === 'current_week') {
            const dayOfWeek = start.getDay();
            const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
            start.setDate(start.getDate() + diffToMonday);
        } else if (presetKey === 'current_month') {
            start.setDate(1);
        } else if (presetKey === 'current_quarter') {
            const quarterStartMonth = Math.floor(end.getMonth() / 3) * 3;
            start.setMonth(quarterStartMonth, 1);
        } else if (presetKey === 'current_semester') {
            const semesterStartMonth = end.getMonth() < 6 ? 0 : 6;
            start.setMonth(semesterStartMonth, 1);
        } else if (presetKey === 'current_year') {
            start.setMonth(0, 1);
        } else {
            return { start: '', end: '' };
        }
        const normalizedStart = clampDateToRange(start, range, 'none') || start;
        const normalizedEnd = clampDateToRange(end, range, 'none') || end;
        return {
            start: formatDateInputValue(normalizedStart),
            end: formatDateInputValue(normalizedEnd),
        };
    }

    function applyQuickDatePreset(summaryJson, presetKey) {
        const range = resolvePresetDateRange(summaryJson, presetKey);
        state.datasetFilters = {
            ...state.datasetFilters,
            dateStart: range.start,
            dateEnd: range.end,
        };
        if (datasetFilterDateStart) {
            datasetFilterDateStart.value = range.start;
        }
        if (datasetFilterDateEnd) {
            datasetFilterDateEnd.value = range.end;
        }
    }

    function resolvePeriodLabel(row, metricPeriodMode) {
        const rowDate = resolveRowDate(row);
        if (rowDate) {
            const year = rowDate.getFullYear();
            const month = rowDate.getMonth() + 1;
            const day = rowDate.getDate();
            if (metricPeriodMode === 'daily') {
                return `${day} ${getIndonesianMonthName(month)} ${year}`;
            }
            if (metricPeriodMode === 'weekly') {
                const weekInfo = getIsoWeekInfo(rowDate);
                return `Minggu ${weekInfo.week} ${weekInfo.year}`;
            }
            if (metricPeriodMode === 'monthly') {
                return `${getIndonesianMonthName(month)} ${year}`;
            }
            if (metricPeriodMode === 'quarterly') {
                return `Triwulan ${toRomanNumeral(Math.ceil(month / 3))} ${year}`;
            }
            if (metricPeriodMode === 'four_monthly') {
                return `Caturwulan ${toRomanNumeral(Math.ceil(month / 4))} ${year}`;
            }
            if (metricPeriodMode === 'semesterly') {
                return `Semester ${toRomanNumeral(Math.ceil(month / 6))} ${year}`;
            }
            if (metricPeriodMode === 'yearly' || metricPeriodMode === 'fiscal_year') {
                return metricPeriodMode === 'fiscal_year' ? `Tahun Anggaran ${year}` : `Tahun ${year}`;
            }
        }

        if (metricPeriodMode === 'weekly' && row.week_number != null) {
            return `Minggu ${row.week_number} ${row.reporting_year || ''}`.trim();
        }
        if (metricPeriodMode === 'monthly' && row.month_number != null) {
            return `${getIndonesianMonthName(row.month_number)} ${row.reporting_year || ''}`.trim();
        }
        if (metricPeriodMode === 'quarterly' && row.quarter_number != null) {
            return `Triwulan ${toRomanNumeral(row.quarter_number)} ${row.reporting_year || ''}`.trim();
        }
        if (metricPeriodMode === 'four_monthly' && row.four_month_number != null) {
            return `Caturwulan ${toRomanNumeral(row.four_month_number)} ${row.reporting_year || ''}`.trim();
        }
        if (metricPeriodMode === 'semesterly' && row.semester_number != null) {
            return `Semester ${toRomanNumeral(row.semester_number)} ${row.reporting_year || ''}`.trim();
        }
        if ((metricPeriodMode === 'yearly' || metricPeriodMode === 'fiscal_year') && row.reporting_year != null) {
            return metricPeriodMode === 'fiscal_year' ? `Tahun Anggaran ${row.reporting_year}` : `Tahun ${row.reporting_year}`;
        }

        const fallbackKeys = ['quarter_label', 'semester_label', 'month_label', 'week_label', 'day_label', 'year_label'];
        for (const key of fallbackKeys) {
            if (row[key]) {
                return row[key];
            }
        }
        return '-';
    }

    function resolvePeriodNumber(row, metricPeriodMode) {
        const numericKeyMap = {
            daily: 'day_number',
            weekly: 'week_number',
            monthly: 'month_number',
            quarterly: 'quarter_number',
            four_monthly: 'four_month_number',
            semesterly: 'semester_number',
            yearly: 'year_number',
            fiscal_year: 'fiscal_year_number',
        };
        if (metricPeriodMode === 'yearly' || metricPeriodMode === 'fiscal_year') {
            return Number(row.reporting_year || row.year_number || 1);
        }
        const primaryKey = numericKeyMap[metricPeriodMode];
        const fallbackKeys = ['quarter_number', 'semester_number', 'month_number', 'week_number', 'day_number'];
        if (primaryKey && row[primaryKey] != null) {
            return Number(row[primaryKey] || 0);
        }
        const rowDate = resolveRowDate(row);
        if (rowDate) {
            const month = rowDate.getMonth() + 1;
            if (metricPeriodMode === 'daily') {
                return Number(formatDateInputValue(rowDate).replaceAll('-', ''));
            }
            if (metricPeriodMode === 'weekly') {
                const weekInfo = getIsoWeekInfo(rowDate);
                return Number(`${weekInfo.year}${padNumber(weekInfo.week)}`);
            }
            if (metricPeriodMode === 'monthly') {
                return Number(`${rowDate.getFullYear()}${padNumber(month)}`);
            }
            if (metricPeriodMode === 'four_monthly') {
                return Number(`${rowDate.getFullYear()}${Math.ceil(month / 4)}`);
            }
        }
        for (const key of fallbackKeys) {
            if (row[key] != null) {
                return Number(row[key] || 0);
            }
        }
        return 0;
    }

    function renderPlotlyChart(key, selector, data, layout, configOverrides = {}) {
        destroyChart(key);
        const el = document.querySelector(selector);
        if (!el) {
            return;
        }
        if (!Plotly) {
            el.innerHTML = '<div class="text-muted">Library Plotly belum tersedia.</div>';
            return;
        }
        const hasData = Array.isArray(data) && data.some((trace) => Array.isArray(trace.x) ? trace.x.length : Array.isArray(trace.labels) ? trace.labels.length : Array.isArray(trace.values) ? trace.values.length : Array.isArray(trace.r) ? trace.r.length : false);
        const emptyMessage = layout && layout.emptyMessage ? layout.emptyMessage : 'Belum ada data chart.';
        if (!hasData) {
            el.innerHTML = `<div class="text-muted">${escapeHtml(emptyMessage)}</div>`;
            return;
        }
        el.innerHTML = '';
        const chartConfig = {
            displayModeBar: false,
            responsive: true,
            ...configOverrides,
        };
        const { emptyMessage: _unusedEmptyMessage, ...plotLayout } = layout || {};
        Plotly.newPlot(el, data, {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 56, r: 24, b: 56, l: 56 },
            font: { family: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', size: 12 },
            legend: { orientation: 'h', y: -0.2 },
            hoverlabel: { namelength: -1 },
            ...plotLayout,
        }, chartConfig);
        state.charts[key] = { library: 'plotly', element: el };
    }

    function buildQuickFlowButton(label, attrs) {
        const htmlAttrs = Object.entries(attrs || {}).map(([key, value]) => `${key}="${escapeHtml(value)}"`).join(' ');
        return `<button type="button" class="btn btn-sm btn-soft-primary" ${htmlAttrs}>${escapeHtml(label)}</button>`;
    }

    function buildSelectOptions(selectElement, values, selectedValue, defaultLabel) {
        if (!selectElement) {
            return;
        }
        const normalizedSelected = selectedValue == null ? '' : String(selectedValue);
        const options = [`<option value="">${escapeHtml(defaultLabel || 'Semua')}</option>`].concat((values || []).map((value) => {
            const normalizedValue = value == null ? '' : String(value);
            const isSelected = normalizedSelected && normalizedSelected === normalizedValue;
            return `<option value="${escapeHtml(normalizedValue)}"${isSelected ? ' selected' : ''}>${escapeHtml(normalizedValue)}</option>`;
        }));
        selectElement.innerHTML = options.join('');
        selectElement.value = normalizedSelected;
    }

    function renderDatasetInsights(filteredDataset) {
        if (!datasetInsightPanel) {
            return;
        }
        if (!filteredDataset || !filteredDataset.filteredRows.length) {
            datasetInsightPanel.innerHTML = '<div class="text-muted">Belum ada insight karena filter saat ini tidak menghasilkan data.</div>';
            return;
        }
        const { completion, filteredRows, topDaerah, topJenis, topTimKerja, selectedPeriodMetric, filters } = filteredDataset;
        const filterBadges = [
            filters.reportingYear ? `Tahun ${filters.reportingYear}` : 'Semua Tahun',
            filters.status ? `Status ${filters.status}` : 'Semua Status',
            filters.jenis ? `Jenis ${filters.jenis}` : 'Semua Jenis',
            filters.dateStart || filters.dateEnd ? `Tanggal ${filters.dateStart || '...'} s.d. ${filters.dateEnd || '...'}` : 'Semua Tanggal',
            `Mode ${mapMetricPeriodModeLabel(filters.metricPeriodMode)}`,
        ];
        const strongestPeriod = selectedPeriodMetric[0];
        datasetInsightPanel.innerHTML = `
            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                <div>
                    <div class="fw-semibold mb-2">Insight Otomatis Filter Saat Ini</div>
                    <div class="text-muted small mb-2">${filterBadges.map((item) => `<span class="badge bg-secondary-subtle text-secondary me-1 mb-1">${escapeHtml(item)}</span>`).join('')}</div>
                    <div class="small">${escapeHtml(`Tersaring ${filteredRows.length} baris dengan ${completion.selesai} selesai dan ${completion.dikembalikan} dikembalikan (${completion.achievementPercentage}% selesai).`)}</div>
                </div>
                <div class="text-muted small">Insight ini dibangkitkan otomatis dari row_snapshots summary_json demo.</div>
            </div>
            <div class="row g-3 mt-1">
                <div class="col-md-4"><div class="border rounded p-3 bg-white h-100"><div class="text-muted small">Dominasi Daerah</div><div class="fw-semibold">${escapeHtml(topDaerah && topDaerah.length ? `${topDaerah[0].label} (${topDaerah[0].count})` : '-')}</div></div></div>
                <div class="col-md-4"><div class="border rounded p-3 bg-white h-100"><div class="text-muted small">Jenis Terbanyak</div><div class="fw-semibold">${escapeHtml(topJenis ? `${topJenis.label} (${topJenis.count})` : '-')}</div></div></div>
                <div class="col-md-4"><div class="border rounded p-3 bg-white h-100"><div class="text-muted small">Tim Kerja Dominan</div><div class="fw-semibold">${escapeHtml(topTimKerja ? `${topTimKerja.label} (${topTimKerja.count})` : '-')}</div></div></div>
                <div class="col-12"><div class="border rounded p-3 bg-white"><div class="text-muted small">Puncak Periode</div><div class="fw-semibold">${escapeHtml(strongestPeriod ? `${strongestPeriod.label} (${strongestPeriod.total} dokumen, ${strongestPeriod.achievement_percentage}% selesai)` : 'Belum ada data periode.')}</div></div></div>
            </div>
        `;
    }

    function normalizeCounterMap(rows, key, fallbackLabel) {
        return rows.reduce((acc, row) => {
            const label = row[key] || fallbackLabel;
            acc[label] = (acc[label] || 0) + 1;
            return acc;
        }, {});
    }

    function buildTopItems(counterMap, limit = 10) {
        return Object.entries(counterMap || {})
            .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
            .slice(0, limit)
            .map(([label, count]) => ({ label, count }));
    }

    function applyDatasetFilters(summaryJson) {
        const rowSnapshots = Array.isArray(summaryJson && summaryJson.row_snapshots) ? summaryJson.row_snapshots : [];
        const filters = {
            reportingYear: datasetFilterReportingYear ? datasetFilterReportingYear.value : state.datasetFilters.reportingYear,
            status: datasetFilterStatus ? datasetFilterStatus.value : state.datasetFilters.status,
            jenis: datasetFilterJenis ? datasetFilterJenis.value : state.datasetFilters.jenis,
            dateStart: datasetFilterDateStart ? datasetFilterDateStart.value : state.datasetFilters.dateStart,
            dateEnd: datasetFilterDateEnd ? datasetFilterDateEnd.value : state.datasetFilters.dateEnd,
            metricPeriodMode: datasetMetricPeriodMode ? datasetMetricPeriodMode.value : state.datasetFilters.metricPeriodMode,
        };
        state.datasetFilters = { ...state.datasetFilters, ...filters };
        const filteredRows = rowSnapshots.filter((row) => {
            if (filters.reportingYear && String(row.reporting_year) !== String(filters.reportingYear)) {
                return false;
            }
            if (filters.status && String(row.hasil) !== String(filters.status)) {
                return false;
            }
            if (filters.jenis && String(row.jenis) !== String(filters.jenis)) {
                return false;
            }
            const rowDate = resolveRowDate(row);
            if (filters.dateStart && rowDate && formatDateInputValue(rowDate) < filters.dateStart) {
                return false;
            }
            if (filters.dateEnd && rowDate && formatDateInputValue(rowDate) > filters.dateEnd) {
                return false;
            }
            return true;
        });

        const hasilCounts = normalizeCounterMap(filteredRows, 'hasil', 'Tanpa Hasil');
        const jenisCounts = normalizeCounterMap(filteredRows, 'jenis', 'Tanpa Jenis');
        const timKerjaCounts = normalizeCounterMap(filteredRows, 'tim_kerja', 'Tanpa Tim');
        const daerahCounts = normalizeCounterMap(filteredRows, 'daerah', 'Tanpa Daerah');
        const metodeCounts = normalizeCounterMap(filteredRows, 'metode', '(kosong)');
        const periodMetricsMap = filteredRows.reduce((acc, row) => {
            const label = resolvePeriodLabel(row, filters.metricPeriodMode);
            if (!acc[label]) {
                acc[label] = {
                    label,
                    period_type: filters.metricPeriodMode,
                    period_number: resolvePeriodNumber(row, filters.metricPeriodMode),
                    reporting_year: Number(row.reporting_year || 0),
                    total: 0,
                    selesai: 0,
                    dikembalikan: 0,
                };
            }
            acc[label].total += 1;
            if (row.hasil === 'Selesai') {
                acc[label].selesai += 1;
            }
            if (row.hasil === 'Dikembalikan') {
                acc[label].dikembalikan += 1;
            }
            return acc;
        }, {});
        const selectedPeriodMetric = Object.values(periodMetricsMap)
            .map((item) => ({ ...item, achievement_percentage: item.total ? Number(((item.selesai / item.total) * 100).toFixed(2)) : 0 }))
            .sort((left, right) => left.reporting_year - right.reporting_year || left.period_number - right.period_number || String(left.label).localeCompare(String(right.label)));

        const completion = {
            selesai: hasilCounts.Selesai || 0,
            dikembalikan: hasilCounts.Dikembalikan || 0,
            achievementPercentage: filteredRows.length ? Number((((hasilCounts.Selesai || 0) / filteredRows.length) * 100).toFixed(2)) : 0,
        };

        return {
            filters,
            filteredRows,
            hasilCounts,
            jenisCounts,
            timKerjaCounts,
            daerahCounts,
            metodeCounts,
            topDaerah: buildTopItems(daerahCounts, 10),
            topJenis: buildTopItems(jenisCounts, 1)[0] || null,
            topTimKerja: buildTopItems(timKerjaCounts, 1)[0] || null,
            completion,
            selectedPeriodMetric,
        };
    }

    function populateDatasetFilterControls(summaryJson) {
        const dimensions = (summaryJson && summaryJson.filter_dimensions) || {};
        buildSelectOptions(datasetFilterReportingYear, dimensions.reporting_years || [], state.datasetFilters.reportingYear, 'Semua Tahun');
        buildSelectOptions(datasetFilterStatus, dimensions.hasil_options || [], state.datasetFilters.status, 'Semua Status');
        buildSelectOptions(datasetFilterJenis, dimensions.jenis_options || [], state.datasetFilters.jenis, 'Semua Jenis');
        const dateRange = resolveDateRange(summaryJson);
        if (datasetFilterDateStart) {
            datasetFilterDateStart.min = formatDateInputValue(dateRange.min);
            datasetFilterDateStart.max = formatDateInputValue(dateRange.max);
            datasetFilterDateStart.value = state.datasetFilters.dateStart || '';
        }
        if (datasetFilterDateEnd) {
            datasetFilterDateEnd.min = formatDateInputValue(dateRange.min);
            datasetFilterDateEnd.max = formatDateInputValue(dateRange.max);
            datasetFilterDateEnd.value = state.datasetFilters.dateEnd || '';
        }
        if (datasetMetricPeriodMode) {
            datasetMetricPeriodMode.value = state.datasetFilters.metricPeriodMode || 'quarterly';
        }
    }

    function populateResultFilterControls() {
        buildSelectOptions(resultsFilterReportingYear, Array.from(new Set(state.results.map((item) => item.reporting_year).filter(Boolean))).sort(), state.resultFilters.reportingYear, 'Semua Tahun');
        buildSelectOptions(resultsFilterStatus, Array.from(new Set(state.results.map((item) => item.completion_status || item.status).filter(Boolean))).sort(), state.resultFilters.status, 'Semua Status');
    }

    function getFilteredResults() {
        return state.results.filter((result) => {
            if (state.resultFilters.reportingYear && String(result.reporting_year) !== String(state.resultFilters.reportingYear)) {
                return false;
            }
            const resultStatus = result.completion_status || result.status;
            if (state.resultFilters.status && String(resultStatus) !== String(state.resultFilters.status)) {
                return false;
            }
            return true;
        });
    }

    async function handleResultRowSelection(indicatorVersionId) {
        const normalizedIndicatorVersionId = Number(indicatorVersionId) || null;
        state.selectedIndicatorVersionId = normalizedIndicatorVersionId;
        renderResultsTable();
        const indicatorWorkspace = findIndicatorWorkspaceByVersionId(normalizedIndicatorVersionId);
        const linkedReport = findReportWorkspaceByIndicatorVersionId(normalizedIndicatorVersionId);
        if (linkedReport && linkedReport.report && linkedReport.report.id) {
            await loadReportDetail(linkedReport.report.id);
        }
        if (indicatorWorkspace && indicatorWorkspace.indicator && indicatorWorkspace.indicator.id) {
            await loadIndicatorDetail(indicatorWorkspace.indicator.id, {
                autoOpenDataset: true,
                selectedIndicatorVersionId: normalizedIndicatorVersionId,
            });
            setActiveIndicatorTab('result-history');
        }
    }

    function wireResultTableActions() {
        if (!resultsTableBody) {
            return;
        }
        resultsTableBody.querySelectorAll('[data-result-indicator-version-id]').forEach((button) => {
            button.addEventListener('click', async () => {
                const indicatorVersionId = button.getAttribute('data-result-indicator-version-id');
                await handleResultRowSelection(indicatorVersionId);
            });
        });
    }

    function bindAnalyticsFilterControls() {
        if (resultsFilterReportingYear) {
            resultsFilterReportingYear.addEventListener('change', () => {
                state.resultFilters.reportingYear = resultsFilterReportingYear.value;
                renderResultsTable();
            });
        }
        if (resultsFilterStatus) {
            resultsFilterStatus.addEventListener('change', () => {
                state.resultFilters.status = resultsFilterStatus.value;
                renderResultsTable();
            });
        }
        [datasetFilterReportingYear, datasetFilterStatus, datasetFilterJenis, datasetFilterDateStart, datasetFilterDateEnd, datasetMetricPeriodMode].filter(Boolean).forEach((element) => {
            element.addEventListener('change', () => {
                state.datasetFilters.reportingYear = datasetFilterReportingYear ? datasetFilterReportingYear.value : state.datasetFilters.reportingYear;
                state.datasetFilters.status = datasetFilterStatus ? datasetFilterStatus.value : state.datasetFilters.status;
                state.datasetFilters.jenis = datasetFilterJenis ? datasetFilterJenis.value : state.datasetFilters.jenis;
                state.datasetFilters.dateStart = datasetFilterDateStart ? datasetFilterDateStart.value : state.datasetFilters.dateStart;
                state.datasetFilters.dateEnd = datasetFilterDateEnd ? datasetFilterDateEnd.value : state.datasetFilters.dateEnd;
                state.datasetFilters.metricPeriodMode = datasetMetricPeriodMode ? datasetMetricPeriodMode.value : state.datasetFilters.metricPeriodMode;
                if (state.currentDatasetDetail) {
                    renderDatasetDetail(state.currentDatasetDetail);
                }
            });
        });
        if (datasetQuickRanges) {
            datasetQuickRanges.querySelectorAll('[data-quick-range]').forEach((button) => {
                button.addEventListener('click', () => {
                    if (!state.currentDatasetDetail) {
                        return;
                    }
                    const latestRun = (state.currentDatasetDetail.runs || [])[0] || null;
                    applyQuickDatePreset((latestRun && latestRun.summary_json) || {}, button.getAttribute('data-quick-range'));
                    state.datasetFilters.dateStart = datasetFilterDateStart ? datasetFilterDateStart.value : state.datasetFilters.dateStart;
                    state.datasetFilters.dateEnd = datasetFilterDateEnd ? datasetFilterDateEnd.value : state.datasetFilters.dateEnd;
                    renderDatasetDetail(state.currentDatasetDetail);
                });
            });
        }
    }

    function renderSummaryCards() {
        setSummaryValue('reports', state.reports.length);
        setSummaryValue('indicators', state.indicators.length);
        setSummaryValue('results', state.results.length);
    }

    function renderPlaceholder(panel, message) {
        if (!panel) {
            return;
        }
        panel.innerHTML = `<div class="text-muted">${escapeHtml(message)}</div>`;
    }

    function renderReportDetail(data) {
        if (!reportDetailPanel) {
            return;
        }
        const report = data.report || {};
        const draftVersion = data.draft_version || null;
        const publishedVersion = data.published_version || null;
        const mappings = data.indicator_mappings || [];
        const activeVersion = publishedVersion || draftVersion || null;
        state.selectedReportId = report.id || null;

        reportDetailPanel.innerHTML = `
            <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                <div>
                    <h5 class="mb-1">${escapeHtml(report.name || '-')}</h5>
                    <div class="text-muted small">${escapeHtml(report.report_key || '-')} • ${escapeHtml(report.report_type || '-')}</div>
                </div>
                <span class="badge bg-info-subtle text-info">${escapeHtml(report.status || '-')}</span>
            </div>
            <p>${escapeHtml(report.description || 'Belum ada deskripsi report.')}</p>
            <div class="row g-3 mb-3">
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-light-subtle h-100">
                        <div class="fw-semibold mb-2">Versi aktif</div>
                        <div class="small text-muted mb-2">${escapeHtml(activeVersion ? `v${activeVersion.version_number}` : '-')} • ${escapeHtml(activeVersion ? activeVersion.status : '-')}</div>
                        ${buildMetaDescription(activeVersion && activeVersion.meta_description, 'Versi aktif belum punya meta description.')}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-light-subtle h-100">
                        <div class="fw-semibold mb-2">Narrative Guidance</div>
                        ${formatJsonBlock(activeVersion && activeVersion.narrative_guidance_json, 'Narrative guidance belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-light-subtle">
                        <div class="fw-semibold mb-2">Structure JSON</div>
                        ${formatJsonBlock(activeVersion && activeVersion.structure_json, 'Structure version belum tersedia.')}
                    </div>
                </div>
            </div>
            <div>
                <div class="fw-semibold mb-2">Indicator Mapping</div>
                <div class="row g-3">
                    ${mappings.length ? mappings.map((item) => {
                        const indicatorWorkspace = findIndicatorWorkspaceByVersionId(item.indicator_version && item.indicator_version.id);
                        const latestResult = indicatorWorkspace && indicatorWorkspace.latest_result;
                        const latestProgress = indicatorWorkspace && indicatorWorkspace.latest_progress_entry;
                        return `
                            <div class="col-12">
                                <div class="border rounded p-3 bg-white">
                                    <div class="d-flex justify-content-between align-items-start gap-2">
                                        <div>
                                            <div class="fw-semibold">${escapeHtml((item.mapping && item.mapping.display_label) || (item.indicator_definition && item.indicator_definition.name) || '-')}</div>
                                            <div class="text-muted small">${escapeHtml((item.indicator_definition && item.indicator_definition.indicator_key) || '-')} • section ${escapeHtml((item.mapping && item.mapping.section_key) || '-')}</div>
                                        </div>
                                        <span class="badge bg-primary-subtle text-primary">${escapeHtml(item.indicator_version ? `v${item.indicator_version.version_number}` : '-')}</span>
                                    </div>
                                    <div class="row g-2 mt-2 small">
                                        <div class="col-md-4"><span class="text-muted">Latest Result:</span> ${escapeHtml(latestResult ? (latestResult.measured_value || latestResult.achievement_percentage || '-') : '-')}</div>
                                        <div class="col-md-4"><span class="text-muted">Target:</span> ${escapeHtml(latestResult ? (latestResult.target_value || '-') : '-')}</div>
                                        <div class="col-md-4"><span class="text-muted">Progress:</span> ${escapeHtml(latestProgress ? (latestProgress.progress_percent || '-') : '-')}</div>
                                    </div>
                                    <div class="mt-2 text-muted small">${escapeHtml((latestResult && (latestResult.qualitative_summary || latestResult.constraint_notes)) || (latestProgress && (latestProgress.qualitative_summary || latestProgress.constraint_notes)) || 'Belum ada narasi periodik pada indikator ini.')}</div>
                                    <div class="mt-3 d-flex gap-2 flex-wrap">
                                        ${buildQuickFlowButton('Buka indikator', { 'data-flow-indicator-id': item.indicator_definition && item.indicator_definition.id ? item.indicator_definition.id : '' })}
                                        ${buildQuickFlowButton('Lihat dataset sumber', { 'data-flow-dataset-id': indicatorWorkspace && indicatorWorkspace.published_version && indicatorWorkspace.published_version.dataset_id ? indicatorWorkspace.published_version.dataset_id : (indicatorWorkspace && indicatorWorkspace.draft_version && indicatorWorkspace.draft_version.dataset_id ? indicatorWorkspace.draft_version.dataset_id : '') })}
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('') : '<div class="col-12 text-muted">Belum ada mapping indikator.</div>'}
                </div>
            </div>
        `;
    }

    function renderIndicatorTabNavigation() {
        if (!indicatorTabNavigation) {
            return;
        }
        indicatorTabNavigation.querySelectorAll('[data-tab-key]').forEach((button) => {
            button.addEventListener('click', () => setActiveIndicatorTab(button.getAttribute('data-tab-key')));
        });
    }

    function setActiveIndicatorTab(tabKey) {
        state.activeIndicatorTab = tabKey;
        document.querySelectorAll('#indicatorDetailTabNavigation [data-tab-key]').forEach((button) => {
            button.classList.toggle('active', button.getAttribute('data-tab-key') === tabKey);
        });
        document.querySelectorAll('[data-tab-pane]').forEach((pane) => {
            pane.classList.toggle('active', pane.getAttribute('data-tab-pane') === tabKey);
        });
    }

    function renderIndicatorDefinitionTab(indicator, draftVersion, publishedVersion) {
        const activeVersion = publishedVersion || draftVersion || {};
        return `
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="table-responsive">
                        <table class="table table-sm align-middle mb-0">
                            <tbody>
                                <tr><th class="text-muted">Indicator Key</th><td>${escapeHtml(indicator.indicator_key || '-')}</td></tr>
                                <tr><th class="text-muted">Indicator Code</th><td>${escapeHtml(indicator.indicator_code || '-')}</td></tr>
                                <tr><th class="text-muted">Source Mode</th><td>${escapeHtml(indicator.source_mode || '-')}</td></tr>
                                <tr><th class="text-muted">Calculation Type</th><td>${escapeHtml(indicator.calculation_type || '-')}</td></tr>
                                <tr><th class="text-muted">Target Source</th><td>${escapeHtml(indicator.target_source_type || '-')}</td></tr>
                                <tr><th class="text-muted">Draft Version</th><td>${escapeHtml(draftVersion ? `v${draftVersion.version_number}` : '-')}</td></tr>
                                <tr><th class="text-muted">Published Version</th><td>${escapeHtml(publishedVersion ? `v${publishedVersion.version_number}` : '-')}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="table-responsive">
                        <table class="table table-sm align-middle mb-0">
                            <tbody>
                                <tr><th class="text-muted">Dataset ID</th><td>${escapeHtml(activeVersion.dataset_id || '-')}</td></tr>
                                <tr><th class="text-muted">Dataset Version ID</th><td>${escapeHtml(activeVersion.dataset_version_id || '-')}</td></tr>
                                <tr><th class="text-muted">Period Mode</th><td>${escapeHtml(activeVersion.period_mode || '-')}</td></tr>
                                <tr><th class="text-muted">Aggregation</th><td>${escapeHtml(activeVersion.aggregation_strategy || '-')}</td></tr>
                                <tr><th class="text-muted">Unit</th><td>${escapeHtml(activeVersion.unit_label || '-')}</td></tr>
                                <tr><th class="text-muted">Threshold Rules</th><td>${escapeHtml((activeVersion.threshold_rules_json || []).length)}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    function renderIndicatorFormulaTab(draftVersion, publishedVersion) {
        return `
            <div class="row g-3">
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Draft Formula JSON</div>
                        ${formatJsonBlock(draftVersion && draftVersion.formula_json, 'Draft formula belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Published Formula JSON</div>
                        ${formatJsonBlock(publishedVersion && publishedVersion.formula_json, 'Published formula belum tersedia.')}
                    </div>
                </div>
            </div>
        `;
    }

    function renderIndicatorTargetTab(draftVersion, publishedVersion) {
        return `
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-white h-100">
                        <div class="fw-semibold mb-2">Draft Target Config</div>
                        ${formatJsonBlock(draftVersion && draftVersion.target_config_json, 'Draft target config belum tersedia.')}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-white h-100">
                        <div class="fw-semibold mb-2">Published Target Config</div>
                        ${formatJsonBlock(publishedVersion && publishedVersion.target_config_json, 'Published target config belum tersedia.')}
                    </div>
                </div>
            </div>
        `;
    }

    function renderIndicatorNarrativeTab(draftVersion, publishedVersion, results, progressEntries) {
        return `
            <div class="row g-3">
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Meta Description Draft</div>
                        ${buildMetaDescription(draftVersion && draftVersion.meta_description, 'Draft meta description belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Meta Description Published</div>
                        ${buildMetaDescription(publishedVersion && publishedVersion.meta_description, 'Published meta description belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Narrative Guidance JSON</div>
                        ${formatJsonBlock((draftVersion && draftVersion.narrative_guidance_json) || (publishedVersion && publishedVersion.narrative_guidance_json), 'Narrative guidance belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Recent Narrative Snapshot</div>
                        ${buildMetaDescription((results[0] && (results[0].qualitative_summary || results[0].constraint_notes)) || (progressEntries[0] && (progressEntries[0].qualitative_summary || progressEntries[0].constraint_notes)), 'Belum ada narasi periodik terbaru.')}
                    </div>
                </div>
            </div>
        `;
    }

    function renderIndicatorProgressHistoryTab(progressEntries) {
        if (!progressEntries.length) {
            return '<div class="text-muted">Belum ada progress history.</div>';
        }
        return `
            <div class="list-group list-group-flush indicator-history-list">
                ${progressEntries.map((entry) => `
                    <div class="list-group-item px-0 bg-transparent">
                        <div class="d-flex justify-content-between gap-2">
                            <div>
                                <div class="fw-semibold">${escapeHtml(entry.reporting_year || '-')} • ${escapeHtml(entry.status || '-')}</div>
                                <div class="text-muted small">Progress ${escapeHtml(entry.progress_percent || '-')}%</div>
                            </div>
                            <span class="badge bg-secondary-subtle text-secondary">${escapeHtml((entry.items || []).length)} item</span>
                        </div>
                        <div class="mt-2">${buildMetaDescription(entry.qualitative_summary || entry.constraint_notes, 'Belum ada narasi progress.')}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    function renderIndicatorResultHistoryTab(results) {
        if (!results.length) {
            return '<div class="text-muted">Belum ada result history.</div>';
        }
        return `
            <div class="list-group list-group-flush indicator-history-list">
                ${results.map((result) => `
                    <div class="list-group-item px-0 bg-transparent">
                        <div class="d-flex justify-content-between gap-2 mb-2">
                            <div>
                                <div class="fw-semibold">${escapeHtml(result.reporting_year || '-')} • ${escapeHtml(result.completion_status || result.status || '-')}</div>
                                <div class="text-muted small">Measured ${escapeHtml(result.measured_value || '-')} / Target ${escapeHtml(result.target_value || '-')}</div>
                            </div>
                            <span class="badge bg-success-subtle text-success">${escapeHtml(result.achievement_percentage || '-')}%</span>
                        </div>
                        ${buildMetaDescription(result.qualitative_summary || result.constraint_notes, 'Belum ada narasi result.')}
                    </div>
                `).join('')}
            </div>
        `;
    }

    function renderIndicatorDetail(data) {
        const indicator = data.indicator || {};
        const draftVersion = data.draft_version || null;
        const publishedVersion = data.published_version || null;
        const results = data.results || [];
        const progressEntries = data.progress_entries || [];

        if (indicatorDetailPanel) {
            const activeVersion = publishedVersion || draftVersion || {};
            const linkedReport = findReportWorkspaceByIndicatorVersionId(activeVersion.id);
            indicatorDetailPanel.innerHTML = `
                <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                    <div>
                        <h5 class="mb-1">${escapeHtml(indicator.name || '-')}</h5>
                        <div class="text-muted small">${escapeHtml(indicator.indicator_key || '-')} • ${escapeHtml(indicator.source_mode || '-')}</div>
                    </div>
                    <span class="badge bg-primary-subtle text-primary">${escapeHtml(indicator.status || '-')}</span>
                </div>
                <p>${escapeHtml(indicator.description || 'Belum ada deskripsi indikator.')}</p>
                <div class="analytics-quick-flow-card mt-3">
                    <div class="fw-semibold mb-2">Quick Flow</div>
                    <div class="text-muted small mb-3">Navigasi cepat dari indikator ke report induk atau dataset sumber supaya alur analisis lebih natural.</div>
                    <div class="d-flex gap-2 flex-wrap">
                        ${linkedReport && linkedReport.report && linkedReport.report.id ? buildQuickFlowButton('Buka report induk', { 'data-flow-report-id': linkedReport.report.id }) : ''}
                        ${activeVersion.dataset_id ? buildQuickFlowButton('Buka dataset sumber', { 'data-flow-dataset-id': activeVersion.dataset_id }) : ''}
                    </div>
                </div>
            `;
        }

        const definitionPane = document.getElementById('indicatorDetailTabContentDefinition');
        const formulaPane = document.getElementById('indicatorDetailTabContentFormula');
        const targetPane = document.getElementById('indicatorDetailTabContentTarget');
        const narrativePane = document.getElementById('indicatorDetailTabContentNarrative');
        const progressHistoryPane = document.getElementById('indicatorDetailTabContentProgressHistory');
        const resultHistoryPane = document.getElementById('indicatorDetailTabContentResultHistory');

        if (definitionPane) {
            definitionPane.innerHTML = renderIndicatorDefinitionTab(indicator, draftVersion, publishedVersion);
        }
        if (formulaPane) {
            formulaPane.innerHTML = renderIndicatorFormulaTab(draftVersion, publishedVersion);
        }
        if (targetPane) {
            targetPane.innerHTML = renderIndicatorTargetTab(draftVersion, publishedVersion);
        }
        if (narrativePane) {
            narrativePane.innerHTML = renderIndicatorNarrativeTab(draftVersion, publishedVersion, results, progressEntries);
        }
        if (progressHistoryPane) {
            progressHistoryPane.innerHTML = renderIndicatorProgressHistoryTab(progressEntries);
        }
        if (resultHistoryPane) {
            resultHistoryPane.innerHTML = renderIndicatorResultHistoryTab(results);
        }

        setActiveIndicatorTab(state.activeIndicatorTab || 'definition');
    }

    function createDetailButton(label, onClick) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-sm btn-soft-primary';
        button.textContent = label;
        button.addEventListener('click', onClick);
        return button;
    }

    function renderReportsGrid() {
        if (!reportGridContainer || !Grid) {
            return;
        }
        reportGridContainer.innerHTML = '';
        state.reportGrid = new gridjs.Grid({
            columns: [
                {
                    name: 'Report',
                    formatter: (_, row) => {
                        const item = state.reports[row.cells[5].data];
                        const isSelected = state.selectedReportId && item.report && item.report.id === state.selectedReportId;
                        return gridjs.html(`
                            <div>
                                <div class="fw-semibold">${escapeHtml(item.report.name || '-')}</div>
                                <div class="text-muted small">${escapeHtml(item.report.report_key || '-')}</div>
                                ${isSelected ? '<span class="badge bg-primary-subtle text-primary mt-2">Sedang dibaca</span>' : ''}
                            </div>
                        `);
                    },
                },
                'Draft',
                'Published',
                'Mappings',
                {
                    name: 'Aksi',
                    formatter: (_, row) => {
                        const item = state.reports[row.cells[5].data];
                        const isSelected = state.selectedReportId && item.report && item.report.id === state.selectedReportId;
                        return gridjs.h('button', {
                            className: `btn btn-sm ${isSelected ? 'btn-primary' : 'btn-soft-primary'}`,
                            'data-selected': isSelected ? 'true' : 'false',
                            onClick: () => loadReportDetail(item.report.id, { autoOpenFirstMapping: true }),
                        }, isSelected ? 'Dipilih' : 'Detail');
                    },
                },
                { name: '__index', hidden: true },
            ],
            data: state.reports.map((item, index) => [
                '',
                item.draft_version ? `v${item.draft_version.version_number}` : '-',
                item.published_version ? `v${item.published_version.version_number}` : '-',
                item.indicator_mapping_count || 0,
                '',
                index,
            ]),
            search: true,
            sort: true,
            pagination: { limit: 5 },
        }).render(reportGridContainer);
    }

    function renderIndicatorsGrid() {
        if (!indicatorGridContainer || !Grid) {
            return;
        }
        indicatorGridContainer.innerHTML = '';
        state.indicatorGrid = new gridjs.Grid({
            columns: [
                {
                    name: 'Indikator',
                    formatter: (_, row) => {
                        const item = state.indicators[row.cells[6].data];
                        const isSelected = state.selectedIndicatorId && item.indicator && item.indicator.id === state.selectedIndicatorId;
                        return gridjs.html(`
                            <div>
                                <div class="fw-semibold">${escapeHtml(item.indicator.name || '-')}</div>
                                <div class="text-muted small">${escapeHtml(item.indicator.indicator_key || '-')}</div>
                                ${isSelected ? '<span class="badge bg-primary-subtle text-primary mt-2">Sedang dibaca</span>' : ''}
                            </div>
                        `);
                    },
                },
                'Source',
                'Draft',
                'Published',
                'Latest Result',
                {
                    name: 'Aksi',
                    formatter: (_, row) => {
                        const item = state.indicators[row.cells[6].data];
                        const isSelected = state.selectedIndicatorId && item.indicator && item.indicator.id === state.selectedIndicatorId;
                        return gridjs.h('button', {
                            className: `btn btn-sm ${isSelected ? 'btn-primary' : 'btn-soft-primary'}`,
                            'data-selected': isSelected ? 'true' : 'false',
                            onClick: () => loadIndicatorDetail(item.indicator.id, { autoOpenDataset: true }),
                        }, isSelected ? 'Dipilih' : 'Detail');
                    },
                },
                { name: '__index', hidden: true },
            ],
            data: state.indicators.map((item, index) => [
                '',
                item.indicator.source_mode || '-',
                item.draft_version ? `v${item.draft_version.version_number}` : '-',
                item.published_version ? `v${item.published_version.version_number}` : '-',
                item.latest_result ? (item.latest_result.achievement_percentage || item.latest_result.measured_value || '-') : '-',
                '',
                index,
            ]),
            search: true,
            sort: true,
            pagination: { limit: 5 },
        }).render(indicatorGridContainer);
    }

    function renderResultsTable() {
        if (!resultsTableBody) {
            return;
        }
        populateResultFilterControls();
        const filteredResults = getFilteredResults();
        if (!filteredResults.length) {
            resultsTableBody.innerHTML = '<tr><td colspan="8" class="text-muted">Belum ada result yang cocok dengan filter saat ini.</td></tr>';
            return;
        }
        resultsTableBody.innerHTML = filteredResults.map((result) => {
            const isSelected = state.selectedIndicatorVersionId && Number(result.indicator_version_id) === Number(state.selectedIndicatorVersionId);
            return `
                <tr class="${isSelected ? 'table-primary' : ''}" data-result-indicator-version-id="${escapeHtml(result.indicator_version_id || '')}">
                    <td>${escapeHtml(result.indicator_version_id || '-')}</td>
                    <td>${escapeHtml(result.reporting_year || '-')}</td>
                    <td>${escapeHtml(result.completion_status || result.status || '-')}</td>
                    <td>${escapeHtml(result.measured_value || '-')}</td>
                    <td>${escapeHtml(result.target_value || '-')}</td>
                    <td>${escapeHtml(result.achievement_percentage || '-')}</td>
                    <td>${escapeHtml(result.qualitative_summary || result.constraint_notes || '-')}</td>
                    <td><button type="button" class="btn btn-sm ${isSelected ? 'btn-primary' : 'btn-soft-primary'}" data-result-indicator-version-id="${escapeHtml(result.indicator_version_id || '')}">${isSelected ? 'Dipilih' : 'Buka'}</button></td>
                </tr>
            `;
        }).join('');
        wireResultTableActions();
    }

    function renderDatasetRunPreviewTable(rows) {
        if (!rows || !rows.length) {
            return '<div class="text-muted">Preview hasil run belum tersedia.</div>';
        }
        const columns = Array.from(rows.reduce((acc, row) => {
            Object.keys(row || {}).forEach((key) => acc.add(key));
            return acc;
        }, new Set()));
        return `
            <div class="table-responsive">
                <table class="table table-sm align-middle mb-0">
                    <thead>
                        <tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join('')}</tr>
                    </thead>
                    <tbody>
                        ${rows.slice(0, 5).map((row) => `
                            <tr>${columns.map((column) => `<td>${escapeHtml(row[column] ?? '-')}</td>`).join('')}</tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    function renderDatasetDetail(data) {
        if (!datasetDetailPanel) {
            return;
        }
        const dataset = data.dataset || {};
        const publishedVersion = data.published_version || null;
        const draftVersion = data.draft_version || null;
        const versions = data.versions || [];
        const runs = data.runs || [];
        const activeVersion = publishedVersion || draftVersion || null;
        const latestRun = runs[0] || null;
        state.selectedDatasetId = dataset.id || null;
        state.currentDatasetDetail = data;

        populateDatasetFilterControls(latestRun && latestRun.summary_json);
        const filteredDataset = applyDatasetFilters(latestRun && latestRun.summary_json);
        const completion = filteredDataset.completion;
        const topDaerah = filteredDataset.topDaerah;
        const filteredPreviewRows = filteredDataset.filteredRows.slice(0, 5).map((row) => ({
            tanggal: row.tanggal,
            daerah: row.daerah,
            jenis: row.jenis,
            hasil: row.hasil,
            tim_kerja: row.tim_kerja,
            periode: resolvePeriodLabel(row, filteredDataset.filters.metricPeriodMode),
        }));

        const linkedIndicator = state.indicators.find((item) => (item.published_version && dataset.id && item.published_version.dataset_id === dataset.id) || (item.draft_version && dataset.id && item.draft_version.dataset_id === dataset.id));
        datasetDetailPanel.innerHTML = `
            <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                <div>
                    <h5 class="mb-1">${escapeHtml(dataset.name || '-')}</h5>
                    <div class="text-muted small">${escapeHtml(dataset.dataset_key || '-')} • ${escapeHtml(dataset.source_domain || '-')} / ${escapeHtml(dataset.source_type || '-')}</div>
                </div>
                <span class="badge bg-info-subtle text-info">${escapeHtml(dataset.status || '-')}</span>
            </div>
            <p>${escapeHtml(dataset.description || 'Belum ada deskripsi dataset.')}</p>
            <div class="analytics-quick-flow-card mb-3">
                <div class="fw-semibold mb-2">Quick Flow</div>
                <div class="text-muted small mb-3">Lompatan cepat dari dataset ke indikator utama yang memakai dataset ini.</div>
                <div class="d-flex gap-2 flex-wrap">
                    ${linkedIndicator && linkedIndicator.indicator && linkedIndicator.indicator.id ? buildQuickFlowButton('Buka indikator terkait', { 'data-flow-indicator-id': linkedIndicator.indicator.id }) : '<span class="text-muted small">Belum ada indikator terkait.</span>'}
                </div>
            </div>
            <div class="row g-3 mb-3">
                <div class="col-md-3"><div class="border rounded p-3 bg-light-subtle h-100"><div class="text-muted small">Version aktif</div><div class="fw-semibold">${escapeHtml(activeVersion ? `v${activeVersion.version_number}` : '-')}</div><div class="text-muted small mt-2">Primary Source</div><div>${escapeHtml(dataset.primary_source_ref || '-')}</div></div></div>
                <div class="col-md-3"><div class="border rounded p-3 bg-light-subtle h-100"><div class="text-muted small">Rows setelah filter</div><div class="fw-semibold">${escapeHtml(formatNumber(filteredDataset.filteredRows.length || 0))}</div><div class="text-muted small mt-2">Freshness</div><div>${escapeHtml((latestRun && latestRun.freshness_status) || '-')}</div></div></div>
                <div class="col-md-3"><div class="border rounded p-3 bg-light-subtle h-100"><div class="text-muted small">Outcome harmonisasi</div><div class="fw-semibold">${escapeHtml(`${completion.selesai} selesai / ${completion.dikembalikan} dikembalikan`)}</div><div class="text-muted small mt-2">Persentase selesai</div><div>${escapeHtml(`${completion.achievementPercentage}%`)}</div></div></div>
                <div class="col-md-3"><div class="border rounded p-3 bg-light-subtle h-100"><div class="text-muted small">Top daerah</div><div class="fw-semibold">${escapeHtml(topDaerah && topDaerah.length ? `${topDaerah[0].label} (${topDaerah[0].count})` : '-') }</div><div class="text-muted small mt-2">Mode periode</div><div>${escapeHtml(mapMetricPeriodModeLabel(filteredDataset.filters.metricPeriodMode))}</div></div></div>
            </div>
            <div class="row g-3 mb-3">
                <div class="col-md-6"><div class="border rounded p-3 bg-white h-100"><div class="fw-semibold mb-2">Source Contract JSON</div>${formatJsonBlock(activeVersion && activeVersion.source_contract_json, 'Source contract belum tersedia.')}</div></div>
                <div class="col-md-6"><div class="border rounded p-3 bg-white h-100"><div class="fw-semibold mb-2">Query & Transform Spec</div>${formatJsonBlock({ query_spec_json: activeVersion && activeVersion.query_spec_json, transform_spec_json: activeVersion && activeVersion.transform_spec_json }, 'Spec dataset belum tersedia.')}</div></div>
                <div class="col-12"><div class="border rounded p-3 bg-white"><div class="fw-semibold mb-2">Summary JSON Run Terbaru</div>${formatJsonBlock(latestRun && latestRun.summary_json, 'Summary run terbaru belum tersedia.')}</div></div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                            <div>
                                <div class="fw-semibold">Chart Ringan Summary Run</div>
                                <div class="text-muted small">Chart kini sadar filter reporting year / status / jenis serta mode timeseries yang bisa tumbuh dari harian, mingguan, bulanan, triwulan, semester, sampai tahunan.</div>
                            </div>
                        </div>
                        <div class="row g-3">
                            <div class="col-lg-4"><div id="analyticsChartHasilCounts" class="analytics-chart-box"></div></div>
                            <div class="col-lg-4"><div id="analyticsChartJenisCounts" class="analytics-chart-box"></div></div>
                            <div class="col-lg-4"><div id="analyticsChartTimKerjaCounts" class="analytics-chart-box"></div></div>
                            <div class="col-12 col-xl-6"><div id="analyticsChartTopDaerah" class="analytics-chart-box"></div></div>
                            <div class="col-12 col-xl-6"><div id="analyticsChartPeriodMetrics" class="analytics-chart-box"></div></div>
                        </div>
                    </div>
                </div>
                <div class="col-12"><div class="border rounded p-3 bg-white"><div class="fw-semibold mb-2">Preview Result Rows Setelah Filter</div>${renderDatasetRunPreviewTable(filteredPreviewRows)}</div></div>
                <div class="col-md-6"><div class="border rounded p-3 bg-white h-100"><div class="fw-semibold mb-2">Versi Dataset</div><div class="list-group list-group-flush">${versions.length ? versions.map((version) => `
                                <div class="list-group-item px-0">
                                    <div class="d-flex justify-content-between gap-2">
                                        <div>
                                            <div class="fw-medium">v${escapeHtml(version.version_number)}</div>
                                            <div class="text-muted small">${escapeHtml(version.status || '-')} • grain ${escapeHtml(version.grain_key || '-')}</div>
                                        </div>
                                        <span class="badge bg-secondary-subtle text-secondary">${escapeHtml(version.freshness_strategy || '-')}</span>
                                    </div>
                                </div>
                            `).join('') : '<div class="text-muted">Belum ada versi dataset.</div>'}</div></div></div>
                <div class="col-md-6"><div class="border rounded p-3 bg-white h-100"><div class="fw-semibold mb-2">Run History</div><div class="list-group list-group-flush">${runs.length ? runs.slice(0, 5).map((run) => {
                                const tone = resolveRunStatusTone(run.status);
                                return `
                                    <div class="list-group-item px-0">
                                        <div class="d-flex justify-content-between gap-2">
                                            <div>
                                                <div class="fw-medium">${escapeHtml(run.run_key || '-')}</div>
                                                <div class="text-muted small">${escapeHtml(formatDateTime(run.started_at))} → ${escapeHtml(formatDateTime(run.finished_at))}</div>
                                            </div>
                                            <span class="badge bg-${tone.bg}-subtle text-${tone.text}">${escapeHtml(run.status || '-')}</span>
                                        </div>
                                        <div class="text-muted small mt-2">Rows ${escapeHtml(formatNumber(run.result_row_count || 0))} • Materialization ${escapeHtml(run.materialization_ref || '-')}</div>
                                    </div>
                                `;
                            }).join('') : '<div class="text-muted">Belum ada histori run.</div>'}</div></div></div>
            </div>
        `;
        wireQuickFlowActions(datasetDetailPanel);
        renderDatasetSummaryCharts(filteredDataset);
        renderDatasetInsights(filteredDataset);
    }

    function wireQuickFlowActions(scope) {
        (scope || document).querySelectorAll('[data-flow-report-id]').forEach((button) => {
            button.addEventListener('click', () => loadReportDetail(button.getAttribute('data-flow-report-id'), { autoOpenFirstMapping: true }));
        });
        (scope || document).querySelectorAll('[data-flow-indicator-id]').forEach((button) => {
            button.addEventListener('click', () => loadIndicatorDetail(button.getAttribute('data-flow-indicator-id'), { autoOpenDataset: true }));
        });
        (scope || document).querySelectorAll('[data-flow-dataset-id]').forEach((button) => {
            button.addEventListener('click', () => loadDatasetDetail(button.getAttribute('data-flow-dataset-id')));
        });
    }

    function renderDatasetSummaryCharts(filteredDataset) {
        const summary = filteredDataset || {};
        const hasilSeries = toChartSeriesMap(summary.hasilCounts);
        renderPlotlyChart('hasilCounts', '#analyticsChartHasilCounts', [{
            type: 'pie',
            hole: 0.5,
            labels: hasilSeries.map((item) => item.label),
            values: hasilSeries.map((item) => item.count),
            textinfo: 'label+value',
            hovertemplate: '%{label}: %{value}<extra></extra>',
            marker: { colors: ['#0ab39c', '#f06548', '#405189', '#f7b84b', '#299cdb'] },
        }], {
            title: { text: 'Distribusi Hasil', x: 0, xanchor: 'left', font: { size: 14 } },
            height: 260,
            emptyMessage: 'Belum ada data hasil.',
        });

        const jenisSeries = toChartSeriesMap(summary.jenisCounts);
        renderPlotlyChart('jenisCounts', '#analyticsChartJenisCounts', [{
            type: 'bar',
            x: jenisSeries.map((item) => item.label),
            y: jenisSeries.map((item) => item.count),
            text: jenisSeries.map((item) => item.count),
            textposition: 'outside',
            cliponaxis: false,
            hovertemplate: '%{x}: %{y}<extra>Dokumen</extra>',
            marker: { color: '#405189' },
        }], {
            title: { text: 'Distribusi Jenis', x: 0, xanchor: 'left', font: { size: 14 } },
            height: 260,
            showlegend: false,
            xaxis: { automargin: true },
            yaxis: { title: { text: 'Dokumen' }, rangemode: 'tozero' },
            emptyMessage: 'Belum ada data jenis.',
        });

        const timKerjaSeries = toChartSeriesMap(summary.timKerjaCounts);
        renderPlotlyChart('timKerjaCounts', '#analyticsChartTimKerjaCounts', [{
            type: 'scatterpolar',
            r: timKerjaSeries.map((item) => item.count),
            theta: timKerjaSeries.map((item) => item.label),
            fill: 'toself',
            name: 'Dokumen',
            hovertemplate: '%{theta}: %{r}<extra>Dokumen</extra>',
            line: { color: '#0ab39c' },
            marker: { color: '#0ab39c' },
        }], {
            title: { text: 'Sebaran Tim Kerja', x: 0, xanchor: 'left', font: { size: 14 } },
            height: 260,
            polar: { radialaxis: { visible: true, rangemode: 'tozero' } },
            emptyMessage: 'Belum ada data tim kerja.',
        });

        const topDaerahSeries = Array.isArray(summary.topDaerah) ? summary.topDaerah.slice(0, 10) : [];
        renderPlotlyChart('topDaerah', '#analyticsChartTopDaerah', [{
            type: 'bar',
            orientation: 'h',
            x: topDaerahSeries.map((item) => Number(item.count || 0)).reverse(),
            y: topDaerahSeries.map((item) => item.label).reverse(),
            text: topDaerahSeries.map((item) => Number(item.count || 0)).reverse(),
            textposition: 'outside',
            cliponaxis: false,
            hovertemplate: '%{y}: %{x}<extra>Dokumen</extra>',
            marker: { color: '#f7b84b' },
        }], {
            title: { text: 'Top Daerah', x: 0, xanchor: 'left', font: { size: 14 } },
            height: 320,
            showlegend: false,
            margin: { t: 56, r: 32, b: 40, l: 120 },
            xaxis: { title: { text: 'Dokumen' }, rangemode: 'tozero' },
            yaxis: { automargin: true },
            emptyMessage: 'Belum ada data daerah.',
        });

        const periodSeries = Array.isArray(summary.selectedPeriodMetric) ? summary.selectedPeriodMetric : [];
        const periodModeLabel = mapMetricPeriodModeLabel(summary.filters && summary.filters.metricPeriodMode);
        renderPlotlyChart('periodMetrics', '#analyticsChartPeriodMetrics', [
            {
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Total Dokumen',
                x: periodSeries.map((item) => item.label),
                y: periodSeries.map((item) => item.total),
                hovertemplate: '%{x}<br>Total: %{y}<extra></extra>',
                line: { color: '#405189', width: 3 },
            },
            {
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Selesai',
                x: periodSeries.map((item) => item.label),
                y: periodSeries.map((item) => item.selesai),
                hovertemplate: '%{x}<br>Selesai: %{y}<extra></extra>',
                line: { color: '#0ab39c', width: 3 },
            },
            {
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Persentase Selesai',
                x: periodSeries.map((item) => item.label),
                y: periodSeries.map((item) => item.achievement_percentage),
                hovertemplate: '%{x}<br>Selesai: %{y}%<extra></extra>',
                line: { color: '#f06548', width: 4, dash: 'dot' },
                yaxis: 'y2',
            },
        ], {
            title: { text: `Metric Periode (${periodModeLabel})`, x: 0, xanchor: 'left', font: { size: 14 } },
            height: 320,
            hovermode: 'x unified',
            xaxis: { automargin: true },
            yaxis: { title: { text: 'Jumlah Dokumen' }, rangemode: 'tozero' },
            yaxis2: { title: { text: '% Selesai' }, overlaying: 'y', side: 'right', rangemode: 'tozero', ticksuffix: '%' },
            emptyMessage: 'Belum ada data periode.',
        });
    }

    function renderDatasetRunsPanel() {
        if (!datasetRunsList) {
            return;
        }
        if (!state.datasets.length) {
            datasetRunsList.innerHTML = '<div class="text-muted">Belum ada dataset run yang bisa ditampilkan.</div>';
            return;
        }

        datasetRunsList.innerHTML = state.datasets.map((item) => {
            const dataset = item.dataset || {};
            const publishedVersion = item.published_version || item.draft_version || null;
            const latestRun = item.latest_run || null;
            const datasetDetailUrl = (config.analyticsDatasetDetailUrlTemplate || '').replace('__DATASET_ID__', String(dataset.id || ''));
            const datasetRunsUrl = (config.analyticsDatasetRunsUrlTemplate || '').replace('__DATASET_ID__', String(dataset.id || ''));
            const tone = resolveRunStatusTone(latestRun && latestRun.status);
            const isSelected = state.selectedDatasetId && dataset.id === state.selectedDatasetId;
            const completion = latestRun && latestRun.summary_json && latestRun.summary_json.completion;

            return `
                <div class="list-group-item px-0 ${isSelected ? 'border-primary border-2 rounded px-2' : ''}">
                    <div class="d-flex justify-content-between align-items-start gap-2">
                        <div>
                            <div class="fw-semibold">${escapeHtml(dataset.name || '-')}</div>
                            <div class="text-muted small">${escapeHtml(dataset.dataset_key || '-')} • ${escapeHtml(dataset.source_type || '-')}</div>
                        </div>
                        <span class="badge bg-${tone.bg}-subtle text-${tone.text}">${escapeHtml((latestRun && latestRun.status) || 'no-run')}</span>
                    </div>
                    <div class="small text-muted mt-2">
                        Version aktif: ${escapeHtml(publishedVersion ? `v${publishedVersion.version_number}` : '-')}
                        • Rows: ${escapeHtml(formatNumber((latestRun && latestRun.result_row_count) || 0))}
                    </div>
                    <div class="small text-muted mt-1">
                        ${escapeHtml(completion ? `${completion.selesai} selesai • ${completion.dikembalikan} dikembalikan` : 'Belum ada summary completion')}
                    </div>
                    <div class="small text-muted mt-1">
                        Started: ${escapeHtml(formatDateTime((latestRun && latestRun.started_at) || '-'))}
                    </div>
                    <div class="mt-2 d-flex gap-2 flex-wrap">
                        <button class="btn btn-sm btn-soft-primary" type="button" data-dataset-detail-id="${escapeHtml(dataset.id || '')}">Detail Dataset</button>
                        <a class="btn btn-sm btn-soft-secondary" href="${escapeHtml(datasetDetailUrl || '#')}">Dataset API</a>
                        <a class="btn btn-sm btn-soft-secondary" href="${escapeHtml(datasetRunsUrl || '#')}">Run History API</a>
                    </div>
                </div>
            `;
        }).join('');

        datasetRunsList.querySelectorAll('[data-dataset-detail-id]').forEach((button) => {
            button.addEventListener('click', () => loadDatasetDetail(button.getAttribute('data-dataset-detail-id')));
        });
        wireQuickFlowActions(datasetRunsList);
    }

    async function loadReports() {
        const data = await fetchJson(config.analyticsReportsUrl);
        state.reports = data.reports || [];
        renderReportsGrid();
        renderSummaryCards();
    }

    async function loadIndicators() {
        const data = await fetchJson(config.analyticsIndicatorsUrl);
        state.indicators = data.indicators || [];
        renderIndicatorsGrid();
        renderSummaryCards();
    }

    async function loadResults() {
        const data = await fetchJson(config.analyticsResultsUrl);
        state.results = data.results || [];
        renderResultsTable();
        renderSummaryCards();
    }

    async function loadDatasets() {
        const data = await fetchJson(config.analyticsDatasetsUrl);
        state.datasets = data.datasets || [];
        renderDatasetRunsPanel();
        if (!state.selectedDatasetId && state.datasets.length && state.datasets[0].dataset && state.datasets[0].dataset.id) {
            await loadDatasetDetail(state.datasets[0].dataset.id);
        }
    }

    async function loadReportDetail(reportId, options = {}) {
        try {
            const url = config.analyticsReportDetailUrlTemplate.replace('__REPORT_ID__', String(reportId));
            const data = await fetchJson(url);
            renderReportDetail(data);
            wireQuickFlowActions(reportDetailPanel);
            renderReportsGrid();
            if (options.autoOpenFirstMapping) {
                const firstMapping = (data.indicator_mappings || [])[0];
                const indicatorId = firstMapping && firstMapping.indicator_definition && firstMapping.indicator_definition.id;
                if (indicatorId) {
                    await loadIndicatorDetail(indicatorId, { autoOpenDataset: true });
                }
            }
        } catch (error) {
            renderPlaceholder(reportDetailPanel, error.message || 'Gagal memuat detail report.');
        }
    }

    async function loadIndicatorDetail(indicatorId, options = {}) {
        try {
            const url = config.analyticsIndicatorDetailUrlTemplate.replace('__INDICATOR_ID__', String(indicatorId));
            const data = await fetchJson(url);
            state.selectedIndicatorId = data.indicator && data.indicator.id ? data.indicator.id : Number(indicatorId);
            const activeVersion = data.published_version || data.draft_version || {};
            state.selectedIndicatorVersionId = options.selectedIndicatorVersionId || activeVersion.id || null;
            renderIndicatorDetail(data);
            wireQuickFlowActions(indicatorDetailPanel);
            renderIndicatorsGrid();
            renderResultsTable();
            if (options.autoOpenDataset) {
                if (activeVersion.dataset_id) {
                    await loadDatasetDetail(activeVersion.dataset_id);
                }
            }
        } catch (error) {
            renderPlaceholder(indicatorDetailPanel, error.message || 'Gagal memuat detail indikator.');
        }
    }

    async function loadDatasetDetail(datasetId) {
        try {
            const url = config.analyticsDatasetDetailUrlTemplate.replace('__DATASET_ID__', String(datasetId));
            const data = await fetchJson(url);
            renderDatasetDetail(data);
            renderDatasetRunsPanel();
        } catch (error) {
            renderPlaceholder(datasetDetailPanel, error.message || 'Gagal memuat detail dataset.');
        }
    }

    async function bootstrap() {
        renderIndicatorTabNavigation();
        bindAnalyticsFilterControls();
        setActiveIndicatorTab('definition');
        renderPlaceholder(reportDetailPanel, 'Pilih salah satu report untuk melihat detail.');
        renderPlaceholder(indicatorDetailPanel, 'Pilih salah satu indikator untuk melihat ringkasan utama.');
        renderPlaceholder(datasetDetailPanel, 'Pilih salah satu dataset untuk melihat contract dan preview hasil run.');
        renderDatasetRunsPanel();
        try {
            await Promise.all([loadReports(), loadIndicators(), loadResults(), loadDatasets()]);
            if (!state.selectedReportId && state.reports.length && state.reports[0].report && state.reports[0].report.id) {
                await loadReportDetail(state.reports[0].report.id);
            }
            if (!state.selectedIndicatorId && state.indicators.length && state.indicators[0].indicator && state.indicators[0].indicator.id) {
                await loadIndicatorDetail(state.indicators[0].indicator.id, { autoOpenDataset: true });
            }
        } catch (error) {
            renderPlaceholder(reportDetailPanel, error.message || 'Gagal memuat workspace analytics.');
            renderPlaceholder(indicatorDetailPanel, error.message || 'Gagal memuat workspace analytics.');
            renderPlaceholder(datasetDetailPanel, error.message || 'Gagal memuat detail dataset.');
            if (resultsTableBody) {
                resultsTableBody.innerHTML = `<tr><td colspan="8" class="text-danger">${escapeHtml(error.message || 'Gagal memuat data.')}</td></tr>`;
            }
            if (datasetRunsList) {
                datasetRunsList.innerHTML = `<div class="text-danger">${escapeHtml(error.message || 'Gagal memuat dataset runs.')}</div>`;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', bootstrap);
})();
