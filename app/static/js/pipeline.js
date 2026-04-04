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

                    // Update result text & progress
                    $row.find('.step-result-text').remove();
                    $row.find('.step-progress-bar').remove();

                    if (step.status === 'running' && data.step_progress && data.step_progress[step.step_name]) {
                        var prog = data.step_progress[step.step_name];
                        var current = parseInt(prog.current) || 0;
                        var total = parseInt(prog.total) || 1;
                        var pct = Math.round((current / total) * 100);
                        var label = prog.current_label || '';
                        $row.find('.step-label').parent().append(
                            '<div class="step-progress-bar mt-2" style="max-width: 320px;">' +
                            '  <div class="d-flex justify-content-between small text-muted mb-1">' +
                            '    <span>Generating ' + label + '...</span>' +
                            '    <span>' + current + ' / ' + total + '</span>' +
                            '  </div>' +
                            '  <div class="progress" style="height: 6px;">' +
                            '    <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: ' + pct + '%;"></div>' +
                            '  </div>' +
                            '</div>'
                        );
                    } else if (step.status === 'completed' && step.result_data) {
                        var txt = '';
                        if (step.result_data.total_duration) {
                            txt = step.result_data.paragraphs_processed + ' paragraphs · ' +
                                  step.result_data.total_duration + 's · ' +
                                  step.result_data.total_characters + ' chars';
                        } else if (step.result_data.scenes_processed !== undefined) {
                            txt = step.result_data.scenes_processed + ' scenes processed';
                        } else if (step.result_data.word_count) {
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

                        // Auto-load scripts/TTS when completed
                        if (step.step_name === 'script_generated' && !koLoaded) loadKoScript();
                        if (step.step_name === 'script_translated' && !enLoaded) loadEnScript();
                        if (step.step_name === 'tts_completed' && !ttsLoaded) loadTtsResults();
                        if (step.step_name === 'images_generated' && !imagesLoaded) loadImageResults();
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

    var ttsLoaded = false;
    var imagesLoaded = false;

    $(document).on('click', '.btn-toggle-result', function(e) {
        e.stopPropagation();
        var step = $(this).data('step');
        var $panel = $('#result-' + step);
        $panel.toggleClass('d-none');

        if (step === 'script_generated' && !koLoaded) loadKoScript();
        if (step === 'script_translated' && !enLoaded) loadEnScript();
        if (step === 'tts_completed' && !ttsLoaded) loadTtsResults();
        if (step === 'images_generated' && !imagesLoaded) loadImageResults();
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

    // ─── EN Script (structured paragraphs + per-paragraph TTS) ───
    function loadEnScript() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/script/en', function(data) {
            enLoaded = true;
            var $container = $('#en-paragraphs-container').empty();
            var totalWords = 0;
            (data.paragraphs || []).forEach(function(p, i) {
                var words = (p.text || '').split(/\s+/).filter(function(w) { return w; }).length;
                totalWords += words;
                var moodBadge = p.mood ? '<span class="badge bg-' + getMoodColor(p.mood) + ' bg-opacity-10 text-' + getMoodColor(p.mood) + '">' + p.mood + '</span>' : '';

                // Audio controls: show player if audio exists, otherwise show generate button
                var audioHtml = '';
                if (p.audio_path) {
                    var audioUrl = '/pipeline/api/' + RUN_ID + '/audio/P' + p.paragraph_index + '.mp3';
                    audioHtml =
                        '<div class="en-para-audio mt-1 d-flex align-items-center gap-2">' +
                        '  <audio controls preload="none" src="' + audioUrl + '" style="height:32px; flex-grow:1;"></audio>' +
                        '  <a href="' + audioUrl + '/download" class="btn btn-sm btn-outline-secondary py-0 px-1" title="Download">' +
                        '    <i class="bi bi-download"></i>' +
                        '  </a>' +
                        '  <button class="btn btn-sm btn-outline-warning btn-para-tts py-0 px-1" data-para-id="' + p.id + '" title="Regenerate TTS">' +
                        '    <i class="bi bi-arrow-clockwise"></i>' +
                        '  </button>' +
                        '</div>';
                } else {
                    audioHtml =
                        '<div class="en-para-audio mt-1">' +
                        '  <button class="btn btn-sm btn-outline-primary btn-para-tts" data-para-id="' + p.id + '">' +
                        '    <i class="bi bi-mic me-1"></i>Generate TTS' +
                        '  </button>' +
                        '</div>';
                }

                $container.append(
                    '<div class="card mb-2 en-para-card" data-id="' + p.id + '" data-para-index="' + p.paragraph_index + '">' +
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
                    audioHtml +
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

    // ─── Per-paragraph TTS generation ───
    $(document).on('click', '.btn-para-tts', function() {
        var $btn = $(this);
        var paraId = $btn.data('para-id');
        var $card = $btn.closest('.en-para-card');
        var paraIndex = $card.data('para-index');

        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span>');

        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/tts/paragraph/' + paraId,
            method: 'POST',
            data: '{}',
            success: function(result) {
                var audioUrl = '/pipeline/api/' + RUN_ID + '/audio/P' + result.paragraph_index + '.mp3';
                var $audioDiv = $card.find('.en-para-audio');
                $audioDiv.html(
                    '<div class="d-flex align-items-center gap-2">' +
                    '  <audio controls preload="none" src="' + audioUrl + '?t=' + Date.now() + '" style="height:32px; flex-grow:1;"></audio>' +
                    '  <a href="' + audioUrl + '/download" class="btn btn-sm btn-outline-secondary py-0 px-1" title="Download">' +
                    '    <i class="bi bi-download"></i>' +
                    '  </a>' +
                    '  <button class="btn btn-sm btn-outline-warning btn-para-tts py-0 px-1" data-para-id="' + paraId + '" title="Regenerate TTS">' +
                    '    <i class="bi bi-arrow-clockwise"></i>' +
                    '  </button>' +
                    '</div>'
                );
                showToast('TTS generated for P' + result.paragraph_index + ' (' + result.audio_duration + 's)', 'success');
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'TTS generation failed.';
                showToast(msg, 'danger');
                $btn.prop('disabled', false).html('<i class="bi bi-mic me-1"></i>Generate TTS');
            }
        });
    });

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

    // ─── TTS results panel (audio players + download) ───
    function loadTtsResults() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/script/en', function(data) {
            ttsLoaded = true;
            var $list = $('#tts-player-list').empty();
            var hasAudio = false;
            (data.paragraphs || []).forEach(function(p) {
                if (!p.audio_path) return;
                hasAudio = true;
                var audioUrl = '/pipeline/api/' + RUN_ID + '/audio/P' + p.paragraph_index + '.mp3';
                $list.append(
                    '<div class="d-flex align-items-center gap-2 mb-2">' +
                    '  <span class="fw-semibold small text-muted" style="width:30px;">P' + p.paragraph_index + '</span>' +
                    '  <audio controls preload="none" src="' + audioUrl + '" style="height:32px; flex-grow:1;"></audio>' +
                    '  <span class="text-muted small" style="width:40px;">' + (p.audio_duration ? p.audio_duration.toFixed(1) + 's' : '') + '</span>' +
                    '  <a href="' + audioUrl + '/download" class="btn btn-sm btn-outline-secondary py-0 px-1" title="Download">' +
                    '    <i class="bi bi-download"></i>' +
                    '  </a>' +
                    '</div>'
                );
            });
            if (hasAudio) {
                $('#btn-download-all-audio').show();
            } else {
                $list.html('<p class="text-muted small">No audio files generated yet.</p>');
            }
        });
    }

    // ─── Image results panel ───
    function loadImageResults() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/images', function(data) {
            imagesLoaded = true;
            var $container = $('#image-scenes-container').empty();
            var images = data.images || [];

            if (!images.length) {
                $container.html('<p class="text-muted small">No images generated yet.</p>');
                return;
            }

            // Also load EN script to show scene direction context
            $.getJSON('/pipeline/api/' + RUN_ID + '/script/en', function(scriptData) {
                var paraMap = {};
                (scriptData.paragraphs || []).forEach(function(p) {
                    paraMap[p.paragraph_index] = p;
                });

                images.forEach(function(img) {
                    var para = paraMap[img.scene_index] || {};
                    var sceneText = para.scene_direction || '';
                    var selectedUrl = img.selected_url || '';

                    var imagesHtml = '';
                    (img.image_urls || []).forEach(function(url, idx) {
                        var isSelected = (url === selectedUrl);
                        imagesHtml +=
                            '<div class="col-6 col-md-3">' +
                            '  <div class="position-relative scene-img-wrapper' + (isSelected ? ' selected' : '') + '"' +
                            '       data-scene-id="' + img.id + '" data-url="' + url + '">' +
                            '    <img src="' + url + '" class="img-fluid rounded" style="cursor:pointer; aspect-ratio:16/9; object-fit:cover; width:100%;">' +
                            (isSelected ? '<span class="badge bg-success position-absolute top-0 end-0 m-1"><i class="bi bi-check-lg"></i> Selected</span>' : '') +
                            '  </div>' +
                            '</div>';
                    });

                    $container.append(
                        '<div class="card mb-3 scene-image-card" data-scene-id="' + img.id + '">' +
                        '  <div class="card-body p-2">' +
                        '    <div class="d-flex justify-content-between align-items-center mb-2">' +
                        '      <span class="fw-semibold small text-muted">P' + img.scene_index + '</span>' +
                        '      <button class="btn btn-sm btn-outline-warning btn-regen-scene py-0 px-2" ' +
                        '              data-para-id="' + (para.id || '') + '" title="Regenerate">' +
                        '        <i class="bi bi-arrow-clockwise me-1"></i>Regenerate' +
                        '      </button>' +
                        '    </div>' +
                        '    <div class="text-muted small mb-2" style="font-size:0.78rem;">' + (sceneText || img.prompt || '') + '</div>' +
                        '    <div class="row g-2">' + imagesHtml + '</div>' +
                        '  </div>' +
                        '</div>'
                    );
                });
            });
        });
    }

    // Select image click
    $(document).on('click', '.scene-img-wrapper', function() {
        var sceneId = $(this).data('scene-id');
        var url = $(this).data('url');
        var $card = $(this).closest('.scene-image-card');

        // Optimistic UI
        $card.find('.scene-img-wrapper').removeClass('selected').find('.badge').remove();
        $(this).addClass('selected').append(
            '<span class="badge bg-success position-absolute top-0 end-0 m-1"><i class="bi bi-check-lg"></i> Selected</span>'
        );

        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/images/select',
            method: 'POST',
            data: JSON.stringify({ scene_image_id: sceneId, selected_url: url }),
            success: function() {
                showToast('Image selected!', 'success');
            },
            error: function(xhr) {
                showToast(xhr.responseJSON ? xhr.responseJSON.error : 'Failed to select.', 'danger');
            }
        });
    });

    // Regenerate single scene
    $(document).on('click', '.btn-regen-scene', function(e) {
        e.stopPropagation();
        var $btn = $(this);
        var paraId = $btn.data('para-id');
        if (!paraId) return;

        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span> Generating...');

        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/images/paragraph/' + paraId,
            method: 'POST',
            data: '{}',
            success: function() {
                showToast('Images regenerated!', 'success');
                imagesLoaded = false;
                loadImageResults();
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'Image generation failed.';
                showToast(msg, 'danger');
                $btn.prop('disabled', false).html('<i class="bi bi-arrow-clockwise me-1"></i>Regenerate');
            }
        });
    });

    // Download all audio files one by one
    $('#btn-download-all-audio').on('click', function() {
        $('#tts-player-list a[href$="/download"]').each(function(i) {
            var $link = $(this);
            setTimeout(function() {
                var a = document.createElement('a');
                a.href = $link.attr('href');
                a.download = '';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }, i * 300);
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
