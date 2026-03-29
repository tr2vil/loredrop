$(document).ready(function() {
    var editingPrompt = null;

    var STEP_LABELS = {
        'topic_generation': {label: 'Topic Generation', color: 'primary', icon: 'bi-lightbulb'},
        'script_generation': {label: 'Script Generation', color: 'success', icon: 'bi-file-earmark-text'},
        'scene_direction': {label: 'Scene Direction', color: 'info', icon: 'bi-image'},
        'tts': {label: 'TTS', color: 'warning', icon: 'bi-mic'},
        'image_generation': {label: 'Image Generation', color: 'danger', icon: 'bi-palette'},
        'other': {label: 'Other', color: 'secondary', icon: 'bi-gear'}
    };

    function getStepBadge(step) {
        var info = STEP_LABELS[step] || STEP_LABELS['other'];
        return '<span class="badge bg-' + info.color + ' bg-opacity-10 text-' + info.color + '">' +
               '<i class="bi ' + info.icon + ' me-1"></i>' + info.label + '</span>';
    }

    function truncate(str, len) {
        if (!str) return '<span class="text-muted fst-italic">Not set</span>';
        return str.length > len ? str.substring(0, len) + '...' : str;
    }

    // Step display order
    var STEP_ORDER = ['topic_generation', 'script_generation', 'scene_direction', 'tts', 'image_generation', 'other'];

    function loadPrompts() {
        $.getJSON('/prompts/api/list', function(data) {
            var $list = $('#prompts-list');
            $list.empty();
            if (!data.prompts || data.prompts.length === 0) {
                $list.html('<div class="col-12"><p class="text-muted text-center py-4">No prompts yet.</p></div>');
                return;
            }

            // Group prompts by step
            var groups = {};
            data.prompts.forEach(function(p) {
                var step = p.step || 'other';
                if (!groups[step]) groups[step] = [];
                groups[step].push(p);
            });

            // Render each step group in order
            STEP_ORDER.forEach(function(step) {
                if (!groups[step]) return;
                var info = STEP_LABELS[step] || STEP_LABELS['other'];

                var $section = $(
                    '<div class="col-12 mb-2">' +
                    '  <div class="d-flex align-items-center gap-2 mb-3">' +
                    '    <span class="badge bg-' + info.color + ' bg-opacity-10 text-' + info.color + '" style="font-size: 0.85rem; padding: 6px 12px;">' +
                    '      <i class="bi ' + info.icon + ' me-1"></i>' + info.label +
                    '    </span>' +
                    '    <hr class="flex-grow-1 my-0">' +
                    '  </div>' +
                    '  <div class="row g-3 prompt-group"></div>' +
                    '</div>'
                );

                var $row = $section.find('.prompt-group');
                groups[step].forEach(function(p) {
                    var hasSystem = p.system_prompt && p.system_prompt.length > 0;
                    var hasUser = p.user_prompt && p.user_prompt.length > 0;
                    var hasTemplate = !hasSystem && !hasUser && p.template && p.template.length > 0;

                    var indicators = '';
                    if (hasSystem) indicators += '<span class="badge bg-dark bg-opacity-10 text-dark me-1"><i class="bi bi-cpu me-1"></i>System</span>';
                    if (hasUser || hasTemplate) indicators += '<span class="badge bg-dark bg-opacity-10 text-dark"><i class="bi bi-person me-1"></i>User</span>';

                    $row.append(
                        '<div class="col-md-6">' +
                        '  <div class="card stat-card h-100 prompt-card" data-name="' + p.name + '" style="cursor:pointer;">' +
                        '    <div class="card-body py-3">' +
                        '      <h6 class="card-title mb-1"><i class="bi bi-file-earmark-code me-1"></i>' + p.name + '</h6>' +
                        '      <p class="card-text text-muted small mb-2">' + (p.description || 'No description') + '</p>' +
                        '      <div>' + indicators + '</div>' +
                        '    </div>' +
                        '  </div>' +
                        '</div>'
                    );
                });

                $list.append($section);
            });
        });
    }

    loadPrompts();

    // New prompt
    $('#btn-new-prompt').on('click', function() {
        editingPrompt = null;
        $('#prompt-editor-title').text('New Prompt');
        $('#prompt-name').val('').prop('readonly', false);
        $('#prompt-step').val('');
        $('#prompt-description').val('');
        $('#prompt-system').val('');
        $('#prompt-user').val('');
        $('#btn-delete-prompt').hide();
        new bootstrap.Modal('#promptEditorModal').show();
    });

    // Edit prompt
    $(document).on('click', '.prompt-card', function() {
        var name = $(this).data('name');
        editingPrompt = name;
        $.getJSON('/prompts/api/' + name, function(data) {
            $('#prompt-editor-title').text('Edit: ' + name);
            $('#prompt-name').val(name).prop('readonly', true);
            $('#prompt-step').val(data.step || '');
            $('#prompt-description').val(data.description || '');
            $('#prompt-system').val(data.system_prompt || '');
            // Fallback: old format had 'template' as single field
            $('#prompt-user').val(data.user_prompt || data.template || '');
            $('#btn-delete-prompt').show();
            new bootstrap.Modal('#promptEditorModal').show();
        });
    });

    // Save prompt
    $('#btn-save-prompt').on('click', function() {
        var name = $('#prompt-name').val().trim();
        if (!name) { showToast('Name is required.', 'warning'); return; }

        var payload = {
            name: name,
            step: $('#prompt-step').val(),
            description: $('#prompt-description').val().trim(),
            system_prompt: $('#prompt-system').val(),
            user_prompt: $('#prompt-user').val()
        };

        var method = editingPrompt ? 'PUT' : 'POST';
        var url = editingPrompt ? '/prompts/api/' + editingPrompt : '/prompts/api/';

        $.ajax({
            url: url,
            method: method,
            data: JSON.stringify(payload),
            success: function() {
                bootstrap.Modal.getInstance(document.getElementById('promptEditorModal')).hide();
                showToast('Prompt saved!', 'success');
                loadPrompts();
            },
            error: function() { showToast('Failed to save prompt.', 'danger'); }
        });
    });

    // Delete prompt
    $('#btn-delete-prompt').on('click', function() {
        if (!editingPrompt) return;
        if (!confirm('Delete prompt "' + editingPrompt + '"?')) return;
        $.ajax({
            url: '/prompts/api/' + editingPrompt,
            method: 'DELETE',
            success: function() {
                bootstrap.Modal.getInstance(document.getElementById('promptEditorModal')).hide();
                showToast('Prompt deleted.', 'info');
                loadPrompts();
            },
            error: function() { showToast('Failed to delete prompt.', 'danger'); }
        });
    });
});
