$(document).ready(function() {
    // Pipeline detail page: poll status
    if (typeof RUN_ID !== 'undefined') {
        var pollInterval = setInterval(function() {
            $.getJSON('/pipeline/api/' + RUN_ID + '/status', function(data) {
                // Update step cards
                if (data.steps) {
                    data.steps.forEach(function(step) {
                        var $card = $('#step-' + step.step_name);
                        $card.removeClass('pending running completed failed').addClass(step.status);

                        var iconHtml;
                        if (step.status === 'completed') {
                            iconHtml = '<i class="bi bi-check-circle-fill"></i>';
                        } else if (step.status === 'running') {
                            iconHtml = '<div class="spinner-border spinner-border-sm" role="status"></div>';
                        } else if (step.status === 'failed') {
                            iconHtml = '<i class="bi bi-x-circle-fill"></i>';
                        } else {
                            iconHtml = '<i class="bi bi-circle"></i>';
                        }
                        $card.find('.step-icon').html(iconHtml);
                    });

                    // Enable next pending step button
                    var prevCompleted = true;
                    data.steps.forEach(function(step) {
                        var $btn = $('#step-' + step.step_name).find('.btn-execute-step');
                        if (step.status === 'pending' && prevCompleted) {
                            $btn.prop('disabled', false);
                            prevCompleted = false;
                        } else if (step.status === 'completed') {
                            prevCompleted = true;
                        } else {
                            prevCompleted = false;
                        }
                    });
                }

                // Update logs
                if (data.logs && data.logs.length > 0) {
                    var $log = $('#log-feed');
                    $log.html('');
                    data.logs.forEach(function(entry) {
                        $log.append('<div>' + entry + '</div>');
                    });
                    $log.scrollTop($log[0].scrollHeight);
                }

                // Stop polling if completed or failed
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(pollInterval);
                }
            });
        }, 2000);
    }

    // Execute step
    $(document).on('click', '.btn-execute-step', function() {
        var runId = $(this).data('run-id');
        var step = $(this).data('step');
        var $btn = $(this).prop('disabled', true);

        $.ajax({
            url: '/pipeline/' + runId + '/step/' + step + '/execute',
            method: 'POST',
            data: '{}',
            success: function() {
                showToast('Step "' + step + '" started.', 'info');
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'Failed to execute step.';
                showToast(msg, 'danger');
                $btn.prop('disabled', false);
            }
        });
    });

    // Auto mode toggle
    $('#auto-mode-toggle').on('change', function() {
        var runId = $(this).data('run-id');
        var autoMode = $(this).is(':checked');
        $.ajax({
            url: '/pipeline/' + runId + '/auto',
            method: 'POST',
            data: JSON.stringify({auto_mode: autoMode}),
            success: function() {
                showToast('Auto mode ' + (autoMode ? 'enabled' : 'disabled') + '.', 'info');
            }
        });
    });
});
