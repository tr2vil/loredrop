$(document).ready(function() {
    // Update current time
    function updateTime() {
        var now = new Date();
        var timeStr = now.toLocaleString('ko-KR', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        });
        $('#current-time, #current-time-mobile').text(timeStr);
    }
    updateTime();
    setInterval(updateTime, 60000);

    // Mobile sidebar toggle
    $('#btn-sidebar-toggle').on('click', function() {
        $('#sidebar').toggleClass('open');
        $('#sidebar-overlay').toggleClass('d-none show');
    });
    $('#sidebar-overlay').on('click', function() {
        $('#sidebar').removeClass('open');
        $(this).addClass('d-none').removeClass('show');
    });
    // Close sidebar on nav link click (mobile)
    $('#sidebar .nav-link').on('click', function() {
        if (window.innerWidth < 768) {
            $('#sidebar').removeClass('open');
            $('#sidebar-overlay').addClass('d-none').removeClass('show');
        }
    });

    // AJAX defaults
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
    var $alert = $('<div class="alert alert-' + type + ' alert-dismissible fade show position-fixed shadow-sm" ' +
        'style="top: 16px; right: 16px; z-index: 9999; min-width: 280px; max-width: 90vw; font-size: 0.9rem;" role="alert">' +
        message +
        '<button type="button" class="btn-close btn-close-sm" data-bs-dismiss="alert"></button>' +
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
