(function () {
    const config = window.analyticsWorkspaceConfig || {};
    const Grid = window.gridjs && window.gridjs.Grid;
    const ApexCharts = window.ApexCharts;

    const reportGridContainer = document.getElementById('analyticsReportsGrid');
    const indicatorGridContainer = document.getElementById('analyticsIndicatorsGrid');
    const resultsTableBody = document.querySelector('#analyticsResultsTable tbody');
    const datasetRunsList = document.getElementById('analyticsDatasetRunsList');
    const datasetDetailPanel = document.getElementById('analyticsDatasetDetailPanel');
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
        selectedDatasetId: null,
        charts: {},
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
        if (state.charts[key]) {
            state.charts[key].destroy();
            delete state.charts[key];
        }
    }

    function toChartSeriesMap(value) {
        if (!value || typeof value !== 'object') {
            return [];
        }
        return Object.entries(value).map(([label, count]) => ({ label, count: Number(count || 0) }));
    }

    function renderApexChart(key, selector, options) {
        destroyChart(key);
        const el = document.querySelector(selector);
        if (!el) {
            return;
        }
        if (!ApexCharts) {
            el.innerHTML = '<div class="text-muted">Library chart belum tersedia.</div>';
            return;
        }
        const chart = new ApexCharts(el, options);
        chart.render();
        state.charts[key] = chart;
    }

    function buildQuickFlowButton(label, attrs) {
        const htmlAttrs = Object.entries(attrs || {}).map(([key, value]) => `${key}="${escapeHtml(value)}"`).join(' ');
        return `<button type="button" class="btn btn-sm btn-soft-primary" ${htmlAttrs}>${escapeHtml(label)}</button>`;
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
        if (!state.results.length) {
            resultsTableBody.innerHTML = '<tr><td colspan="7" class="text-muted">Belum ada result yang bisa ditampilkan.</td></tr>';
            return;
        }
        resultsTableBody.innerHTML = state.results.map((result) => `
            <tr>
                <td>${escapeHtml(result.indicator_version_id || '-')}</td>
                <td>${escapeHtml(result.reporting_year || '-')}</td>
                <td>${escapeHtml(result.completion_status || result.status || '-')}</td>
                <td>${escapeHtml(result.measured_value || '-')}</td>
                <td>${escapeHtml(result.target_value || '-')}</td>
                <td>${escapeHtml(result.achievement_percentage || '-')}</td>
                <td>${escapeHtml(result.qualitative_summary || result.constraint_notes || '-')}</td>
            </tr>
        `).join('');
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
        const completion = latestRun && latestRun.summary_json && latestRun.summary_json.completion;
        const topDaerah = latestRun && latestRun.summary_json && latestRun.summary_json.top_daerah;
        state.selectedDatasetId = dataset.id || null;

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
                <div class="col-md-4">
                    <div class="border rounded p-3 bg-light-subtle h-100">
                        <div class="text-muted small">Version aktif</div>
                        <div class="fw-semibold">${escapeHtml(activeVersion ? `v${activeVersion.version_number}` : '-')}</div>
                        <div class="text-muted small mt-2">Primary Source</div>
                        <div>${escapeHtml(dataset.primary_source_ref || '-')}</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="border rounded p-3 bg-light-subtle h-100">
                        <div class="text-muted small">Rows run terbaru</div>
                        <div class="fw-semibold">${escapeHtml(formatNumber((latestRun && latestRun.result_row_count) || 0))}</div>
                        <div class="text-muted small mt-2">Freshness</div>
                        <div>${escapeHtml((latestRun && latestRun.freshness_status) || '-')}</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="border rounded p-3 bg-light-subtle h-100">
                        <div class="text-muted small">Outcome harmonisasi</div>
                        <div class="fw-semibold">${escapeHtml(completion ? `${completion.selesai} selesai / ${completion.dikembalikan} dikembalikan` : '-')}</div>
                        <div class="text-muted small mt-2">Top daerah</div>
                        <div>${escapeHtml(topDaerah && topDaerah.length ? `${topDaerah[0].label} (${topDaerah[0].count})` : '-')}</div>
                    </div>
                </div>
            </div>
            <div class="row g-3 mb-3">
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-white h-100">
                        <div class="fw-semibold mb-2">Source Contract JSON</div>
                        ${formatJsonBlock(activeVersion && activeVersion.source_contract_json, 'Source contract belum tersedia.')}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-white h-100">
                        <div class="fw-semibold mb-2">Query & Transform Spec</div>
                        ${formatJsonBlock({ query_spec_json: activeVersion && activeVersion.query_spec_json, transform_spec_json: activeVersion && activeVersion.transform_spec_json }, 'Spec dataset belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Summary JSON Run Terbaru</div>
                        ${formatJsonBlock(latestRun && latestRun.summary_json, 'Summary run terbaru belum tersedia.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                            <div>
                                <div class="fw-semibold">Chart Ringan Summary Run</div>
                                <div class="text-muted small">Membaca pola hasil, jenis, dan tim kerja langsung dari summary_json tanpa nunggu dashboard final.</div>
                            </div>
                        </div>
                        <div class="row g-3">
                            <div class="col-lg-4"><div id="analyticsChartHasilCounts" class="analytics-chart-box"></div></div>
                            <div class="col-lg-4"><div id="analyticsChartJenisCounts" class="analytics-chart-box"></div></div>
                            <div class="col-lg-4"><div id="analyticsChartTimKerjaCounts" class="analytics-chart-box"></div></div>
                            <div class="col-12"><div id="analyticsChartTopDaerah" class="analytics-chart-box"></div></div>
                        </div>
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-white">
                        <div class="fw-semibold mb-2">Preview Result Rows</div>
                        ${renderDatasetRunPreviewTable(latestRun && latestRun.result_preview_json)}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-white h-100">
                        <div class="fw-semibold mb-2">Versi Dataset</div>
                        <div class="list-group list-group-flush">
                            ${versions.length ? versions.map((version) => `
                                <div class="list-group-item px-0">
                                    <div class="d-flex justify-content-between gap-2">
                                        <div>
                                            <div class="fw-medium">v${escapeHtml(version.version_number)}</div>
                                            <div class="text-muted small">${escapeHtml(version.status || '-')} • grain ${escapeHtml(version.grain_key || '-')}</div>
                                        </div>
                                        <span class="badge bg-secondary-subtle text-secondary">${escapeHtml(version.freshness_strategy || '-')}</span>
                                    </div>
                                </div>
                            `).join('') : '<div class="text-muted">Belum ada versi dataset.</div>'}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="border rounded p-3 bg-white h-100">
                        <div class="fw-semibold mb-2">Run History</div>
                        <div class="list-group list-group-flush">
                            ${runs.length ? runs.slice(0, 5).map((run) => {
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
                            }).join('') : '<div class="text-muted">Belum ada histori run.</div>'}
                        </div>
                    </div>
                </div>
            </div>
        `;
        wireQuickFlowActions(datasetDetailPanel);
        renderDatasetSummaryCharts(latestRun && latestRun.summary_json);
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

    function renderDatasetSummaryCharts(summaryJson) {
        const summary = summaryJson || {};
        renderApexChart('hasilCounts', '#analyticsChartHasilCounts', {
            chart: { type: 'donut', height: 260, toolbar: { show: false } },
            series: toChartSeriesMap(summary.hasil_counts).map((item) => item.count),
            labels: toChartSeriesMap(summary.hasil_counts).map((item) => item.label),
            legend: { position: 'bottom' },
            title: { text: 'Distribusi Hasil', align: 'left', style: { fontSize: '14px' } },
            dataLabels: { enabled: true },
            noData: { text: 'Belum ada data hasil.' },
        });

        const jenisSeries = toChartSeriesMap(summary.jenis_counts);
        renderApexChart('jenisCounts', '#analyticsChartJenisCounts', {
            chart: { type: 'bar', height: 260, toolbar: { show: false } },
            series: [{ name: 'Dokumen', data: jenisSeries.map((item) => item.count) }],
            xaxis: { categories: jenisSeries.map((item) => item.label) },
            plotOptions: { bar: { borderRadius: 4, distributed: true } },
            title: { text: 'Distribusi Jenis', align: 'left', style: { fontSize: '14px' } },
            legend: { show: false },
            noData: { text: 'Belum ada data jenis.' },
        });

        const timKerjaSeries = toChartSeriesMap(summary.tim_kerja_counts);
        renderApexChart('timKerjaCounts', '#analyticsChartTimKerjaCounts', {
            chart: { type: 'radar', height: 260, toolbar: { show: false } },
            series: [{ name: 'Dokumen', data: timKerjaSeries.map((item) => item.count) }],
            xaxis: { categories: timKerjaSeries.map((item) => item.label) },
            title: { text: 'Sebaran Tim Kerja', align: 'left', style: { fontSize: '14px' } },
            noData: { text: 'Belum ada data tim kerja.' },
        });

        const topDaerahSeries = Array.isArray(summary.top_daerah) ? summary.top_daerah.slice(0, 10) : [];
        renderApexChart('topDaerah', '#analyticsChartTopDaerah', {
            chart: { type: 'bar', height: 320, toolbar: { show: false } },
            series: [{ name: 'Dokumen', data: topDaerahSeries.map((item) => Number(item.count || 0)) }],
            xaxis: { categories: topDaerahSeries.map((item) => item.label) },
            plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
            title: { text: 'Top Daerah', align: 'left', style: { fontSize: '14px' } },
            legend: { show: false },
            noData: { text: 'Belum ada data daerah.' },
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
            renderIndicatorDetail(data);
            wireQuickFlowActions(indicatorDetailPanel);
            renderIndicatorsGrid();
            if (options.autoOpenDataset) {
                const activeVersion = data.published_version || data.draft_version || {};
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
                resultsTableBody.innerHTML = `<tr><td colspan="7" class="text-danger">${escapeHtml(error.message || 'Gagal memuat data.')}</td></tr>`;
            }
            if (datasetRunsList) {
                datasetRunsList.innerHTML = `<div class="text-danger">${escapeHtml(error.message || 'Gagal memuat dataset runs.')}</div>`;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', bootstrap);
})();
