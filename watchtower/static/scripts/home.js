$(document).ready(function () { 
    
    $('#play-mjpeg').click(function (e) {
        $('#mjpeg-stream').attr('src', 'mjpeg');
    });

    $('#pause-mjpeg').click(function (e) {
        $('#mjpeg-stream').attr('src', '');
    });

    $('#start').click(function (e) {
        $('#start-spinner').show();
        change_status('start')
    });

    $('#stop').click(function (e) {
        $('#stop-spinner').show();
        change_status('stop')
    });

    function change_status(endpoint) {
        $.ajax({
            type: 'GET',
            url: "api/" + endpoint,
            dataType: 'json',
            success: function (result, status, xhr) {
                parse_status_response(result)
                $('#stop-spinner').hide();
                $('#start-spinner').hide();
            },
            error: function (xhr, status, error) {
                alert('Result: ' + status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText)
                $('#stop-spinner').hide();
                $('#start-spinner').hide();
            }
        });
    }

    function parse_status_response(result) {
        console.log(result)
        if (result['monitoring'] == true) {
            console.log('Monitoring')
            $('#status').text('running');
        } else {
            console.log('Not monitoring')
            $('#status').text('stopped');
        }
    }
    
  });