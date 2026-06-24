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
    const datasetFilterDateStart = document.getElementById('analyticsDatasetFilterDateStart');
    const datasetFilterDateEnd = document.getElementById('analyticsDatasetFilterDateEnd');
    const datasetDimensionSelect = document.getElementById('analyticsDatasetDimensionSelect');
    const datasetTimeseriesSplit = document.getElementById('analyticsDatasetTimeseriesSplit');
    const datasetMetricPeriodMode = document.getElementById('analyticsDatasetMetricPeriodMode');
    const datasetChartType = document.getElementById('analyticsDatasetChartType');
    const datasetQuickRanges = document.getElementById('analyticsDatasetQuickRanges');
    const chartContainer = document.getElementById('analyticsDatasetChart');
    const dimensionPieChartContainer = document.getElementById('analyticsDatasetDimensionPieChart');
    const dimensionChartsContainer = document.getElementById('analyticsDatasetDimensionCharts');
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
        reportSourceDetails: {},
        reportSourceRuns: {},
        currentFilteredRowsByBlock: {},
        chartRendered: false,
        lastChartType: '',
        map: null,
        mapLayer: null,
        filters: {
            reportingYear: '',
            dateStart: '',
            dateEnd: '',
            dimensionKey: '',
            splitTimeseriesByDimension: true,
            metricPeriodMode: reportConfig.default_period_mode || 'monthly',
            chartType: 'bar',
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

    function getDateFieldKeys(block) {
        const configuredXKey = ((block && block.config) || {}).x_key;
        const curatedDateKeys = getBlockCuratedFields(block)
            .filter(function (field) {
                return field && field.key && (field.role === 'date' || ['date', 'datetime', 'day'].includes(String(field.type || '').toLowerCase()));
            })
            .map(function (field) { return field.key; });
        return [configuredXKey]
            .concat(curatedDateKeys)
            .concat(['tanggal', 'period_date', 'submitted_at', 'created_at'])
            .filter(Boolean);
    }

    function resolveRowDate(row, block) {
        const dateKeys = getDateFieldKeys(block);
        const rawCandidate = dateKeys.find(function (key) {
            return row && row[key] !== null && row[key] !== undefined && row[key] !== '';
        });
        const rawValue = rawCandidate && row
            ? String(row[rawCandidate]).slice(0, 10)
            : '';
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
        } else if (presetKey === 'quarter_1') {
            start.setMonth(0, 1);
            end.setMonth(2, 31);
        } else if (presetKey === 'quarter_2') {
            start.setMonth(3, 1);
            end.setMonth(5, 30);
        } else if (presetKey === 'quarter_3') {
            start.setMonth(6, 1);
            end.setMonth(8, 30);
        } else if (presetKey === 'quarter_4') {
            start.setMonth(9, 1);
            end.setMonth(11, 31);
        } else if (presetKey === 'current_semester') {
            start.setMonth(today.getMonth() < 6 ? 0 : 6, 1);
        } else if (presetKey === 'semester_1') {
            start.setMonth(0, 1);
            end.setMonth(5, 30);
        } else if (presetKey === 'semester_2') {
            start.setMonth(6, 1);
            end.setMonth(11, 31);
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

    function getDimensionFilterFields() {
        const dimensionBlock = getReportBlock('dimension_pie') || getReportBlock('dimension_distribution') || getReportBlock('plotly_timeseries');
        return resolveDimensionChartFields(dimensionBlock);
    }

    function populateDimensionFilterOptions() {
        if (!datasetDimensionSelect) {
            return;
        }
        const fields = getDimensionFilterFields();
        const optionHtml = ['<option value="">Semua Dimensi</option>'].concat(
            fields.map(function (field) {
                const selectedAttr = String(field.key) === String(state.filters.dimensionKey || '') ? ' selected' : '';
                return `<option value="${escapeHtml(field.key)}"${selectedAttr}>${escapeHtml(field.label || field.key)}</option>`;
            })
        );
        datasetDimensionSelect.innerHTML = optionHtml.join('');
        if (state.filters.dimensionKey && !fields.some(function (field) { return field.key === state.filters.dimensionKey; })) {
            state.filters.dimensionKey = '';
            datasetDimensionSelect.value = '';
        }
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

    function getOrderedReportBlocks() {
        return Array.isArray(reportConfig.blocks)
            ? reportConfig.blocks.slice().sort(function (left, right) {
                return Number((left && left.order) || 9999) - Number((right && right.order) || 9999);
            })
            : [];
    }

    function getReportDataSources() {
        return Array.isArray(reportConfig.data_sources) ? reportConfig.data_sources : [];
    }

    function getBlockConfig(blockType) {
        const block = getOrderedReportBlocks().find(function (item) {
            return item && item.type === blockType;
        });
        return (block && block.config) || {};
    }

    function getReportBlock(blockType) {
        return getOrderedReportBlocks().find(function (item) {
            return item && item.type === blockType;
        }) || null;
    }

    function getBlockDataSource(block) {
        const sources = getReportDataSources();
        const blockConfig = (block && block.config) || {};
        const sourceAlias = block && (block.data_source_alias || block.source_alias || blockConfig.data_source_alias);
        if (sourceAlias) {
            const matchedSource = sources.find(function (source) {
                return source && source.alias === sourceAlias;
            });
            if (matchedSource) {
                return matchedSource;
            }
        }
        return sources[0] || null;
    }

    function getCuratedFields() {
        const datasetContract = reportConfig.dataset_contract || {};
        return Array.isArray(datasetContract.curated_fields) ? datasetContract.curated_fields : [];
    }

    function getRowsFromRuns(runs) {
        const successfulRun = (runs || []).find((run) => run.status === 'succeeded') || (runs || [])[0] || null;
        const summaryJson = (successfulRun && successfulRun.summary_json) || {};
        return Array.isArray(summaryJson.row_snapshots) ? summaryJson.row_snapshots : [];
    }

    function getRowsForBlock(block, fallbackRows) {
        const source = getBlockDataSource(block);
        const datasetId = source && source.dataset_id;
        if (datasetId && state.reportSourceRuns[String(datasetId)]) {
            return getRowsFromRuns(state.reportSourceRuns[String(datasetId)]);
        }
        return Array.isArray(fallbackRows) ? fallbackRows : [];
    }

    function filterRowsForBlock(block, fallbackRows) {
        return applyDatasetFilters(getRowsForBlock(block, fallbackRows));
    }

    function getBlockCuratedFields(block) {
        const source = getBlockDataSource(block);
        if (source && Array.isArray(source.curated_fields) && source.curated_fields.length) {
            return source.curated_fields;
        }
        return getCuratedFields();
    }

    function getFieldLabelMap(block) {
        return getBlockCuratedFields(block).reduce(function (acc, field) {
            if (field && field.key) {
                acc[field.key] = field.label || field.key;
            }
            return acc;
        }, {});
    }

    function resolveConfiguredFieldKeys(block, requestedKeys, fallbackKeys) {
        const curatedFieldKeys = getBlockCuratedFields(block).map(function (field) {
            return field.key;
        }).filter(Boolean);
        const allowlist = curatedFieldKeys.length ? new Set(curatedFieldKeys) : null;
        const requested = Array.isArray(requestedKeys) ? requestedKeys.filter(Boolean) : [];
        const selected = requested.filter(function (key) {
            return !allowlist || allowlist.has(key);
        });
        if (selected.length) {
            return selected;
        }
        return (Array.isArray(fallbackKeys) ? fallbackKeys : []).filter(function (key) {
            return !allowlist || allowlist.has(key);
        });
    }

    function resolveConfiguredSeries(block, fallbackKeys) {
        const config = (block && block.config) || getBlockConfig('plotly_timeseries');
        const requestedSeries = Array.isArray(config.series) ? config.series : [];
        const curatedFieldKeys = new Set(getBlockCuratedFields(block).map(function (field) {
            return field.key;
        }).filter(Boolean));
        const normalized = requestedSeries.filter(function (series) {
            return series && series.key && (!curatedFieldKeys.size || curatedFieldKeys.has(series.key));
        }).map(function (series) {
            return {
                key: series.key,
                label: series.label || series.key,
                aggregation: series.aggregation || 'sum',
            };
        });
        if (normalized.length) {
            return normalized;
        }
        return (fallbackKeys || []).map(function (key) {
            return { key, label: key, aggregation: 'sum' };
        }).filter(function (series) {
            return series.key === 'total' || !curatedFieldKeys.size || curatedFieldKeys.has(series.key);
        });
    }

    function resolveChartXKey(block, rows, configuredXKey) {
        const availableKeys = new Set();
        (rows || []).forEach(function (row) {
            Object.keys(row || {}).forEach(function (key) {
                if (row[key] !== null && row[key] !== undefined && row[key] !== '') {
                    availableKeys.add(key);
                }
            });
        });
        if (configuredXKey && availableKeys.has(configuredXKey)) {
            return configuredXKey;
        }

        const categoricalField = getBlockCuratedFields(block).find(function (field) {
            return field && field.key && availableKeys.has(field.key) && !['metric', 'date', 'geo_latitude', 'geo_longitude'].includes(field.role);
        });
        if (categoricalField) {
            return categoricalField.key;
        }

        return ['status_realisasi', 'hasil', 'status', 'jenis', 'nama_indikator', 'judul_kegiatan', 'daerah', 'reporting_year'].find(function (key) {
            return availableKeys.has(key);
        }) || '';
    }

    function summarizeFieldMetric(rows, key) {
        if (key === 'total') {
            return rows.length;
        }
        const rawValues = rows.map(function (row) {
            return row && row[key];
        }).filter(function (value) {
            return value !== null && value !== undefined && value !== '';
        });
        const numericValues = rawValues.map(function (value) {
            return Number(value);
        }).filter(function (value) {
            return !Number.isNaN(value);
        });
        if (!numericValues.length) {
            return rawValues.length ? rawValues.length : null;
        }
        const normalizedKey = String(key || '').toLowerCase();
        if (normalizedKey.includes('pct') || normalizedKey.includes('percent') || normalizedKey.includes('achievement')) {
            return numericValues.reduce(function (acc, value) { return acc + value; }, 0) / numericValues.length;
        }
        return numericValues.reduce(function (acc, value) { return acc + value; }, 0);
    }

    function formatMetricValue(key, value) {
        if (value === null || value === undefined) {
            return '-';
        }
        const normalizedKey = String(key || '').toLowerCase();
        if (normalizedKey.includes('pct') || normalizedKey.includes('percent') || normalizedKey.includes('achievement')) {
            return formatPercent(value);
        }
        return formatNumber(value);
    }

    function resolveRowDisplayValue(row, key) {
        const value = row && row[key];
        if (value === null || value === undefined || value === '') {
            return '-';
        }
        return value;
    }

    function renderMetricCards(rows, summaryJson) {
        if (!datasetMetricCards) {
            return;
        }
        const yearSummary = state.filters.reportingYear || ((summaryJson && summaryJson.filter_dimensions && summaryJson.filter_dimensions.reporting_years || []).join(', ') || 'Semua tahun');
        const metricBlock = getReportBlock('metric_cards');
        const metricConfig = (metricBlock && metricBlock.config) || {};
        const configuredMetricKeys = resolveConfiguredFieldKeys(
            metricBlock,
            metricConfig.metric_keys,
            ['total', 'selesai', 'dikembalikan', 'achievement_pct']
        );
        const fieldLabels = getFieldLabelMap(metricBlock);
        const metricCards = configuredMetricKeys.map(function (key) {
            if (key === 'selesai') {
                const value = rows.filter((row) => String(row.hasil || '').toLowerCase() === 'selesai').length;
                return buildMetricCard(fieldLabels[key] || 'Selesai', formatNumber(value), 'Jumlah status selesai setelah filter diterapkan.', 'text-success');
            }
            if (key === 'dikembalikan') {
                const value = rows.filter((row) => String(row.hasil || '').toLowerCase() === 'dikembalikan').length;
                return buildMetricCard(fieldLabels[key] || 'Dikembalikan', formatNumber(value), 'Jumlah status dikembalikan setelah filter diterapkan.', 'text-danger');
            }
            if (key === 'achievement_pct') {
                const metricValue = summarizeFieldMetric(rows, key);
                const fallbackValue = rows.length ? (rows.filter((row) => String(row.hasil || '').toLowerCase() === 'selesai').length / rows.length) * 100 : 0;
                return buildMetricCard(fieldLabels[key] || 'Achievement', formatMetricValue(key, metricValue === null ? fallbackValue : metricValue), `Snapshot aktif untuk ${yearSummary}.`, 'text-primary');
            }
            const metricValue = summarizeFieldMetric(rows, key);
            return buildMetricCard(fieldLabels[key] || key, formatMetricValue(key, metricValue), `Snapshot aktif untuk ${yearSummary}.`, '');
        });

        datasetMetricCards.innerHTML = metricCards.length
            ? metricCards.join('')
            : '<div class="col-12"><div class="alert alert-light border mb-0">Belum ada metric terkonfigurasi pada block metric_cards.</div></div>';
    }

    function renderDatasetSummary(dataset, activeVersion, latestRun, filteredRows) {
        if (!datasetDetailSummary) {
            return;
        }
        if (!dataset) {
            datasetDetailSummary.innerHTML = '<div class="text-muted">Pilih dataset untuk melihat ringkasan.</div>';
            return;
        }
        const reportFamilyLabel = (((config.reportViewerOptions || {}).report_family_labels || {})[reportConfig.report_family]) || reportConfig.report_family || 'Custom / Fleksibel';
        const selectedIndicatorCount = Number(reportConfig.selected_indicator_count || 0);
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
                            <tr><th class="text-muted">Family Report</th><td>${escapeHtml(reportFamilyLabel)}</td></tr>
                            <tr><th class="text-muted">Item Dinamis</th><td>${escapeHtml(formatNumber(selectedIndicatorCount))} item indikator/field terpilih</td></tr>
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

        const tableBlock = getReportBlock('detail_table');
        const tableConfig = (tableBlock && tableBlock.config) || {};
        const configuredColumns = resolveConfiguredFieldKeys(
            tableBlock,
            tableConfig.column_keys,
            ['tanggal', 'daerah', 'jenis', 'hasil', 'reporting_year']
        );
        const fieldLabels = getFieldLabelMap(tableBlock);
        const previewRows = rows;
        detailTableContainer.innerHTML = `
            <table class="table table-sm align-middle mb-0">
                <thead>
                    <tr>
                        ${configuredColumns.map(function (columnKey) {
                            return `<th>${escapeHtml(fieldLabels[columnKey] || columnKey)}</th>`;
                        }).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${previewRows.map(function (row) {
                        return `
                            <tr>
                                ${configuredColumns.map(function (columnKey) {
                                    return `<td>${escapeHtml(resolveRowDisplayValue(row, columnKey))}</td>`;
                                }).join('')}
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
            <div class="text-muted fs-12 mt-3">Menampilkan semua ${escapeHtml(formatNumber(rows.length))} baris aktif hasil run/filter.</div>
        `;
    }

    function resolveTableExportRows() {
        const rows = state.currentFilteredRowsByBlock.detail_table || [];
        return Array.isArray(rows) ? rows : [];
    }

    function resolveTableExportColumns(rows) {
        const tableBlock = getReportBlock('detail_table');
        const tableConfig = (tableBlock && tableBlock.config) || {};
        const configuredColumns = resolveConfiguredFieldKeys(
            tableBlock,
            tableConfig.column_keys,
            ['tanggal', 'daerah', 'jenis', 'hasil', 'reporting_year']
        );
        if (configuredColumns.length) {
            return configuredColumns;
        }
        const discovered = new Set();
        rows.forEach(function (row) {
            Object.keys(row || {}).forEach(function (key) {
                discovered.add(key);
            });
        });
        return Array.from(discovered);
    }

    function downloadBlob(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    function serializeCsvCell(value) {
        const normalized = value === null || value === undefined ? '' : String(value);
        return `"${normalized.replaceAll('"', '""')}"`;
    }

    function exportDetailRows(format) {
        const rows = resolveTableExportRows();
        const columns = resolveTableExportColumns(rows);
        const datasetName = state.currentDatasetDetail && state.currentDatasetDetail.dataset
            ? (state.currentDatasetDetail.dataset.dataset_key || state.currentDatasetDetail.dataset.id || 'dataset')
            : 'dataset';
        const timestamp = new Date().toISOString().slice(0, 10);
        if (format === 'json') {
            downloadBlob(
                `${datasetName}-filtered-rows-${timestamp}.json`,
                JSON.stringify({ columns, rows }, null, 2),
                'application/json;charset=utf-8'
            );
            return;
        }
        if (format === 'xlsx') {
            if (window.XLSX) {
                const exportRows = rows.map(function (row) {
                    return columns.reduce(function (acc, column) {
                        acc[column] = resolveRowDisplayValue(row, column);
                        return acc;
                    }, {});
                });
                const worksheet = window.XLSX.utils.json_to_sheet(exportRows, { header: columns });
                const workbook = window.XLSX.utils.book_new();
                window.XLSX.utils.book_append_sheet(workbook, worksheet, 'Dataset Run');
                window.XLSX.writeFile(workbook, `${datasetName}-filtered-rows-${timestamp}.xlsx`);
                return;
            }
            const tsv = [
                columns.join('\t'),
                ...rows.map(function (row) {
                    return columns.map(function (column) {
                        return String(resolveRowDisplayValue(row, column)).replaceAll('\t', ' ');
                    }).join('\t');
                }),
            ].join('\n');
            downloadBlob(`${datasetName}-filtered-rows-${timestamp}.xls`, tsv, 'application/vnd.ms-excel;charset=utf-8');
            return;
        }
        const csv = [
            columns.map(serializeCsvCell).join(','),
            ...rows.map(function (row) {
                return columns.map(function (column) {
                    return serializeCsvCell(resolveRowDisplayValue(row, column));
                }).join(',');
            }),
        ].join('\n');
        downloadBlob(`${datasetName}-filtered-rows-${timestamp}.csv`, csv, 'text/csv;charset=utf-8');
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
        const narrativeBlock = getReportBlock('narrative');
        const narrativeConfig = (narrativeBlock && narrativeBlock.config) || getBlockConfig('narrative');
        const focusFieldKeys = resolveConfiguredFieldKeys(narrativeBlock, narrativeConfig.focus_field_keys, ['achievement_pct', 'total']);
        const fieldLabels = getFieldLabelMap(narrativeBlock);
        const focusSummary = focusFieldKeys.map(function (key) {
            const resolvedValue = key === 'achievement_pct'
                ? achievement
                : key === 'total'
                    ? total
                    : summarizeFieldMetric(rows, key);
            return `<li><strong>${escapeHtml(fieldLabels[key] || key)}</strong>: ${escapeHtml(formatMetricValue(key, resolvedValue))}</li>`;
        }).join('');

        narrativeContainer.innerHTML = `
            <div class="alert alert-warning-subtle border border-warning-subtle mb-0">${escapeHtml(intro)}</div>
            <div>
                <div class="fw-semibold mb-1">Ringkasan Otomatis Viewer</div>
                <p class="mb-0 text-muted">Pada mode ${escapeHtml(activeMode)}, viewer membaca ${escapeHtml(formatNumber(total))} baris untuk ${escapeHtml(activeYear)} dengan ${escapeHtml(formatNumber(selesai))} status selesai dan ${escapeHtml(formatNumber(dikembalikan))} status dikembalikan. Achievement saat ini berada di ${escapeHtml(formatPercent(achievement))} untuk rentang ${escapeHtml(rangeText)}.</p>
            </div>
            <div>
                <div class="fw-semibold mb-1">Fokus Field Builder</div>
                <ul class="mb-0 text-muted ps-3">${focusSummary || '<li>Tidak ada field fokus terkonfigurasi.</li>'}</ul>
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

    function aggregateRows(rows, periodMode, xKey, seriesConfig, block) {
        const bucketMap = new Map();
        rows.forEach(function (row, rowIndex) {
            const date = resolveRowDate(row, block);
            const rawXValue = xKey ? row[xKey] : null;
            const dateFieldKeys = getDateFieldKeys(block);
            const shouldBucketByDate = Boolean(date && xKey && dateFieldKeys.includes(xKey));
            let label = shouldBucketByDate ? '' : (rawXValue || row.tanggal || row.period_date || row.submitted_at || `Baris ${rowIndex + 1}`);
            if ((!rawXValue || shouldBucketByDate) && date) {
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
            }

            const current = bucketMap.get(label) || { label, sortValue: date ? date.getTime() : bucketMap.size, values: {} };
            (seriesConfig || []).forEach(function (seriesItem) {
                const key = seriesItem.key;
                let value = 0;
                if (key === 'total') {
                    value = 1;
                } else if (key === 'selesai') {
                    value = String(row.hasil || '').toLowerCase() === 'selesai' ? 1 : 0;
                } else if (key === 'dikembalikan') {
                    value = String(row.hasil || '').toLowerCase() === 'dikembalikan' ? 1 : 0;
                } else {
                    const rawValue = row && row[key];
                    const numeric = Number(rawValue);
                    value = Number.isNaN(numeric)
                        ? (rawValue === null || rawValue === undefined || rawValue === '' ? 0 : 1)
                        : numeric;
                }
                current.values[key] = (current.values[key] || 0) + value;
            });
            current.sortValue = date ? Math.min(current.sortValue, date.getTime()) : current.sortValue;
            bucketMap.set(label, current);
        });

        return Array.from(bucketMap.values()).sort(function (left, right) {
            return left.sortValue - right.sortValue;
        });
    }

    function aggregateRowsByPeriodAndDimension(rows, periodMode, xKey, dimensionKey, block) {
        const bucketMap = new Map();
        rows.forEach(function (row, rowIndex) {
            const date = resolveRowDate(row, block);
            const rawXValue = xKey ? row[xKey] : null;
            const dateFieldKeys = getDateFieldKeys(block);
            const shouldBucketByDate = Boolean(date && xKey && dateFieldKeys.includes(xKey));
            let label = shouldBucketByDate ? '' : (rawXValue || row.tanggal || row.period_date || row.submitted_at || `Baris ${rowIndex + 1}`);
            if ((!rawXValue || shouldBucketByDate) && date) {
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
                } else if (periodMode === 'semesterly' || periodMode === 'semester') {
                    label = row.semester_label || `${date.getFullYear()}-S${date.getMonth() < 6 ? 1 : 2}`;
                } else if (periodMode === 'yearly') {
                    label = String(date.getFullYear());
                }
            }

            const rawDimensionValue = row && row[dimensionKey];
            const dimensionValues = Array.isArray(rawDimensionValue) ? rawDimensionValue : [rawDimensionValue];
            dimensionValues.forEach(function (dimensionValue) {
                const dimensionLabel = dimensionValue === null || dimensionValue === undefined || dimensionValue === '' ? '(Kosong)' : String(dimensionValue);
                const bucketKey = `${label}|||${dimensionLabel}`;
                const current = bucketMap.get(bucketKey) || { label, dimensionLabel, sortValue: date ? date.getTime() : bucketMap.size, value: 0 };
                current.value += 1;
                current.sortValue = date ? Math.min(current.sortValue, date.getTime()) : current.sortValue;
                bucketMap.set(bucketKey, current);
            });
        });
        const buckets = Array.from(bucketMap.values()).sort(function (left, right) {
            return left.sortValue - right.sortValue || left.dimensionLabel.localeCompare(right.dimensionLabel);
        });
        return {
            buckets,
            periodLabels: Array.from(new Set(buckets.map(function (bucket) { return bucket.label; }))),
            dimensionLabels: Array.from(new Set(buckets.map(function (bucket) { return bucket.dimensionLabel; }))),
        };
    }

    function renderChart(rows) {
        if (!chartContainer || !Plotly) {
            return;
        }
        const chartBlock = getReportBlock('plotly_timeseries');
        const chartConfig = (chartBlock && chartBlock.config) || getBlockConfig('plotly_timeseries');
        const fallbackSeriesKeys = ['total', 'selesai', 'dikembalikan'];
        const configuredSeries = resolveConfiguredSeries(chartBlock, fallbackSeriesKeys);
        const xKey = resolveChartXKey(chartBlock, rows, chartConfig.x_key || 'tanggal');
        const activeDimensionKey = state.filters.dimensionKey || '';
        const shouldSplitByDimension = Boolean(activeDimensionKey && state.filters.splitTimeseriesByDimension);
        const series = shouldSplitByDimension
            ? []
            : aggregateRows(rows, state.filters.metricPeriodMode || 'monthly', xKey, configuredSeries, chartBlock);
        const dimensionSeries = shouldSplitByDimension
            ? aggregateRowsByPeriodAndDimension(rows, state.filters.metricPeriodMode || 'monthly', xKey, activeDimensionKey, chartBlock)
            : null;
        if (!series.length && (!dimensionSeries || !dimensionSeries.buckets.length)) {
            Plotly.react(chartContainer, [], {
                title: 'Belum ada data pada filter aktif',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
            }, { responsive: true });
            return;
        }

        const palette = ['#405189', '#0ab39c', '#f06548', '#f7b84b'];
        const chartType = state.filters.chartType || 'bar';
        if (state.lastChartType && state.lastChartType !== chartType && Plotly.purge) {
            Plotly.purge(chartContainer);
        }
        state.lastChartType = chartType;
        let traces = [];
        if (dimensionSeries && dimensionSeries.buckets.length) {
            const bucketLookup = dimensionSeries.buckets.reduce(function (acc, bucket) {
                acc[`${bucket.label}|||${bucket.dimensionLabel}`] = bucket.value;
                return acc;
            }, {});
            traces = dimensionSeries.dimensionLabels.slice(0, 20).map(function (dimensionLabel, index) {
                return {
                    x: dimensionSeries.periodLabels,
                    y: dimensionSeries.periodLabels.map(function (periodLabel) {
                        return bucketLookup[`${periodLabel}|||${dimensionLabel}`] || 0;
                    }),
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: dimensionLabel,
                    line: { color: palette[index % palette.length], width: 3 },
                    marker: { color: palette[index % palette.length], opacity: 0.85 },
                };
            });
        } else if (chartType === 'pie') {
            const firstSeries = configuredSeries[0] || { key: 'total', label: 'Total' };
            traces = [{
                labels: series.map((item) => item.label),
                values: series.map((item) => item.values[firstSeries.key] || 0),
                type: 'pie',
                name: firstSeries.label || firstSeries.key,
                marker: { colors: palette },
                textinfo: 'label+percent',
            }];
        } else {
            traces = configuredSeries.map(function (seriesItem, index) {
                const isLine = chartType === 'line';
                const isScatter = chartType === 'scatter';
                return {
                    x: series.map((item) => item.label),
                    y: series.map((item) => item.values[seriesItem.key] || 0),
                    type: isLine || isScatter ? 'scatter' : 'bar',
                    mode: isLine ? 'lines+markers' : isScatter ? 'markers' : undefined,
                    name: seriesItem.label || seriesItem.key,
                    line: isLine ? { color: palette[index % palette.length], width: 3 } : undefined,
                    marker: { color: palette[index % palette.length], opacity: 0.8, size: isScatter ? 10 : undefined },
                };
            });
        }

        const layout = {
            margin: { l: 48, r: 20, t: 20, b: 48 },
            legend: { orientation: 'h' },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
        };
        if (chartType !== 'pie' || dimensionSeries) {
            layout.barmode = 'group';
            layout.xaxis = { title: xKey || 'Kategori/Periode' };
            layout.yaxis = { title: dimensionSeries ? 'Jumlah Record' : 'Nilai' };
        }

        Plotly.react(chartContainer, traces, layout, {
            responsive: true,
            displayModeBar: false,
        });
    }

    function isDimensionChartField(field) {
        if (!field || !field.key) {
            return false;
        }
        const normalizedType = String(field.type || '').toLowerCase();
        return field.role === 'dimension' || ['select', 'radio', 'checkbox', 'selectboxes', 'string', 'text'].includes(normalizedType);
    }

    function resolveDimensionChartFields(block) {
        const config = (block && block.config) || getBlockConfig('dimension_distribution');
        const requestedKeys = Array.isArray(config.dimension_keys) ? config.dimension_keys.filter(Boolean) : [];
        const fields = getBlockCuratedFields(block).filter(isDimensionChartField);
        const requested = requestedKeys.length
            ? requestedKeys.map(function (key) {
                return fields.find(function (field) { return field.key === key; }) || { key, label: key.replaceAll('_', ' ').replace(/\b\w/g, function (char) { return char.toUpperCase(); }), role: 'dimension', type: 'string' };
            })
            : fields;
        return requested.filter(function (field, index, array) {
            return field && field.key && array.findIndex(function (item) { return item && item.key === field.key; }) === index;
        });
    }

    function summarizeDimensionValues(rows, fieldKey, topN) {
        const bucketMap = new Map();
        rows.forEach(function (row) {
            const rawValue = row && row[fieldKey];
            const values = Array.isArray(rawValue) ? rawValue : [rawValue];
            values.forEach(function (value) {
                const label = value === null || value === undefined || value === '' ? '(Kosong)' : String(value);
                bucketMap.set(label, (bucketMap.get(label) || 0) + 1);
            });
        });
        return Array.from(bucketMap.entries())
            .map(function (entry) { return { label: entry[0], value: entry[1] }; })
            .sort(function (left, right) { return right.value - left.value || left.label.localeCompare(right.label); })
            .slice(0, topN || 20);
    }

    function resolveActiveDimensionField(block) {
        const fields = resolveDimensionChartFields(block);
        if (state.filters.dimensionKey) {
            const selected = fields.find(function (field) { return field.key === state.filters.dimensionKey; });
            if (selected) {
                return selected;
            }
        }
        return fields[0] || null;
    }

    function renderDimensionPieChart(rows) {
        if (!dimensionPieChartContainer || !Plotly) {
            return;
        }
        const pieBlock = getReportBlock('dimension_pie') || getReportBlock('dimension_distribution');
        const field = resolveActiveDimensionField(pieBlock);
        const config = (pieBlock && pieBlock.config) || getBlockConfig('dimension_pie') || getBlockConfig('dimension_distribution');
        const topN = Number(config.top_n || 20);
        if (!field) {
            Plotly.react(dimensionPieChartContainer, [], {
                title: 'Belum ada field dimensi/select yang dipilih pada dataset ini.',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
            }, { responsive: true, displayModeBar: false });
            return;
        }
        const buckets = summarizeDimensionValues(rows, field.key, topN);
        if (!buckets.length) {
            Plotly.react(dimensionPieChartContainer, [], {
                title: 'Belum ada data pada filter aktif',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
            }, { responsive: true, displayModeBar: false });
            return;
        }
        Plotly.react(dimensionPieChartContainer, [{
            labels: buckets.map(function (bucket) { return bucket.label; }),
            values: buckets.map(function (bucket) { return bucket.value; }),
            type: 'pie',
            hole: 0.48,
            name: field.label || field.key,
            textinfo: 'label+percent',
            hovertemplate: '%{label}<br>Jumlah: %{value}<br>Persentase: %{percent}<extra></extra>',
        }], {
            margin: { l: 20, r: 20, t: 16, b: 20 },
            legend: { orientation: 'h' },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
        }, {
            responsive: true,
            displayModeBar: false,
        });
    }

    function renderDimensionCharts(rows) {
        if (!dimensionChartsContainer || !Plotly) {
            return;
        }
        const dimensionBlock = getReportBlock('dimension_distribution');
        const dimensionFields = resolveDimensionChartFields(dimensionBlock).filter(function (field) {
            return !state.filters.dimensionKey || field.key === state.filters.dimensionKey;
        });
        const config = (dimensionBlock && dimensionBlock.config) || getBlockConfig('dimension_distribution');
        const topN = Number(config.top_n || 20);

        if (!dimensionFields.length) {
            dimensionChartsContainer.innerHTML = '<div class="col-12"><div class="alert alert-light border mb-0">Belum ada field dimensi/select yang dipilih pada dataset ini.</div></div>';
            return;
        }

        dimensionChartsContainer.innerHTML = dimensionFields.map(function (field, index) {
            return `
                <div class="col-12 col-xl-6">
                    <div class="border rounded p-3 h-100">
                        <div class="d-flex justify-content-between gap-2 align-items-start mb-2">
                            <div>
                                <div class="fw-semibold">${escapeHtml(field.label || field.key)}</div>
                                <div class="text-muted fs-12"><code>${escapeHtml(field.key)}</code> · ${escapeHtml(field.type || 'dimension')}</div>
                            </div>
                            <span class="badge bg-soft-primary text-primary">Dimensi</span>
                        </div>
                        <div id="analyticsDatasetDimensionChart${index}" class="analytics-chart-box"></div>
                    </div>
                </div>
            `;
        }).join('');

        dimensionFields.forEach(function (field, index) {
            const target = document.getElementById(`analyticsDatasetDimensionChart${index}`);
            if (!target) {
                return;
            }
            const buckets = summarizeDimensionValues(rows, field.key, topN);
            if (!buckets.length) {
                Plotly.react(target, [], {
                    title: 'Belum ada data pada filter aktif',
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: 'transparent',
                }, { responsive: true, displayModeBar: false });
                return;
            }
            Plotly.react(target, [{
                x: buckets.map(function (bucket) { return bucket.label; }),
                y: buckets.map(function (bucket) { return bucket.value; }),
                type: 'bar',
                marker: { color: '#405189', opacity: 0.85 },
                hovertemplate: '%{x}<br>Jumlah: %{y}<extra></extra>',
            }], {
                margin: { l: 48, r: 20, t: 12, b: 96 },
                xaxis: { title: field.label || field.key, automargin: true },
                yaxis: { title: 'Jumlah Record' },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
            }, {
                responsive: true,
                displayModeBar: false,
            });
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
        const mapBlock = getReportBlock('geo_map');
        const mapConfig = (mapBlock && mapBlock.config) || getBlockConfig('geo_map');
        const latitudeField = mapConfig.latitude_field || 'latitude';
        const longitudeField = mapConfig.longitude_field || 'longitude';
        const labelField = mapConfig.label_field || 'daerah';
        return rows.map(function (row) {
            const lat = resolveCoordinate(row, [latitudeField, 'latitude', 'lat', 'Latitude']);
            const lng = resolveCoordinate(row, [longitudeField, 'longitude', 'lng', 'lon', 'Longitude']);
            if (lat === null || lng === null) {
                return null;
            }
            return {
                lat,
                lng,
                label: row[labelField] || row.daerah || row.label || row.record_label || row.record_key || 'Titik data',
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
            const rowDate = resolveRowDate(row, getReportBlock('plotly_timeseries'));
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
        const currentRows = Array.isArray(summaryJson.row_snapshots) ? summaryJson.row_snapshots : [];
        const filteredRows = applyDatasetFilters(currentRows);
        const metricBlock = getReportBlock('metric_cards');
        const chartBlock = getReportBlock('plotly_timeseries');
        const tableBlock = getReportBlock('detail_table');
        const narrativeBlock = getReportBlock('narrative');
        const mapBlock = getReportBlock('geo_map');
        const dimensionBlock = getReportBlock('dimension_distribution');
        const pieBlock = getReportBlock('dimension_pie');

        state.currentFilteredRowsByBlock = {
            metric_cards: filterRowsForBlock(metricBlock, currentRows),
            plotly_timeseries: filterRowsForBlock(chartBlock, currentRows),
            dimension_pie: filterRowsForBlock(pieBlock, currentRows),
            dimension_distribution: filterRowsForBlock(dimensionBlock, currentRows),
            detail_table: filterRowsForBlock(tableBlock, currentRows),
            narrative: filterRowsForBlock(narrativeBlock, currentRows),
            geo_map: filterRowsForBlock(mapBlock, currentRows),
        };

        renderMetricCards(state.currentFilteredRowsByBlock.metric_cards, summaryJson);
        renderDatasetSummary(dataset, activeVersion, latestRun, filteredRows);
        renderExecutionBridge(detail, latestRun);
        renderChart(state.currentFilteredRowsByBlock.plotly_timeseries);
        renderDimensionPieChart(state.currentFilteredRowsByBlock.dimension_pie || state.currentFilteredRowsByBlock.dimension_distribution);
        renderDimensionCharts(state.currentFilteredRowsByBlock.dimension_distribution);
        renderDetailTable(state.currentFilteredRowsByBlock.detail_table);
        renderNarrative(state.currentFilteredRowsByBlock.narrative, summaryJson);
        renderMap(state.currentFilteredRowsByBlock.geo_map);
    }

    function populateFilterControls(detail, runs) {
        const successfulRun = (runs || []).find((run) => run.status === 'succeeded') || (runs || [])[0] || null;
        const summaryJson = (successfulRun && successfulRun.summary_json) || {};
        const options = collectFilterOptions(summaryJson);

        populateSelectOptions(datasetFilterReportingYear, options.reportingYears, state.filters.reportingYear, 'Semua Tahun');
        populateDimensionFilterOptions();
    }

    function fetchDatasetRunsForSource(datasetId) {
        if (!datasetId || !config.analyticsDatasetRunsUrlTemplate) {
            return Promise.resolve([]);
        }
        const url = replaceTemplate(config.analyticsDatasetRunsUrlTemplate, '__DATASET_ID__', datasetId);
        return fetchJson(url).then(function (data) {
            return data.runs || [];
        }).catch(function () {
            return [];
        });
    }

    function fetchDatasetDetailForSource(datasetId) {
        if (!datasetId || !config.analyticsDatasetDetailUrlTemplate) {
            return Promise.resolve(null);
        }
        const url = replaceTemplate(config.analyticsDatasetDetailUrlTemplate, '__DATASET_ID__', datasetId);
        return fetchJson(url).catch(function () {
            return null;
        });
    }

    function loadReportDataSources() {
        const sources = getReportDataSources();
        if (!sources.length) {
            return Promise.resolve([]);
        }
        const uniqueDatasetIds = Array.from(new Set(sources.map(function (source) {
            return source && source.dataset_id ? String(source.dataset_id) : '';
        }).filter(Boolean)));
        return Promise.all(uniqueDatasetIds.map(function (datasetId) {
            if (String(datasetId) === String(state.selectedDatasetId || '') && state.currentDatasetDetail) {
                state.reportSourceDetails[String(datasetId)] = state.currentDatasetDetail;
                state.reportSourceRuns[String(datasetId)] = state.currentDatasetRuns || [];
                return Promise.resolve({ datasetId, detail: state.currentDatasetDetail, runs: state.currentDatasetRuns || [] });
            }
            return Promise.all([
                fetchDatasetDetailForSource(datasetId),
                fetchDatasetRunsForSource(datasetId),
            ]).then(function (results) {
                state.reportSourceDetails[String(datasetId)] = results[0];
                state.reportSourceRuns[String(datasetId)] = results[1] || [];
                return { datasetId, detail: results[0], runs: results[1] || [] };
            });
        }));
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
                return loadReportDataSources().then(function () {
                    populateFilterControls(data, runs);
                    rerenderDatasetView();
                });
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
            [datasetFilterDateStart, 'dateStart'],
            [datasetFilterDateEnd, 'dateEnd'],
            [datasetDimensionSelect, 'dimensionKey'],
            [datasetMetricPeriodMode, 'metricPeriodMode'],
            [datasetChartType, 'chartType'],
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

        if (datasetTimeseriesSplit) {
            state.filters.splitTimeseriesByDimension = datasetTimeseriesSplit.checked;
            datasetTimeseriesSplit.addEventListener('change', function () {
                state.filters.splitTimeseriesByDimension = datasetTimeseriesSplit.checked;
                rerenderDatasetView();
            });
        }

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

        document.querySelectorAll('[data-analytics-export]').forEach(function (button) {
            button.addEventListener('click', function () {
                exportDetailRows(button.getAttribute('data-analytics-export'));
            });
        });
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
        datasetMetricPeriodMode.value = 'monthly';
    }
    state.filters.metricPeriodMode = datasetMetricPeriodMode ? datasetMetricPeriodMode.value : (reportConfig.default_period_mode || 'monthly');
    state.filters.chartType = datasetChartType ? datasetChartType.value : 'bar';

    bindFilters();
    loadDatasets();
})();
