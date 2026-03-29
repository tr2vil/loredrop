$(document).ready(function() {
    var selectedTopicId = null;

    // Load topics
    function loadTopics() {
        var date = $('#filter-date').val();
        var status = $('#filter-status').val();
        var params = {};
        if (date) params.date = date;
        if (status) params.status = status;

        $.getJSON('/topics/api/list', params, function(data) {
            var $tbody = $('#topics-table-body');
            $tbody.empty();
            if (!data.topics || data.topics.length === 0) {
                $tbody.html('<tr><td colspan="6" class="text-center text-muted py-4">No topics found.</td></tr>');
                return;
            }
            data.topics.forEach(function(topic) {
                var statusBadge = topic.is_selected
                    ? '<span class="badge bg-success">Selected</span>'
                    : '<span class="badge bg-secondary">Recommended</span>';
                var actions = topic.is_selected
                    ? '<a href="/pipeline/start/' + topic.id + '" class="btn btn-sm btn-outline-primary">Pipeline</a>'
                    : '<button class="btn btn-sm btn-primary btn-select-topic" data-id="' + topic.id + '" data-title="' + topic.title + '">Select</button>';
                $tbody.append(
                    '<tr>' +
                    '<td>' + topic.id + '</td>' +
                    '<td>' + topic.title + '</td>' +
                    '<td>' + (topic.category || '-') + '</td>' +
                    '<td>' + (topic.batch_date || '-') + '</td>' +
                    '<td>' + statusBadge + '</td>' +
                    '<td>' + actions + '</td>' +
                    '</tr>'
                );
            });
        });
    }

    loadTopics();

    // Filter change
    $('#filter-date, #filter-status').on('change', loadTopics);

    // Generate topics
    $('#btn-generate').on('click', function() {
        var $btn = $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span> Generating...');
        $.ajax({
            url: '/topics/generate',
            method: 'POST',
            data: '{}',
            success: function(data) {
                showToast('Topics generated!', 'success');
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
