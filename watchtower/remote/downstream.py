import logging
import os
import requests
import uuid
from threading import Thread

def __poll_server(url, camera_name, instance_path):
    uuid_string = None
    uuid_path = os.path.join(instance_path, 'uuid')
    if not os.path.exists(uuid_path):
        with open(uuid_path, 'w') as uuid_file:
            logging.getLogger(__name__).info('Creating new uuid file.')
            uuid_string = str(uuid.uuid4())
            uuid_file.write(uuid_string)
    else:
        with open(os.path.join(instance_path, 'uuid'), 'r') as uuid_file:
            logging.getLogger(__name__).info('Using existing uuid file.')
            uuid_string = uuid_file.read()

    if uuid_string is None:
        logging.getLogger(__name__).error('Failed to find uuid. Aborting')
        return
    try:
        response = requests.post(
            url,
            verify=os.path.join(os.environ['CERT_DIR'], os.environ['DOWNSTREAM_CA']),
            cert=(
                os.path.join(os.environ['CERT_DIR'], os.environ['CLIENT_CERT']),
                os.path.join(os.environ['CERT_DIR'], os.environ['CLIENT_KEY'])
            ),
            json={
                'name': camera_name,
                'id': uuid_string
            }
        )
        if not response.ok:
            logging.getLogger(__name__).error('Error polling server. Code: %i' % response.status_code)
    except Exception as ex:
        logging.getLogger(__name__).exception(f'Exception connecting to downstream server.')
    
def poll_server(camera, instance_path):
    poll_thread = Thread(
        name='poll_thread',
        target=__poll_server,
        args=(
            f"https://{os.environ['DOWNSTREAM_SERVER_IP']}/api/cameras",
            camera.name,
            instance_path
        )
    )
    logging.getLogger(__name__).info('Starting poll thread.')
    poll_thread.start()