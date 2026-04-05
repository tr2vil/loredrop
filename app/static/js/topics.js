$(document).ready(function() {
    var selectedTopicId = null;

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

            renderSelected(selected);
            renderUnselected(unselected);
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
            'history_verification': {icon: 'bi-book', label: 'History', color: 'primary'},
            'channel_fit': {icon: 'bi-bullseye', label: 'Channel Fit', color: 'success'},
            'audience_appeal': {icon: 'bi-people', label: 'Audience', color: 'warning'}
        };

        var html = '<div class="mt-2 pt-2 border-top">';
        html += '<small class="fw-bold text-muted d-block mb-2"><i class="bi bi-robot me-1"></i>Agent Evaluation</small>';

        for (var key in agentLabels) {
            var d = details[key];
            if (!d) continue;
            var cfg = agentLabels[key];
            var score = d.score != null ? parseFloat(d.score).toFixed(1) : '-';

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

    function renderSelected(topics) {
        var $tbody = $('#selected-table-body');
        $('#selected-count').text(topics.length);
        $tbody.empty();

        if (topics.length === 0) {
            $tbody.html('<tr><td colspan="6" class="text-center text-muted py-3">No topics selected yet.</td></tr>');
            return;
        }

        topics.forEach(function(t) {
            var typeBadge = t.video_type === 'short'
                ? '<span class="badge bg-info bg-opacity-10 text-info">Short</span>'
                : '<span class="badge bg-purple bg-opacity-10 text-purple">Long</span>';
            $tbody.append(
                '<tr class="topic-row" style="cursor:pointer;" data-id="' + t.id + '">' +
                '<td>' + t.id + '</td>' +
                '<td><i class="bi bi-chevron-right me-1 small toggle-icon"></i>' + t.title + '</td>' +
                '<td><span class="badge bg-dark bg-opacity-10 text-dark">' + (t.category || '-') + '</span></td>' +
                '<td>' + (typeBadge || '-') + '</td>' +
                '<td>' + (t.batch_date || '-') + '</td>' +
                '<td><a href="/pipeline/start/' + t.id + '" class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation();"><i class="bi bi-camera-reels me-1"></i><span class="d-none d-md-inline">Produce</span></a></td>' +
                '</tr>' +
                '<tr class="detail-row d-none" data-parent="' + t.id + '">' +
                '<td colspan="6" class="bg-light px-4 py-3" style="border-top:none;">' +
                formatDescription(t.description, t.validation_details) +
                '</td>' +
                '</tr>'
            );
        });
    }

    function renderUnselected(topics) {
        var $tbody = $('#unselected-table-body');
        $('#unselected-count').text(topics.length);
        $tbody.empty();

        if (topics.length === 0) {
            $tbody.html('<tr><td colspan="6" class="text-center text-muted py-3">No recommended topics.</td></tr>');
            return;
        }

        topics.forEach(function(t) {
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
    }

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
        var $btn = $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span> Generating & Validating...');
        $.ajax({
            url: '/topics/generate',
            method: 'POST',
            data: '{}',
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
