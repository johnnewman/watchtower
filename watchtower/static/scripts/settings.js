$(document).ready(function () {
    
    $('#apply-settings').click(function (e) {
        var params = {
            awb_mode: $('#awb-field').val(),
            brightness: parseInt($('#brightness-field').val()),
            contrast: parseInt($('#contrast-field').val()),
            exposure_mode: $('#exposure-mode-field').val(),
            exposure_compensation: parseInt($('#exposure-compensation-field').val()),
            image_effect: $('#image-effects-field').val(),
            iso: parseInt($('#iso-field').val()),
            meter_mode: $('#meter-mode-field').val(),
            rotation: parseInt($('#rotation-field').val()),
            saturation: parseInt($('#saturation-field').val()),
            sharpness: parseInt($('#sharpness-field').val()),
            video_denoise: $('#denoise-field').is(":checked")
        }
        apply_settings(params)
    });

    function apply_settings(params) {
        console.log('posting ' + JSON.stringify(params))
        $.ajax({
            type: 'POST',
            url: 'api/config',
            data: JSON.stringify(params),
            dataType: 'json',
            contentType: 'application/json',
            success: function (result, status, xhr) {
                console.log(result)
                $('#settings-success-alert').show()
                setTimeout(function() {
                    $('#settings-success-alert').hide();
                }, 3000);
            },
            error: function (xhr, status, error) {
                console.log(status + ' ' + error + ' ' + xhr.status + ' ' + xhr.statusText)
                $('#settings-error-alert').show()
                setTimeout(function() {
                    $('#settings-error-alert').hide();
                }, 3000); 
            }
        });
    }
})