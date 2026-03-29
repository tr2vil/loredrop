$(document).ready(function() {

    // Pipeline detail page
    if (typeof RUN_ID !== 'undefined') {
        var statusIcons = {
            'completed': '<i class="bi bi-check-circle-fill text-success fs-4"></i>',
            'running': '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>',
            'failed': '<i class="bi bi-x-circle-fill text-danger fs-4"></i>',
            'pending': '<i class="bi bi-circle text-muted fs-4"></i>',
            'skipped': '<i class="bi bi-dash-circle text-muted fs-4"></i>'
        };

        var statusBadgeClass = {
            'pending': 'secondary',
            'running': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'paused': 'warning'
        };

        var lastLogCount = 0;

        function pollStatus() {
            $.getJSON('/pipeline/api/' + RUN_ID + '/status', function(data) {
                // Update run status badge
                var cls = statusBadgeClass[data.status] || 'secondary';
                $('#run-status-badge').attr('class', 'badge bg-' + cls + ' me-2').text(data.status.toUpperCase());

                if (data.status === 'completed') {
                    $('#btn-run-all').prop('disabled', true);
                }

                // Update step icons and buttons
                if (data.steps) {
                    var prevCompleted = true;
                    data.steps.forEach(function(step) {
                        var $icon = $('.step-status-icon[data-step="' + step.step_name + '"]');
                        $icon.html(statusIcons[step.status] || statusIcons['pending']);

                        var $row = $('#step-row-' + step.step_name);

                        // Update result/error text
                        var $info = $row.find('.step-label').parent();
                        $info.find('.step-result').remove();
                        if (step.status === 'completed' && step.result_data) {
                            var resultText = '';
                            if (step.result_data.word_count) {
                                resultText = step.result_data.word_count + ' chars, ' + step.result_data.paragraphs + ' paragraphs';
                                // Show script preview
                                loadScriptPreview(step.result_data.script_id);
                            } else if (step.result_data.message) {
                                resultText = step.result_data.message;
                            }
                            if (resultText) {
                                $info.find('.step-label').after('<span class="text-muted small ms-2 step-result">' + resultText + '</span>');
                            }
                        } else if (step.status === 'failed' && step.error_message) {
                            $info.find('.step-label').after('<span class="text-danger small ms-2 step-result">' + step.error_message + '</span>');
                        }

                        // Update buttons
                        $row.find('.btn-execute-step, .btn-retry-step').remove();
                        if (step.status === 'pending' && prevCompleted) {
                            $row.find('.d-flex.align-items-center.gap-2').append(
                                '<button class="btn btn-sm btn-outline-primary btn-execute-step" ' +
                                'data-run-id="' + RUN_ID + '" data-step="' + step.step_name + '">' +
                                '<i class="bi bi-play-fill"></i> Run</button>'
                            );
                        } else if (step.status === 'failed') {
                            $row.find('.d-flex.align-items-center.gap-2').append(
                                '<button class="btn btn-sm btn-outline-danger btn-execute-step" ' +
                                'data-run-id="' + RUN_ID + '" data-step="' + step.step_name + '">' +
                                '<i class="bi bi-arrow-clockwise"></i> Retry</button>'
                            );
                        }

                        if (step.status === 'completed') {
                            prevCompleted = true;
                        } else {
                            prevCompleted = false;
                        }
                    });
                }

                // Update logs
                if (data.logs && data.logs.length > 0) {
                    if (data.logs.length !== lastLogCount) {
                        var $log = $('#log-feed');
                        $log.html('');
                        data.logs.forEach(function(entry) {
                            var cssClass = 'text-light';
                            if (entry.indexOf('Failed') >= 0 || entry.indexOf('Error') >= 0) cssClass = 'text-danger';
                            else if (entry.indexOf('Completed') >= 0) cssClass = 'text-success';
                            else if (entry.indexOf('Starting') >= 0) cssClass = 'text-info';
                            else if (entry.indexOf('Auto-mode') >= 0) cssClass = 'text-warning';
                            $log.append('<div class="' + cssClass + '">' + entry + '</div>');
                        });
                        $log.scrollTop($log[0].scrollHeight);
                        lastLogCount = data.logs.length;
                        $('#log-count').text(data.logs.length);
                    }
                }

                // Keep polling if not terminal state
                if (data.status !== 'completed' && data.status !== 'failed') {
                    setTimeout(pollStatus, 2000);
                } else {
                    // One final poll after 1s to catch last updates
                    setTimeout(pollStatus, 1000);
                }
            });
        }

        // Start polling
        pollStatus();

        // Load script preview
        function loadScriptPreview(scriptId) {
            if (!scriptId) return;
            // Simple: just show we have a script. Full preview would need a script API.
            $('#script-preview-card').removeClass('d-none');
        }
    }

    // Execute step
    $(document).on('click', '.btn-execute-step', function() {
        var runId = $(this).data('run-id');
        var step = $(this).data('step');
        $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');

        $.ajax({
            url: '/pipeline/' + runId + '/step/' + step + '/execute',
            method: 'POST',
            data: '{}',
            success: function() {
                showToast('Step "' + step.replace(/_/g, ' ') + '" started.', 'info');
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'Failed to execute step.';
                showToast(msg, 'danger');
            }
        });
    });

    // Run All
    $('#btn-run-all').on('click', function() {
        $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span> Running...');
        $.ajax({
            url: '/pipeline/' + RUN_ID + '/run-all',
            method: 'POST',
            data: '{}',
            success: function() {
                showToast('Pipeline started in auto-mode!', 'success');
            },
            error: function() {
                showToast('Failed to start pipeline.', 'danger');
                $('#btn-run-all').prop('disabled', false).html('<i class="bi bi-play-fill me-1"></i> Run All');
            }
        });
    });
});
