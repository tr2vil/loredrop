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

    // Steps visible in UI (backend still has 6)
    var VISUAL_STEPS = ['topic_confirmed', 'script_generated', 'script_translated', 'uploaded'];
    var HIDDEN_STEPS = ['tts_completed', 'images_generated'];

    var lastLogCount = 0;

    // Helper: extract URL from image data
    function imgUrl(item) { return typeof item === 'object' ? item.url : item; }
    function imgId(item) { return typeof item === 'object' ? item.id : null; }

    // ─── Poll status ───
    function pollStatus() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/status', function(data) {
            // Run badge
            var cls = {pending:'secondary', running:'primary', completed:'success', failed:'danger'}[data.status] || 'secondary';
            $('#run-status-badge').attr('class', 'badge bg-' + cls).text(data.status.toUpperCase());
            if (data.status === 'completed') $('#btn-run-all').prop('disabled', true);

            if (data.steps) {
                var stepMap = {};
                data.steps.forEach(function(s) { stepMap[s.step_name] = s; });

                // Update visible step rows
                var prevCompleted = true;
                var visIdx = 0;
                data.steps.forEach(function(step) {
                    // Skip hidden steps in UI row rendering
                    if (HIDDEN_STEPS.indexOf(step.step_name) >= 0) {
                        prevCompleted = (step.status === 'completed');
                        return;
                    }

                    visIdx++;
                    var $row = $('#step-row-' + step.step_name);
                    if (!$row.length) return;
                    var $num = $row.find('.step-number[data-step="' + step.step_name + '"]');

                    // Update number/icon
                    $num.attr('class', 'step-number ' + (statusNumClass[step.status] || statusNumClass['pending']));
                    $num.html(step.status === 'pending' ? visIdx : (statusIcons[step.status] || visIdx));

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
                    var $actions = $row.find('.step-actions');
                    $actions.find('.btn-execute-step, .bi-check-lg, .btn-toggle-result').remove();

                    if (step.status === 'completed') {
                        var viewSteps = ['script_generated', 'script_translated', 'uploaded'];
                        if (viewSteps.indexOf(step.step_name) >= 0) {
                            $actions.prepend(
                                '<button class="btn btn-sm btn-outline-secondary btn-toggle-result" data-step="' + step.step_name + '" title="View">' +
                                '<i class="bi bi-eye"></i></button>'
                            );
                        }
                        $actions.append('<i class="bi bi-check-lg text-success"></i>');

                        // Auto-load when completed
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

                // Handle hidden steps (TTS/Images) — show inline progress & refresh
                var ttsStep = stepMap['tts_completed'];
                var imgStep = stepMap['images_generated'];

                // TTS batch progress
                if (ttsStep && ttsStep.status === 'running') {
                    var ttsProg = (data.step_progress && data.step_progress['tts_completed']) || {};
                    var ttsCur = parseInt(ttsProg.current) || 0;
                    var ttsTotal = parseInt(ttsProg.total) || 1;
                    var ttsPct = Math.round((ttsCur / ttsTotal) * 100);
                    $('#batch-tts-progress').removeClass('d-none');
                    $('#batch-tts-bar').css('width', ttsPct + '%');
                    $('#batch-tts-label').text(ttsCur + '/' + ttsTotal + ' ' + (ttsProg.current_label || ''));
                    $('#btn-batch-tts').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span> Generating...');
                } else {
                    $('#batch-tts-progress').addClass('d-none');
                    $('#btn-batch-tts').prop('disabled', false).html('<i class="bi bi-mic me-1"></i>All TTS');
                }

                if (ttsStep && ttsStep.status === 'completed' && !ttsCompletedHandled) {
                    ttsCompletedHandled = true;
                    // Refresh EN script to show audio players
                    enLoaded = false;
                    enSceneImages = {};
                    loadEnScript();
                    _updateDownloadAllBtn();
                }

                // Images batch progress
                if (imgStep && imgStep.status === 'running') {
                    var imgProg = (data.step_progress && data.step_progress['images_generated']) || {};
                    var imgCur = parseInt(imgProg.current) || 0;
                    var imgTotal = parseInt(imgProg.total) || 1;
                    var imgPct = Math.round((imgCur / imgTotal) * 100);
                    $('#batch-images-progress').removeClass('d-none');
                    $('#batch-images-bar').css('width', imgPct + '%');
                    $('#batch-images-label').text(imgCur + '/' + imgTotal + ' ' + (imgProg.current_label || ''));
                    $('#btn-batch-images').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span> Generating...');
                } else {
                    $('#batch-images-progress').addClass('d-none');
                    $('#btn-batch-images').prop('disabled', false).html('<i class="bi bi-image me-1"></i>All Images');
                }

                if (imgStep && imgStep.status === 'completed' && !imagesCompletedHandled) {
                    imagesCompletedHandled = true;
                    enLoaded = false;
                    enSceneImages = {};
                    loadEnScript();
                }
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
    var ttsCompletedHandled = false;
    var imagesCompletedHandled = false;

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

    // ─── EN Script (structured paragraphs + per-paragraph TTS + Images) ───
    var enSceneImages = {};

    function loadEnScript() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/images', function(imgData) {
            (imgData.images || []).forEach(function(img) {
                enSceneImages[img.scene_index] = img;
            });
        }).always(function() {
            _renderEnParagraphs();
        });
    }

    function _renderEnParagraphs() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/script/en', function(data) {
            enLoaded = true;
            var $container = $('#en-paragraphs-container').empty();
            var totalWords = 0;
            var hasAudio = false;
            (data.paragraphs || []).forEach(function(p, i) {
                var words = (p.text || '').split(/\s+/).filter(function(w) { return w; }).length;
                totalWords += words;
                var moodBadge = p.mood ? '<span class="badge bg-' + getMoodColor(p.mood) + ' bg-opacity-10 text-' + getMoodColor(p.mood) + '">' + p.mood + '</span>' : '';

                // Audio controls
                var audioHtml = '';
                if (p.audio_path) {
                    hasAudio = true;
                    var audioUrl = '/pipeline/api/' + RUN_ID + '/audio/P' + p.paragraph_index + '.mp3';
                    audioHtml =
                        '<div class="en-para-audio d-flex align-items-center gap-2">' +
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
                        '<div class="en-para-audio">' +
                        '  <button class="btn btn-sm btn-outline-primary btn-para-tts" data-para-id="' + p.id + '">' +
                        '    <i class="bi bi-mic me-1"></i>TTS' +
                        '  </button>' +
                        '</div>';
                }

                // Image controls
                var sceneImg = enSceneImages[p.paragraph_index];
                var imageHtml = '';
                if (sceneImg && sceneImg.image_urls && sceneImg.image_urls.length) {
                    var thumbs = '';
                    sceneImg.image_urls.forEach(function(item) {
                        var url = imgUrl(item);
                        var isSelected = (url === sceneImg.selected_url);
                        thumbs +=
                            '<div class="img-thumb-click' + (isSelected ? ' selected' : '') + '"' +
                            '     data-scene-id="' + sceneImg.id + '" data-url="' + url + '"' +
                            '     style="position:relative; cursor:pointer; border: 2px solid ' + (isSelected ? '#198754' : 'transparent') + '; border-radius: 4px; overflow:hidden;">' +
                            '  <img src="' + url + '" style="width:64px; height:64px; object-fit:cover; display:block;">' +
                            (isSelected ? '<span class="badge bg-success" style="position:absolute;top:0;right:0;font-size:.55rem;"><i class="bi bi-check"></i></span>' : '') +
                            '</div>';
                    });
                    imageHtml =
                        '<div class="en-para-images">' +
                        '  <div class="d-flex align-items-center gap-1 flex-wrap">' + thumbs +
                        '    <button class="btn btn-sm btn-outline-warning btn-para-img py-0 px-1" data-para-id="' + p.id + '" title="Regenerate Images">' +
                        '      <i class="bi bi-arrow-clockwise"></i>' +
                        '    </button>' +
                        '  </div>' +
                        '</div>';
                } else if (p.scene_direction) {
                    imageHtml =
                        '<div class="en-para-images">' +
                        '  <button class="btn btn-sm btn-outline-success btn-para-img" data-para-id="' + p.id + '">' +
                        '    <i class="bi bi-image me-1"></i>Image' +
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
                    '    <div class="d-flex gap-2 mb-1">' +
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
                    '    <div class="d-flex gap-2 align-items-start mt-1">' +
                    '      <div class="flex-grow-1">' + audioHtml + '</div>' +
                    '      <div>' + imageHtml + '</div>' +
                    '    </div>' +
                    '  </div>' +
                    '</div>'
                );
            });
            $('#translated-word-count').text('· ' + totalWords + ' words · ~' + Math.round(totalWords / 2.5) + 's · ' + (data.paragraphs || []).length + ' paragraphs');
            $('#btn-save-translated').prop('disabled', false);
            if (hasAudio) $('#btn-download-all-audio').show();
        }).fail(function() {
            $('#en-paragraphs-container').html('<p class="text-muted small text-center py-3">Not generated yet.</p>');
        });
    }

    function _updateDownloadAllBtn() {
        $.getJSON('/pipeline/api/' + RUN_ID + '/script/en', function(data) {
            var has = (data.paragraphs || []).some(function(p) { return !!p.audio_path; });
            if (has) $('#btn-download-all-audio').show();
        });
    }

    // ─── Per-paragraph Image generation ───
    $(document).on('click', '.btn-para-img', function() {
        var $btn = $(this);
        var paraId = $btn.data('para-id');
        var $card = $btn.closest('.en-para-card');

        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span>');

        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/images/paragraph/' + paraId,
            method: 'POST',
            data: '{}',
            success: function(result) {
                showToast('Images generated for P' + $card.data('para-index') + '!', 'success');
                enSceneImages[result.scene_index] = result;
                enLoaded = false;
                loadEnScript();
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'Image generation failed.';
                showToast(msg, 'danger');
                $btn.prop('disabled', false).html('<i class="bi bi-image me-1"></i>Image');
            }
        });
    });

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
                $('#btn-download-all-audio').show();
            },
            error: function(xhr) {
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'TTS generation failed.';
                showToast(msg, 'danger');
                $btn.prop('disabled', false).html('<i class="bi bi-mic me-1"></i>TTS');
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

    // ─── Batch TTS generation (calls backend step execute) ───
    $('#btn-batch-tts').on('click', function() {
        var $btn = $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span> Starting...');
        ttsCompletedHandled = false;
        $.ajax({
            url: '/pipeline/' + RUN_ID + '/step/tts_completed/execute',
            method: 'POST',
            data: '{}',
            success: function() {
                showToast('TTS generation started.', 'info');
                // pollStatus will handle progress display
                if (!pollActive) { pollActive = true; pollStatus(); }
            },
            error: function(xhr) {
                showToast(xhr.responseJSON ? xhr.responseJSON.error : 'Failed to start TTS.', 'danger');
                $btn.prop('disabled', false).html('<i class="bi bi-mic me-1"></i>All TTS');
            }
        });
    });

    // ─── Batch Images generation (calls backend step execute) ───
    $('#btn-batch-images').on('click', function() {
        var $btn = $(this).prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span> Starting...');
        imagesCompletedHandled = false;
        $.ajax({
            url: '/pipeline/' + RUN_ID + '/step/images_generated/execute',
            method: 'POST',
            data: '{}',
            success: function() {
                showToast('Image generation started.', 'info');
                if (!pollActive) { pollActive = true; pollStatus(); }
            },
            error: function(xhr) {
                showToast(xhr.responseJSON ? xhr.responseJSON.error : 'Failed to start image generation.', 'danger');
                $btn.prop('disabled', false).html('<i class="bi bi-image me-1"></i>All Images');
            }
        });
    });

    // Track if polling is active (restart after completed/failed)
    var pollActive = true;

    // ─── Image Lightbox (click to enlarge) ───
    var lightboxSceneId = null;
    var lightboxUrl = null;

    $(document).on('click', '.img-thumb-click', function(e) {
        e.stopPropagation();
        lightboxSceneId = $(this).data('scene-id');
        lightboxUrl = $(this).data('url');
        var sceneIndex = $(this).closest('.en-para-card').find('.fw-semibold.small').first().text();
        $('#lightbox-title').text(sceneIndex || 'Image');
        $('#lightbox-img').attr('src', lightboxUrl);
        var modal = new bootstrap.Modal(document.getElementById('imageLightbox'));
        modal.show();
    });

    // Select from lightbox
    $('#lightbox-select').on('click', function() {
        if (!lightboxSceneId || !lightboxUrl) return;
        var $btn = $(this).prop('disabled', true);
        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/images/select',
            method: 'POST',
            data: JSON.stringify({ scene_image_id: lightboxSceneId, selected_url: lightboxUrl }),
            success: function() {
                showToast('Image selected!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('imageLightbox')).hide();
                enLoaded = false; enSceneImages = {}; loadEnScript();
            },
            error: function(xhr) {
                showToast(xhr.responseJSON ? xhr.responseJSON.error : 'Failed.', 'danger');
            },
            complete: function() { $btn.prop('disabled', false); }
        });
    });

    // Variation from lightbox
    function doVariation(strength) {
        if (!lightboxSceneId || !lightboxUrl) return;
        var $modal = $('#imageLightbox .modal-footer');
        $modal.find('.btn').prop('disabled', true);
        $modal.find('#lightbox-vary-' + strength).html(
            '<span class="spinner-border spinner-border-sm" style="width:14px;height:14px;"></span> ' +
            (strength === 'subtle' ? 'Subtle' : 'Strong') + '...'
        );
        $.ajax({
            url: '/pipeline/api/' + RUN_ID + '/images/vary',
            method: 'POST',
            data: JSON.stringify({ scene_image_id: lightboxSceneId, source_url: lightboxUrl, strength: strength }),
            success: function() {
                showToast('Variation generated! (' + strength + ')', 'success');
                bootstrap.Modal.getInstance(document.getElementById('imageLightbox')).hide();
                enLoaded = false; enSceneImages = {}; loadEnScript();
            },
            error: function(xhr) {
                showToast(xhr.responseJSON ? xhr.responseJSON.error : 'Variation failed.', 'danger');
            },
            complete: function() {
                $modal.find('.btn').prop('disabled', false);
                $('#lightbox-vary-subtle').html('<i class="bi bi-brush me-1"></i>Subtle');
                $('#lightbox-vary-strong').html('<i class="bi bi-lightning me-1"></i>Strong');
            }
        });
    }
    $('#lightbox-vary-subtle').on('click', function() { doVariation('subtle'); });
    $('#lightbox-vary-strong').on('click', function() { doVariation('strong'); });

    // Download all audio files
    $('#btn-download-all-audio').on('click', function() {
        $('.en-para-audio a[href$="/download"]').each(function(i) {
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
            success: function() {
                showToast('Step started.', 'info');
                if (!pollActive) { pollActive = true; pollStatus(); }
            },
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
            success: function() {
                showToast('Production started!', 'success');
                if (!pollActive) { pollActive = true; pollStatus(); }
            },
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
