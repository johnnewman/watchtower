$(document).ready(function(){

    var buttons = $('button')
    for (i = 0; i < buttons.length; i++) { 
        button = buttons[i];
        if (button.id.startsWith('recording-download-button-')) {
            button.addEventListener("click", downloadRecording)
        } else if (button.id.startsWith('recording-delete-button-')) {
            button.addEventListener("click", deleteRecording)
        }
    }

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