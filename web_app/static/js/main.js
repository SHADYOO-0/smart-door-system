document.addEventListener('DOMContentLoaded', function() {
    const openDoorBtn = document.getElementById('openDoorBtn');
    const takePhotoBtn = document.getElementById('takePhotoBtn');
    const doorCameraImage = document.getElementById('doorCameraImage');
    const imageTimestampSpan = document.getElementById('imageTimestamp');

    if (openDoorBtn) {
        openDoorBtn.addEventListener('click', function() {
            fetch('/open-door', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                console.log('Open door response:', data);
                if(data.success) alert(data.message || 'Door command sent!');
                else alert('Error: ' + (data.message || 'Could not send command.'));
            })
            .catch(error => {
                console.error('Error opening door:', error);
                alert('Failed to send open door command.');
            });
        });
    }

    if (takePhotoBtn && doorCameraImage) {
        takePhotoBtn.addEventListener('click', function() {
            takePhotoBtn.disabled = true;
            takePhotoBtn.textContent = 'Requesting...';

            fetch('/request-photo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                console.log('Take photo response:', data);
                if (data.success) {
                    setTimeout(updateCameraImage, 3000);
                } else {
                    alert('Error: ' + (data.message || 'Could not request photo.'));
                    takePhotoBtn.disabled = false;
                    takePhotoBtn.textContent = 'Take New Photo';
                }
            })
            .catch(error => {
                console.error('Error requesting photo:', error);
                alert('Failed to request photo.');
                takePhotoBtn.disabled = false;
                takePhotoBtn.textContent = 'Take New Photo';
            });
        });

        function updateCameraImage() {
            fetch('/get_new_image_url')
            .then(response => response.json())
            .then(data => {
                if (data.imageUrl) {
                    doorCameraImage.src = data.imageUrl;
                    if (imageTimestampSpan) {
                         const now = new Date();
                         imageTimestampSpan.textContent = now.toLocaleTimeString();
                    }
                }
            })
            .catch(error => console.error('Error fetching new image URL:', error))
            .finally(() => {
                if (takePhotoBtn) {
                   takePhotoBtn.disabled = false;
                   takePhotoBtn.textContent = 'Take New Photo';
                }
            });
        }

        if (doorCameraImage && doorCameraImage.src && imageTimestampSpan) {
             const now = new Date();
             imageTimestampSpan.textContent = now.toLocaleTimeString();
        }
    }
});
