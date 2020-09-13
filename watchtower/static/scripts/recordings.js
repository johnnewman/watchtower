$(document).ready(function(){

    // Iterate over every button, adding listeners to download and delete.
    var buttons = $('button')
    for (i = 0; i < buttons.length; i++) { 
        button = buttons[i];
        if (button.id.startsWith('recording-download-button-')) {
            button.addEventListener("click", downloadRecording)
        } else if (button.id.startsWith('recording-delete-button-')) {
            button.addEventListener("click", deleteRecording)
        }
    }

    /**
     * Creates a temporary <a> tag on the page that will download the selected
     * recording day & time. This tag is programmatically clicked.
     */
    function downloadRecording(event) {
        var button = this
        var datetime = button.id.substring('recording-download-button-'.length)
        var elements = datetime.split(" ")
        var downloadLink = document.createElement('a'); 
        downloadLink.setAttribute('href', encodeURIComponent('api/recordings/'+elements[0]+'/'+elements[1]+'/video')); 
        downloadLink.setAttribute('download', elements[0]+';'+elements[1]); 
        document.body.appendChild(downloadLink);  
        downloadLink.click(); 
        document.body.removeChild(downloadLink); 
    }
    
    /**
     * Deletes the selected recording using an ajax call. If the call was
     * successful, the row for the day & time will be removed.
     */
    function deleteRecording(event) {
        var button = this
        var datetime = button.id.substring('recording-delete-button-'.length)
        var elements = datetime.split(" ")
        $.ajax({
            type: 'DELETE',
            url: 'api/recordings/'+elements[0]+'/'+elements[1],
            success: function (result, status, xhr) {
                var query = $.escapeSelector('list-group-'+elements[0]+' '+elements[1])
                $('#'+query).hide()
            },
            error: function (xhr, status, error) {
                console.log(status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText)
            }
        });
    }
  })