$(document).ready(function () { 

    $('#play-mjpeg').click(function (e) {
        loadStream()
    });

    $('#pause-mjpeg').click(function (e) {
        cancelStream()
    });

    $('#start').click(function (e) {
        $('#start-spinner').show();
        changeStatus('start')
    });

    $('#stop').click(function (e) {
        $('#stop-spinner').show();
        changeStatus('stop')
    });

    /**
     * Turns Watchtower on and off, depending on the endpoint supplied.
     * @param {String} endpoint The endpoint to hit. Either "start" or "stop".
     */
    function changeStatus(endpoint) {
        $.ajax({
            type: 'GET',
            url: "api/" + endpoint,
            dataType: 'json',
            success: function (result, status, xhr) {
                parseStatusResponse(result)
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

    /**
     * Updates the UI based on the response from changeStatus().
     * @param {Anything} result The result from the ajax call.
     */
    function parseStatusResponse(result) {
        if (result['monitoring'] == true) {
            console.log('Monitoring')
            $('#status').text('running');
        } else {
            console.log('Not monitoring')
            $('#status').text('stopped');
        }
    }

    // The global streaming request.
    var xhr = null

    /**
     * Starts a request to Watchtower's mjpeg endpoint. This will read the
     * multipart response and continuously update the <img> element displaying
     * the feed.
     */
    function loadStream() {

        if (xhr !== null) {
            console.log('Request already running. Restarting....')
            xhr.abort()
        }

        xhr = new XMLHttpRequest(),
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
                        // Find the next image tag.
                        lastContentLength = contentLength[contentLength.length-1]
                        index = xhr.responseText.lastIndexOf(lastContentLength)
                        loadedImageForIndex = false
                    }
                    var body = xhr.responseText.substring(index + lastContentLength.length)
                    if (updateImageUsingContentLength(body, parseInt(lastContentLength.split(' ')[1]))) {
                        return
                    }
                    console.log('Image data not cleanly separated by Content-Length. Manually searching.')
                    if (updateImageUsingBoundary(body)) {
                        console.log('Found image.')
                        return
                    }
                    console.log('Could not parse image data.')
                }
            } else {
                if (xhr.status != 0) {
                    console.log('MJPEG Stream error: ' + xhr.status + ' ' + xhr.statusText);
                }
            }
        };
        xhr.send();

        /**
         * Extracts the image data in the body using the provided frameLength.
         * This returns true if it can read all of the image data and the data
         * remaining is either empty or starts with the next multipart boundary
         * string. This method is the preferred approach when compared to
         * updateImageUsingBoundary().
         * @param {String} body The string to extract the image.
         * @param {Number} frameLength The length of the image data.
         */
        function updateImageUsingContentLength(body, frameLength) {
            body = body.replace(/^\s+/g, ''); // Remove leading whitespace.
            if (body.length >= frameLength) {
                var imageData = body.substring(0, frameLength)
                var remainder = body.substring(frameLength).replace(/^\s+/g, '');
                var successful = (imageData.length == frameLength && (remainder.length == 0 || remainder.startsWith('--FRAME')))
                if (successful) {
                    updateImage(imageData)
                }
                return successful
            }
            return false
        }

        /**
         * Searches the body for the next occurrence of the boundary string.
         * The data between the body start and the next occurrence is treated
         * as the image data.
         * 
         * This is less ideal than updateImageUsingContentLength(...) because
         * this method will require two multipart responses since the second
         * response will contain the boundary string that must be parsed.
         * Because we always start the parsing process with the most recent
         * Content-Length, this will result in dropped frames.
         * 
         * Example response:
         * 
         * --FRAME
         * Content-Type: image/jpeg
         * Content-Length: 123
         * 
         * <image1 data>
         *                   <-- End of response 1
         * --FRAME
         * Content-Type: image/jpeg
         * Content-Length: 123
         * 
         * <image2 data>
         *                   <-- End of response 2
         * @param {String} body The string to search for the image data.
         */
        function updateImageUsingBoundary(body) {
            var nextFrameIndex = body.indexOf('--FRAME')
            if (nextFrameIndex !== -1) {
                var imageData = body.substring(0, nextFrameIndex)                        
                updateImage(imageData)
                return true
            }
            return false
        }

        function updateImage(imageData) {
            imageData = imageData.trim()
            $('#mjpeg-stream').attr('src', 'data:image/jpeg;base64, ' + imageData)
            loadedImageForIndex = true
        }
    }

    /**
     * Stops and disposes of the connection to Watchtower's mjpeg endpoint.
     */
    function cancelStream() {
        if (xhr !== null) {
            console.log('Cancelling stream.')
            xhr.abort()
            xhr = null
            return
        }
    }
});