$(document).ready(function() {
    var selectedTopicId = null;

    // Pagination state
    var selectedPage = 1, selectedPerPage = 10, allSelectedTopics = [];
    var unselectedPage = 1, unselectedPerPage = 10, allUnselectedTopics = [];

    // Restore video type from localStorage
    var savedVideoType = localStorage.getItem('loredrop_video_type');
    if (savedVideoType && (savedVideoType === 'short' || savedVideoType === 'long')) {
        $('input[name="generateVideoType"][value="' + savedVideoType + '"]').prop('checked', true);
    }
    $(document).on('change', 'input[name="generateVideoType"]', function() {
        localStorage.setItem('loredrop_video_type', $(this).val());
    });

    // Restore per-page from localStorage
    var savedSelPP = localStorage.getItem('loredrop_sel_perpage');
    if (savedSelPP) { selectedPerPage = parseInt(savedSelPP) || 10; }
    var savedUnselPP = localStorage.getItem('loredrop_unsel_perpage');
    if (savedUnselPP) { unselectedPerPage = parseInt(savedUnselPP) || 10; }

    function loadTopics() {
        var params = {};
        var date = $('#filter-date').val();
        if (date) params.date = date;

        $.getJSON('/topics/api/list', params, function(data) {
            var selected = [];
            var unselected = [];

            (data.topics || []).forEach(function(t) {
                if (t.is_selected) {
                    selected.push(t);
                } else {
                    unselected.push(t);
                }
            });

            allSelectedTopics = selected;
            selectedPage = 1;
            renderSelectedPage();

            allUnselectedTopics = unselected;
            unselectedPage = 1;
            renderUnselectedPage();
        });
    }

    function scoreBadge(score) {
        if (score == null) return '<span class="text-muted">-</span>';
        var s = parseFloat(score);
        var cls = 'bg-success';
        if (s < 5) cls = 'bg-danger';
        else if (s < 8) cls = 'bg-warning text-dark';
        return '<span class="badge ' + cls + '" style="min-width:38px;">' + s.toFixed(1) + '</span>';
    }

    function formatValidationDetails(detailsStr) {
        if (!detailsStr) return '';
        var details;
        try { details = JSON.parse(detailsStr); } catch(e) { return ''; }
        if (!details || typeof details !== 'object') return '';

        var agentLabels = {
            'history_verification': {icon: 'bi-book', label: '역사 검증', color: 'primary'},
            'channel_fit': {icon: 'bi-bullseye', label: '채널 적합도', color: 'success'},
            'audience_appeal': {icon: 'bi-people', label: '청중 관심도', color: 'warning'}
        };

        var html = '<div class="mt-2 pt-2 border-top">';
        html += '<small class="fw-bold text-muted d-block mb-2"><i class="bi bi-robot me-1"></i>에이전트 평가</small>';

        for (var key in agentLabels) {
            var d = details[key];
            if (!d) continue;
            var cfg = agentLabels[key];

            html += '<div class="mb-2 p-2 rounded" style="background:rgba(0,0,0,0.03);">';
            html += '<div class="d-flex align-items-center gap-2 mb-1">';
            html += '<i class="bi ' + cfg.icon + ' text-' + cfg.color + '"></i>';
            html += '<strong class="small">' + cfg.label + '</strong>';
            html += scoreBadge(d.score);
            html += '</div>';
            if (d.reasoning) {
                html += '<div class="small text-muted">' + d.reasoning + '</div>';
            }
            if (d.strengths && d.strengths.length) {
                html += '<div class="small text-success mt-1">';
                d.strengths.forEach(function(s) { html += '<i class="bi bi-check-circle me-1"></i>' + s + ' '; });
                html += '</div>';
            }
            if (d.issues && d.issues.length) {
                html += '<div class="small text-danger mt-1">';
                d.issues.forEach(function(s) { html += '<i class="bi bi-exclamation-circle me-1"></i>' + s + ' '; });
                html += '</div>';
            }
            html += '</div>';
        }
        html += '</div>';
        return html;
    }

    function formatDescription(desc, validationDetails) {
        if (!desc) return '<span class="text-muted">No description</span>';
        var html = '';
        desc.split('\n').forEach(function(line) {
            line = line.trim();
            if (!line) return;
            if (line.startsWith('EN:')) {
                html += '<div class="mb-1"><i class="bi bi-translate me-1 text-primary"></i><em>' + line.substring(3).trim() + '</em></div>';
            } else if (line.startsWith('Why:')) {
                html += '<div class="mb-1">&#x1f4a1; ' + line.substring(4).trim() + '</div>';
            } else if (line.startsWith('Points:')) {
                html += '<div class="mb-1"><i class="bi bi-list-check me-1 text-success"></i>' + line.substring(7).trim() + '</div>';
            } else if (line.startsWith('Keywords:')) {
                var keywords = line.substring(9).trim().split(',');
                html += '<div class="mb-1">';
                keywords.forEach(function(k) {
                    k = k.trim();
                    if (k) html += '<span class="badge bg-secondary bg-opacity-10 text-secondary me-1">' + k + '</span>';
                });
                html += '</div>';
            } else {
                html += '<div class="mb-1">' + line + '</div>';
            }
        });
        html += formatValidationDetails(validationDetails);
        return html;
    }

    // ─── Pagination helper ───
    function renderPager($container, currentPage, totalPages, prefix) {
        $container.empty();
        if (totalPages <= 1) return;
        var html = '<ul class="pagination pagination-sm mb-0">';
        html += '<li class="page-item ' + (currentPage === 1 ? 'disabled' : '') + '">';
        html += '<a class="page-link" href="#" data-page="' + (currentPage - 1) + '" data-prefix="' + prefix + '">&laquo;</a></li>';
        for (var i = 1; i <= totalPages; i++) {
            html += '<li class="page-item ' + (i === currentPage ? 'active' : '') + '">';
            html += '<a class="page-link" href="#" data-page="' + i + '" data-prefix="' + prefix + '">' + i + '</a></li>';
        }
        html += '<li class="page-item ' + (currentPage === totalPages ? 'disabled' : '') + '">';
        html += '<a class="page-link" href="#" data-page="' + (currentPage + 1) + '" data-prefix="' + prefix + '">&raquo;</a></li>';
        html += '</ul>';
        $container.html(html);
    }

    function renderPerPageSelect($container, currentVal, prefix) {
        var html = '<select class="form-select form-select-sm per-page-select" data-prefix="' + prefix + '" style="width:70px;">';
        [5, 10, 20, 50].forEach(function(n) {
            html += '<option value="' + n + '"' + (n === currentVal ? ' selected' : '') + '>' + n + '</option>';
        });
        html += '</select>';
        $container.html(html);
    }

    // ─── Selected Topics ───
    function renderSelectedPage() {
        var topics = allSelectedTopics;
        var $tbody = $('#selected-table-body');
        var $pager = $('#selected-pager-nav');
        var $ppSelect = $('#selected-pp-select');
        $('#selected-count').text(topics.length);
        $tbody.empty();

        // Update delete button visibility
        $('#btn-delete-selected').addClass('d-none');

        if (topics.length === 0) {
            $tbody.html('<tr><td colspan="7" class="text-center text-muted py-3">No topics selected yet.</td></tr>');
            $pager.empty();
            $ppSelect.empty();
            return;
        }

        var totalPages = Math.ceil(topics.length / selectedPerPage);
        if (selectedPage > totalPages) selectedPage = totalPages;
        var start = (selectedPage - 1) * selectedPerPage;
        var pageTopics = topics.slice(start, start + selectedPerPage);

        pageTopics.forEach(function(t) {
            var typeBadge = t.video_type === 'short'
                ? '<span class="badge bg-info bg-opacity-10 text-info">Short</span>'
                : '<span class="badge bg-purple bg-opacity-10 text-purple">Long</span>';
            var hasPipeline = t.has_pipeline_run;
            var checkbox = hasPipeline
                ? '<input type="checkbox" class="form-check-input sel-check" disabled title="Pipeline이 시작된 주제는 삭제할 수 없습니다">'
                : '<input type="checkbox" class="form-check-input sel-check" data-id="' + t.selected_topic_id + '">';
            $tbody.append(
                '<tr class="topic-row" style="cursor:pointer;" data-id="' + t.id + '">' +
                '<td onclick="event.stopPropagation();">' + checkbox + '</td>' +
                '<td><i class="bi bi-chevron-right me-1 small toggle-icon"></i>' + t.title + '</td>' +
                '<td><span class="badge bg-dark bg-opacity-10 text-dark">' + (t.category || '-') + '</span></td>' +
                '<td>' + (typeBadge || '-') + '</td>' +
                '<td>' + (t.batch_date || '-') + '</td>' +
                '<td><a href="/pipeline/start/' + t.id + '" class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation();"><i class="bi bi-camera-reels me-1"></i><span class="d-none d-md-inline">Produce</span></a></td>' +
                '</tr>' +
                '<tr class="detail-row d-none" data-parent="' + t.id + '">' +
                '<td colspan="7" class="bg-light px-4 py-3" style="border-top:none;">' +
                formatDescription(t.description, t.validation_details) +
                '</td>' +
                '</tr>'
            );
        });

        renderPager($pager, selectedPage, totalPages, 'sel');
        renderPerPageSelect($ppSelect, selectedPerPage, 'sel');
    }

    // ─── Unselected Topics ───
    function renderUnselectedPage() {
        var topics = allUnselectedTopics;
        var $tbody = $('#unselected-table-body');
        var $pager = $('#unselected-pager-nav');
        var $ppSelect = $('#unselected-pp-select');
        $('#unselected-count').text(topics.length);
        $tbody.empty();

        if (topics.length === 0) {
            $tbody.html('<tr><td colspan="6" class="text-center text-muted py-3">No recommended topics.</td></tr>');
            $pager.empty();
            $ppSelect.empty();
            return;
        }

        var totalPages = Math.ceil(topics.length / unselectedPerPage);
        if (unselectedPage > totalPages) unselectedPage = totalPages;
        var start = (unselectedPage - 1) * unselectedPerPage;
        var pageTopics = topics.slice(start, start + unselectedPerPage);

        pageTopics.forEach(function(t) {
            $tbody.append(
                '<tr class="topic-row" style="cursor:pointer;" data-id="' + t.id + '">' +
                '<td>' + t.id + '</td>' +
                '<td><i class="bi bi-chevron-right me-1 small toggle-icon"></i>' + t.title + '</td>' +
                '<td class="text-center">' + scoreBadge(t.score_total) + '</td>' +
                '<td><span class="badge bg-dark bg-opacity-10 text-dark">' + (t.category || '-') + '</span></td>' +
                '<td>' + (t.batch_date || '-') + '</td>' +
                '<td><button class="btn btn-sm btn-primary btn-select-topic" data-id="' + t.id + '" data-title="' + t.title + '" onclick="event.stopPropagation();">Select</button></td>' +
                '</tr>' +
                '<tr class="detail-row d-none" data-parent="' + t.id + '">' +
                '<td colspan="6" class="bg-light px-4 py-3" style="border-top:none;">' +
                formatDescription(t.description, t.validation_details) +
                '</td>' +
                '</tr>'
            );
        });

        renderPager($pager, unselectedPage, totalPages, 'unsel');
        renderPerPageSelect($ppSelect, unselectedPerPage, 'unsel');
    }

    // ─── Pagination clicks ───
    $(document).on('click', '.page-link[data-prefix]', function(e) {
        e.preventDefault();
        var page = parseInt($(this).data('page'));
        var prefix = $(this).data('prefix');
        if (prefix === 'sel') {
            var maxPage = Math.ceil(allSelectedTopics.length / selectedPerPage);
            if (page >= 1 && page <= maxPage) { selectedPage = page; renderSelectedPage(); }
        } else if (prefix === 'unsel') {
            var maxPage = Math.ceil(allUnselectedTopics.length / unselectedPerPage);
            if (page >= 1 && page <= maxPage) { unselectedPage = page; renderUnselectedPage(); }
        }
    });

    // ─── Per-page change ───
    $(document).on('change', '.per-page-select', function() {
        var val = parseInt($(this).val()) || 10;
        var prefix = $(this).data('prefix');
        if (prefix === 'sel') {
            selectedPerPage = val;
            selectedPage = 1;
            localStorage.setItem('loredrop_sel_perpage', val);
            renderSelectedPage();
        } else if (prefix === 'unsel') {
            unselectedPerPage = val;
            unselectedPage = 1;
            localStorage.setItem('loredrop_unsel_perpage', val);
            renderUnselectedPage();
        }
    });

    // ─── Selected topic checkbox → show/hide delete button ───
    $(document).on('change', '.sel-check', function() {
        var checked = $('.sel-check:checked').length;
        if (checked > 0) {
            $('#btn-delete-selected').removeClass('d-none').find('.del-count').text(checked);
        } else {
            $('#btn-delete-selected').addClass('d-none');
        }
    });

    // ─── Delete selected topics ───
    $('#btn-delete-selected').on('click', function() {
        var ids = [];
        $('.sel-check:checked').each(function() { ids.push(parseInt($(this).data('id'))); });
        if (ids.length === 0) return;
        if (!confirm(ids.length + '개의 주제를 삭제하시겠습니까?')) return;

        $.ajax({
            url: '/topics/api/delete',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ids: ids}),
            success: function(resp) {
                showToast(resp.deleted + '개 주제 삭제 완료', 'success');
                if (resp.skipped > 0) {
                    showToast(resp.skipped + '개 주제는 Pipeline이 시작되어 삭제 불가', 'warning');
                }
                loadTopics();
            },
            error: function() {
                showToast('삭제 실패', 'danger');
            }
        });
    });

    // Toggle detail row on click
    $(document).on('click', '.topic-row', function() {
        var id = $(this).data('id');
        var $detail = $('tr.detail-row[data-parent="' + id + '"]');
        var $icon = $(this).find('.toggle-icon');
        $detail.toggleClass('d-none');
        $icon.toggleClass('bi-chevron-right bi-chevron-down');
    });

    loadTopics();

    // Filter change
    $('#filter-date').on('change', loadTopics);

    // Generate topics
    $('#btn-generate').on('click', function() {
        var videoType = $('input[name="generateVideoType"]:checked').val() || 'short';
        var $btn = $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span> Generating & Validating...');
        $.ajax({
            url: '/topics/generate',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({video_type: videoType}),
            success: function() {
                showToast('Topics generated and validated!', 'success');
                loadTopics();
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'Failed to generate topics.';
                showToast(msg, 'danger');
            },
            complete: function() {
                $btn.prop('disabled', false).html('<i class="bi bi-stars me-1"></i> Generate Topics');
            }
        });
    });

    // Select topic
    $(document).on('click', '.btn-select-topic', function() {
        selectedTopicId = $(this).data('id');
        $('#select-topic-title').text($(this).data('title'));
        var currentType = $('input[name="generateVideoType"]:checked').val() || 'short';
        $('input[name="videoType"][value="' + currentType + '"]').prop('checked', true);
        new bootstrap.Modal('#selectTopicModal').show();
    });

    // Confirm selection
    $('#btn-confirm-select').on('click', function() {
        var videoType = $('input[name="videoType"]:checked').val();
        $.ajax({
            url: '/topics/' + selectedTopicId + '/select',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({video_type: videoType}),
            success: function() {
                bootstrap.Modal.getInstance(document.getElementById('selectTopicModal')).hide();
                showToast('Topic selected!', 'success');
                loadTopics();
            },
            error: function() {
                showToast('Failed to select topic.', 'danger');
            }
        });
    });
});
