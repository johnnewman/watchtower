$(document).ready(function () { 

    $('#play-mjpeg').click(function (e) {
        loadStream()
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

    function loadStream() {
        const xhr = new XMLHttpRequest(),
            method = "GET",
            url = "mjpeg?encoding=base64";
        xhr.open(method, url, true);

        var index = 0
        var lastContentLength = null
        var loadedImageForIndex = true

        xhr.onreadystatechange = function () {
            if (xhr.status === 200) {
                var contentLength = xhr.responseText.match(/Content-Length: \d+$/gm)
                if (contentLength !== null) {
                    if (loadedImageForIndex) {
                        // Find the next image tag
                        lastContentLength = contentLength[contentLength.length-1]
                        index = xhr.responseText.lastIndexOf(lastContentLength)
                        loadedImageForIndex = false
                    }
                    var body = xhr.responseText.substring(index + lastContentLength.length)
                    var nextFrameIndex = body.indexOf('--FRAME')
                    if (nextFrameIndex !== -1) {
                        var imageData = body.substring(0, nextFrameIndex)                        
                        imageData = imageData.trim()
                        console.log('Length of frame: ' + imageData.length + ' Provided length: ' + lastContentLength)
                        $('#mjpeg-stream').attr('src', 'data:image/jpeg;base64, ' + imageData)
                        loadedImageForIndex = true
                    }
                }
            } else {
                console.log('MJPEG Stream error: ' + xhr.status + ' ' + xhr.statusText);
            }
        };
        xhr.send();
    }

     
    
  });