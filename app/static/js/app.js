$(document).ready(function() {
    // Update current time
    function updateTime() {
        var now = new Date();
        var timeStr = now.toLocaleString('ko-KR', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        });
        $('#current-time').text(timeStr);
    }
    updateTime();
    setInterval(updateTime, 60000);

    // CSRF-safe AJAX setup (for future use)
    $.ajaxSetup({
        contentType: 'application/json',
        dataType: 'json'
    });

    // Flash message auto-dismiss
    setTimeout(function() {
        $('.alert-dismissible').fadeOut();
    }, 5000);
});

// Utility: show toast notification
function showToast(message, type) {
    type = type || 'info';
    var alertClass = 'alert-' + type;
    var $alert = $('<div class="alert ' + alertClass + ' alert-dismissible fade show position-fixed" ' +
        'style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;" role="alert">' +
        message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
        '</div>');
    $('body').append($alert);
    setTimeout(function() { $alert.fadeOut(function() { $alert.remove(); }); }, 4000);
}

// Utility: format date
function formatDate(isoStr) {
    if (!isoStr) return '-';
    var d = new Date(isoStr);
    return d.toLocaleDateString('ko-KR') + ' ' + d.toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'});
}
