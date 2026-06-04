(function () {
    const config = window.analyticsWorkspaceConfig || {};
    const Grid = window.gridjs && window.gridjs.Grid;

    const reportGridContainer = document.getElementById('analyticsReportsGrid');
    const indicatorGridContainer = document.getElementById('analyticsIndicatorsGrid');
    const resultsTableBody = document.querySelector('#analyticsResultsTable tbody');
    const reportDetailPanel = document.getElementById('analyticsReportDetailPanel');
    const indicatorDetailPanel = document.getElementById('analyticsIndicatorDetailPanel');
    const indicatorTabNavigation = document.getElementById('indicatorDetailTabNavigation');

    const state = {
        reports: [],
        indicators: [],
        results: [],
        reportGrid: null,
        indicatorGrid: null,
        activeIndicatorTab: 'definition',
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
                <div class="col-12">
                    <div class="border rounded p-3 bg-light-subtle">
                        <div class="fw-semibold mb-2">Meta Description Draft</div>
                        ${buildMetaDescription(draftVersion && draftVersion.meta_description, 'Draft version belum punya meta description.')}
                    </div>
                </div>
                <div class="col-12">
                    <div class="border rounded p-3 bg-light-subtle">
                        <div class="fw-semibold mb-2">Meta Description Published</div>
                        ${buildMetaDescription(publishedVersion && publishedVersion.meta_description, 'Published version belum tersedia atau belum punya meta description.')}
                    </div>
                </div>
            </div>
            <div>
                <div class="fw-semibold mb-2">Indicator Mapping</div>
                <ul class="list-group list-group-flush">
                    ${mappings.length ? mappings.map((item) => `
                        <li class="list-group-item px-0">
                            <div class="fw-medium">${escapeHtml((item.mapping && item.mapping.display_label) || (item.indicator_definition && item.indicator_definition.name) || '-')}</div>
                            <div class="text-muted small">${escapeHtml((item.indicator_definition && item.indicator_definition.indicator_key) || '-')} • section ${escapeHtml((item.mapping && item.mapping.section_key) || '-')}</div>
                        </li>
                    `).join('') : '<li class="list-group-item px-0 text-muted">Belum ada mapping indikator.</li>'}
                </ul>
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
        return `
            <div class="row g-3">
                <div class="col-12">
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
            indicatorDetailPanel.innerHTML = `
                <div class="d-flex justify-content-between align-items-start gap-2 mb-3">
                    <div>
                        <h5 class="mb-1">${escapeHtml(indicator.name || '-')}</h5>
                        <div class="text-muted small">${escapeHtml(indicator.indicator_key || '-')} • ${escapeHtml(indicator.source_mode || '-')}</div>
                    </div>
                    <span class="badge bg-primary-subtle text-primary">${escapeHtml(indicator.status || '-')}</span>
                </div>
                <p class="mb-0">${escapeHtml(indicator.description || 'Belum ada deskripsi indikator.')}</p>
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
                'Report',
                'Draft',
                'Published',
                'Mappings',
                {
                    name: 'Aksi',
                    formatter: (_, row) => {
                        const item = state.reports[row.cells[5].data];
                        return gridjs.h('span', {}, createDetailButton('Detail', () => loadReportDetail(item.report.id)));
                    },
                },
                { name: '__index', hidden: true },
            ],
            data: state.reports.map((item, index) => [
                `${item.report.name || '-'}\n${item.report.report_key || '-'}`,
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
                'Indikator',
                'Source',
                'Draft',
                'Published',
                'Latest Result',
                {
                    name: 'Aksi',
                    formatter: (_, row) => {
                        const item = state.indicators[row.cells[6].data];
                        return gridjs.h('span', {}, createDetailButton('Detail', () => loadIndicatorDetail(item.indicator.id)));
                    },
                },
                { name: '__index', hidden: true },
            ],
            data: state.indicators.map((item, index) => [
                `${item.indicator.name || '-'}\n${item.indicator.indicator_key || '-'}`,
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

    async function loadReportDetail(reportId) {
        try {
            const url = config.analyticsReportDetailUrlTemplate.replace('__REPORT_ID__', String(reportId));
            const data = await fetchJson(url);
            renderReportDetail(data);
        } catch (error) {
            renderPlaceholder(reportDetailPanel, error.message || 'Gagal memuat detail report.');
        }
    }

    async function loadIndicatorDetail(indicatorId) {
        try {
            const url = config.analyticsIndicatorDetailUrlTemplate.replace('__INDICATOR_ID__', String(indicatorId));
            const data = await fetchJson(url);
            renderIndicatorDetail(data);
        } catch (error) {
            renderPlaceholder(indicatorDetailPanel, error.message || 'Gagal memuat detail indikator.');
        }
    }

    async function bootstrap() {
        renderIndicatorTabNavigation();
        setActiveIndicatorTab('definition');
        renderPlaceholder(reportDetailPanel, 'Pilih salah satu report untuk melihat detail.');
        renderPlaceholder(indicatorDetailPanel, 'Pilih salah satu indikator untuk melihat ringkasan utama.');
        try {
            await Promise.all([loadReports(), loadIndicators(), loadResults()]);
        } catch (error) {
            renderPlaceholder(reportDetailPanel, error.message || 'Gagal memuat workspace analytics.');
            renderPlaceholder(indicatorDetailPanel, error.message || 'Gagal memuat workspace analytics.');
            if (resultsTableBody) {
                resultsTableBody.innerHTML = `<tr><td colspan="7" class="text-danger">${escapeHtml(error.message || 'Gagal memuat data.')}</td></tr>`;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', bootstrap);
})();
