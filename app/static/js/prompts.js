$(document).ready(function() {
    var editingPrompt = null;

    function loadPrompts() {
        $.getJSON('/prompts/api/list', function(data) {
            var $list = $('#prompts-list');
            $list.empty();
            if (!data.prompts || data.prompts.length === 0) {
                $list.html('<div class="col-12"><p class="text-muted text-center py-4">No prompts yet. Click "New Prompt" to create one.</p></div>');
                return;
            }
            data.prompts.forEach(function(p) {
                $list.append(
                    '<div class="col-md-6 col-lg-4">' +
                    '  <div class="card stat-card h-100 prompt-card" data-name="' + p.name + '" style="cursor:pointer;">' +
                    '    <div class="card-body">' +
                    '      <h6 class="card-title"><i class="bi bi-file-earmark-code me-1"></i>' + p.name + '</h6>' +
                    '      <p class="card-text text-muted small">' + (p.description || 'No description') + '</p>' +
                    '      <small class="text-muted">' + (p.updated_at || '') + '</small>' +
                    '    </div>' +
                    '  </div>' +
                    '</div>'
                );
            });
        });
    }

    loadPrompts();

    // New prompt
    $('#btn-new-prompt').on('click', function() {
        editingPrompt = null;
        $('#prompt-editor-title').text('New Prompt');
        $('#prompt-name').val('').prop('readonly', false);
        $('#prompt-description').val('');
        $('#prompt-template').val('');
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
            $('#prompt-description').val(data.description || '');
            $('#prompt-template').val(data.template || '');
            $('#btn-delete-prompt').show();
            new bootstrap.Modal('#promptEditorModal').show();
        });
    });

    // Save prompt
    $('#btn-save-prompt').on('click', function() {
        var name = $('#prompt-name').val().trim();
        var desc = $('#prompt-description').val().trim();
        var template = $('#prompt-template').val();

        if (!name) { showToast('Name is required.', 'warning'); return; }
        if (!template) { showToast('Template is required.', 'warning'); return; }

        var method = editingPrompt ? 'PUT' : 'POST';
        var url = editingPrompt ? '/prompts/api/' + editingPrompt : '/prompts/api/';

        $.ajax({
            url: url,
            method: method,
            data: JSON.stringify({name: name, description: desc, template: template}),
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
