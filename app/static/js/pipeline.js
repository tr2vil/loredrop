$(document).ready(function() {
    if (typeof RUN_ID === 'undefined') return;

    var statusIcons = {
        'completed': '<i class="bi bi-check"></i>',
        'running': '<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span>',
        'failed': '<i class="bi bi-x"></i>',
        'pending': ''
    };

    var statusNumClass = {
        'completed': 'bg-success text-white',
        'running': 'bg-primary text-white',
        'failed': 'bg-danger text-white',
        'pending': 'bg-light text-muted'
    };

    var lastLogCount = 0;
    var scriptLoaded = false;

    // ─── Poll status ───
    function pollStatus() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/status', function(data) {
            // Run badge
            var cls = {pending:'secondary', running:'primary', completed:'success', failed:'danger'}[data.status] || 'secondary';
            $('#run-status-badge').attr('class', 'badge bg-' + cls).text(data.status.toUpperCase());
            if (data.status === 'completed') $('#btn-run-all').prop('disabled', true);

            // Steps
            if (data.steps) {
                var prevCompleted = true;
                var stepIdx = 0;
                data.steps.forEach(function(step) {
                    stepIdx++;
                    var $row = $('#step-row-' + step.step_name);
                    var $num = $row.find('.step-number[data-step="' + step.step_name + '"]');

                    // Update number/icon
                    $num.attr('class', 'step-number ' + (statusNumClass[step.status] || statusNumClass['pending']));
                    $num.html(step.status === 'pending' ? stepIdx : (statusIcons[step.status] || stepIdx));

                    // Update result text
                    $row.find('.step-result-text').remove();
                    if (step.status === 'completed' && step.result_data) {
                        var txt = '';
                        if (step.result_data.word_count) {
                            txt = step.result_data.word_count + ' chars · ' + step.result_data.paragraphs + ' paragraphs';
                        } else if (step.result_data.message) {
                            txt = step.result_data.message;
                        }
                        if (txt) {
                            $row.find('.step-label').parent().append('<div class="text-muted small mt-1 step-result-text">' + txt + '</div>');
                        }
                    } else if (step.status === 'failed' && step.error_message) {
                        $row.find('.step-label').parent().append('<div class="text-danger small mt-1 step-result-text">' + step.error_message + '</div>');
                    }

                    // Update action buttons
                    var $actions = $row.find('.d-flex.align-items-center.gap-2').last();
                    $actions.find('.btn-execute-step, .bi-check-lg, .btn-toggle-result').remove();

                    if (step.status === 'completed') {
                        // Show view button for steps with results
                        var viewSteps = ['script_generated', 'script_translated', 'tts_completed', 'images_generated', 'uploaded'];
                        if (viewSteps.indexOf(step.step_name) >= 0) {
                            $actions.prepend(
                                '<button class="btn btn-sm btn-outline-secondary btn-toggle-result" data-step="' + step.step_name + '" title="View">' +
                                '<i class="bi bi-eye"></i></button>'
                            );
                        }
                        $actions.append('<i class="bi bi-check-lg text-success"></i>');

                        // Auto-load scripts when completed
                        if (step.step_name === 'script_generated' && !koLoaded) loadKoScript();
                        if (step.step_name === 'script_translated' && !enLoaded) loadEnScript();
                    } else if (step.status === 'pending' && prevCompleted) {
                        $actions.append(
                            '<button class="btn btn-sm btn-outline-primary btn-execute-step" data-run-id="' + RUN_ID + '" data-step="' + step.step_name + '">' +
                            '<i class="bi bi-play-fill"></i><span class="d-none d-md-inline ms-1">Run</span></button>'
                        );
                    } else if (step.status === 'failed') {
                        $actions.append(
                            '<button class="btn btn-sm btn-outline-danger btn-execute-step" data-run-id="' + RUN_ID + '" data-step="' + step.step_name + '">' +
                            '<i class="bi bi-arrow-clockwise"></i><span class="d-none d-md-inline ms-1">Retry</span></button>'
                        );
                    }

                    prevCompleted = (step.status === 'completed');
                });
            }

            // Logs
            if (data.logs && data.logs.length !== lastLogCount) {
                var $log = $('#log-feed').html('');
                data.logs.forEach(function(entry) {
                    var c = 'text-light';
                    if (entry.indexOf('Failed') >= 0) c = 'text-danger';
                    else if (entry.indexOf('Completed') >= 0 || entry.indexOf('completed') >= 0) c = 'text-success';
                    else if (entry.indexOf('Starting') >= 0) c = 'text-info';
                    else if (entry.indexOf('Auto-mode') >= 0) c = 'text-warning';
                    $log.append('<div class="' + c + '">' + entry + '</div>');
                });
                $log.scrollTop($log[0].scrollHeight);
                lastLogCount = data.logs.length;
                $('#log-count').text(data.logs.length);
            }

            // Keep polling
            if (data.status !== 'completed' && data.status !== 'failed') {
                setTimeout(pollStatus, 2000);
            }
        });
    }
    pollStatus();

    // ─── Toggle result panels ───
    var koLoaded = false, enLoaded = false;

    $(document).on('click', '.btn-toggle-result', function(e) {
        e.stopPropagation();
        var step = $(this).data('step');
        var $panel = $('#result-' + step);
        $panel.toggleClass('d-none');

        if (step === 'script_generated' && !koLoaded) loadKoScript();
        if (step === 'script_translated' && !enLoaded) loadEnScript();
    });

    // ─── KO Script (structured paragraphs) ───
    var MOOD_COLORS = {
        'tense': 'danger', 'mysterious': 'purple', 'dramatic': 'warning',
        'triumphant': 'success', 'somber': 'secondary', 'hopeful': 'info',
        'shocking': 'danger', 'reflective': 'info', 'urgent': 'warning'
    };

    function getMoodColor(mood) {
        if (!mood) return 'secondary';
        var m = mood.toLowerCase();
        for (var key in MOOD_COLORS) { if (m.indexOf(key) >= 0) return MOOD_COLORS[key]; }
        return 'secondary';
    }

    function loadKoScript() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/script/ko', function(data) {
            koLoaded = true;
            var $container = $('#script-paragraphs-container').empty();
            var totalChars = 0;
            (data.paragraphs || []).forEach(function(p, i) {
                totalChars += (p.text || '').length;
                var moodBadge = p.mood ? '<span class="badge bg-' + getMoodColor(p.mood) + ' bg-opacity-10 text-' + getMoodColor(p.mood) + '">' + p.mood + '</span>' : '';
                $container.append(
                    '<div class="card mb-2 para-card" data-id="' + p.id + '">' +
                    '  <div class="card-body p-2">' +
                    '    <div class="d-flex justify-content-between align-items-center mb-1">' +
                    '      <span class="fw-semibold small text-muted">P' + (i + 1) + '</span>' +
                    '      ' + moodBadge +
                    '    </div>' +
                    '    <textarea class="form-control form-control-sm para-text mb-1" rows="3" ' +
                    '              style="font-size: 0.88rem; line-height: 1.6;">' + (p.text || '') + '</textarea>' +
                    '    <div class="d-flex gap-2">' +
                    '      <div class="flex-grow-1">' +
                    '        <input class="form-control form-control-sm para-scene" placeholder="Scene direction..." ' +
                    '               value="' + (p.scene_direction || '').replace(/"/g, '&quot;') + '" ' +
                    '               style="font-size: 0.8rem; color: #6c757d;">' +
                    '      </div>' +
                    '      <div style="width: 120px;">' +
                    '        <input class="form-control form-control-sm para-mood" placeholder="Mood..." ' +
                    '               value="' + (p.mood || '').replace(/"/g, '&quot;') + '" style="font-size: 0.8rem;">' +
                    '      </div>' +
                    '    </div>' +
                    '  </div>' +
                    '</div>'
                );
            });
            $('#script-char-count').text('· ' + totalChars + ' chars · ' + (data.paragraphs || []).length + ' paragraphs');
            $('#btn-save-script').prop('disabled', false);
        }).fail(function() {
            $('#script-paragraphs-container').html('<p class="text-muted small text-center py-3">Not generated yet.</p>');
        });
    }

    // Track KO changes
    $(document).on('input', '.para-text, .para-scene, .para-mood', function() {
        $('#btn-save-script').removeClass('btn-primary').addClass('btn-warning').html('<i class="bi bi-save me-1"></i>Save *');
    });

    // Save KO script
    $('#btn-save-script').on('click', function() {
        var $btn = $(this).prop('disabled', true);
        var paragraphs = [];
        var fullText = [];
        $('.para-card').each(function() {
            var text = $(this).find('.para-text').val();
            fullText.push(text);
            paragraphs.push({
                id: $(this).data('id'),
                text: text,
                scene_direction: $(this).find('.para-scene').val(),
                mood: $(this).find('.para-mood').val()
            });
        });
        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/script/ko',
            method: 'PUT',
            data: JSON.stringify({ full_text: fullText.join('\n\n'), paragraphs: paragraphs }),
            success: function() {
                showToast('Script saved!', 'success');
                $btn.prop('disabled', false).removeClass('btn-warning').addClass('btn-primary').html('<i class="bi bi-check-lg me-1"></i>Save');
            },
            error: function() { showToast('Failed to save.', 'danger'); $btn.prop('disabled', false); }
        });
    });

    // ─── EN Script (structured paragraphs) ───
    function loadEnScript() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/script/en', function(data) {
            enLoaded = true;
            var $container = $('#en-paragraphs-container').empty();
            var totalWords = 0;
            (data.paragraphs || []).forEach(function(p, i) {
                var words = (p.text || '').split(/\s+/).filter(function(w) { return w; }).length;
                totalWords += words;
                var moodBadge = p.mood ? '<span class="badge bg-' + getMoodColor(p.mood) + ' bg-opacity-10 text-' + getMoodColor(p.mood) + '">' + p.mood + '</span>' : '';
                $container.append(
                    '<div class="card mb-2 en-para-card" data-id="' + p.id + '">' +
                    '  <div class="card-body p-2">' +
                    '    <div class="d-flex justify-content-between align-items-center mb-1">' +
                    '      <span class="fw-semibold small text-muted">P' + (i + 1) + '</span>' +
                    '      ' + moodBadge +
                    '    </div>' +
                    '    <textarea class="form-control form-control-sm en-para-text mb-1" rows="3" ' +
                    '              style="font-size: 0.88rem; line-height: 1.6;">' + (p.text || '') + '</textarea>' +
                    '    <div class="d-flex gap-2">' +
                    '      <div class="flex-grow-1">' +
                    '        <input class="form-control form-control-sm en-para-scene" placeholder="Scene direction..." ' +
                    '               value="' + (p.scene_direction || '').replace(/"/g, '&quot;') + '" ' +
                    '               style="font-size: 0.8rem; color: #6c757d;">' +
                    '      </div>' +
                    '      <div style="width: 120px;">' +
                    '        <input class="form-control form-control-sm en-para-mood" placeholder="Mood..." ' +
                    '               value="' + (p.mood || '').replace(/"/g, '&quot;') + '" style="font-size: 0.8rem;">' +
                    '      </div>' +
                    '    </div>' +
                    '  </div>' +
                    '</div>'
                );
            });
            $('#translated-word-count').text('· ' + totalWords + ' words · ~' + Math.round(totalWords / 2.5) + 's · ' + (data.paragraphs || []).length + ' paragraphs');
            $('#btn-save-translated').prop('disabled', false);
        }).fail(function() {
            $('#en-paragraphs-container').html('<p class="text-muted small text-center py-3">Not generated yet.</p>');
        });
    }

    // Track EN changes
    $(document).on('input', '.en-para-text, .en-para-scene, .en-para-mood', function() {
        $('#btn-save-translated').removeClass('btn-primary').addClass('btn-warning').html('<i class="bi bi-save me-1"></i>Save *');
    });

    // Save EN script
    $('#btn-save-translated').on('click', function() {
        var $btn = $(this).prop('disabled', true);
        var paragraphs = [];
        var fullText = [];
        $('.en-para-card').each(function() {
            var text = $(this).find('.en-para-text').val();
            fullText.push(text);
            paragraphs.push({
                id: $(this).data('id'),
                text: text,
                scene_direction: $(this).find('.en-para-scene').val(),
                mood: $(this).find('.en-para-mood').val()
            });
        });
        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/script/en',
            method: 'PUT',
            data: JSON.stringify({ full_text: fullText.join('\n\n'), paragraphs: paragraphs }),
            success: function() {
                showToast('Script saved!', 'success');
                $btn.prop('disabled', false).removeClass('btn-warning').addClass('btn-primary').html('<i class="bi bi-check-lg me-1"></i>Save');
            },
            error: function() { showToast('Failed to save.', 'danger'); $btn.prop('disabled', false); }
        });
    });

    // ─── Execute step ───
    $(document).on('click', '.btn-execute-step', function() {
        var runId = $(this).data('run-id');
        var step = $(this).data('step');
        $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span>');
        $.ajax({
            url: '/pipeline/' + runId + '/step/' + step + '/execute',
            method: 'POST',
            data: '{}',
            success: function() { showToast('Step started.', 'info'); },
            error: function(xhr) {
                showToast(xhr.responseJSON ? xhr.responseJSON.error : 'Failed.', 'danger');
            }
        });
    });

    // ─── Run All ───
    $('#btn-run-all').on('click', function() {
        $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>Running...');
        $.ajax({
            url: '/pipeline/' + RUN_ID + '/run-all',
            method: 'POST',
            data: '{}',
            success: function() { showToast('Production started!', 'success'); },
            error: function() {
                showToast('Failed to start.', 'danger');
                $('#btn-run-all').prop('disabled', false).html('<i class="bi bi-play-fill me-1"></i>Run All');
            }
        });
    });

    // ─── Upload file select ───
    $('#upload-file').on('change', function() {
        $('#btn-upload-youtube').prop('disabled', !this.files.length);
    });
});
