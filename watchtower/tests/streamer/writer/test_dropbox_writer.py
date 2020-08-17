import math
import os
import pytest
import sys
import subprocess
import time

# Add the watchtower package to the path.
watchtower_path = os.path.dirname(os.path.realpath(__file__))
for i in range(3):
    watchtower_path = os.path.split(watchtower_path)[0]
sys.path.insert(0, watchtower_path)
from watchtower.streamer.writer import dropbox_writer
from watchtower.streamer.writer.disk_writer import DiskWriter


def test_dropbox_writer_integration(writer, random_data, tmp_path):
    """
    Integration test to feed a DropboxWriter chunks of data and verify that the
    decrypted data is identical to the input data. A MockDropboxUploader is
    used to output to the tmp_path instead of Dropbox.
    """

    # Append chunks of bytes to the DropboxWriter instance. This simulates a
    # live feed.
    append_count = 20
    amount_to_read = len(random_data)//append_count
    for i in range(append_count):
        data = random_data[i*amount_to_read:(i+1) * amount_to_read]
        writer.append_bytes(data, close=(i == append_count-1)) # Close on the last chunk.

    # Wait for writers to stop.
    while not writer.is_finished_writing():
        time.sleep(0.05)

    # Read in all of the data that the DropboxWriter output to disk.
    files = os.listdir(tmp_path)
    files.sort() # Sort them into [test_file0.bin, test_file1.bin, ...]
    written_data = ''.encode()
    for file_name in files:
        with open(os.path.join(tmp_path, file_name), 'rb') as f:
            written_data += f.read()
    
    # Assert that multiple files were written to disk.
    assert(len(files) > 0)
    assert(len(files) == math.ceil(len(random_data)/dropbox_writer.DEFAULT_FILE_CHUNK_SIZE))
    # Assert the writer's input data is identical to the data output to disk.
    assert(written_data == random_data)

def test_dropbox_writer_encrypted_integration(encrypted_writer, random_data, tmp_path):
    """
    Integration test to feed a DropboxWriter chunks of data, decrypt the
    output, and verify that the decrypted data is identical to the input data.
    A MockDropboxUploader is used to output to the tmp_path instead of Dropbox.
    This also serves as a good test for decrypt.py, by decrypting each file
    output by the DropboxWriter and verifying that the bytes are identical to
    the original.
    """

    # Append chunks of bytes to the DropboxWriter instance. This simulates a
    # live feed.
    append_count = 20
    amount_to_read = len(random_data)//append_count
    for i in range(append_count):
        data = random_data[i*amount_to_read:(i+1) * amount_to_read]
        encrypted_writer.append_bytes(data, close=(i == append_count-1)) # Close on the last chunk.
    
    # Wait for writers to stop.
    while not encrypted_writer.is_finished_writing():
        time.sleep(0.05)

    # The installation path is one directory up from the package path.
    installation_path = os.path.split(watchtower_path)[0]
    private_key_path = os.path.join(tmp_path, 'private.pem')
    python_exec_path = os.path.join(installation_path, 'venv', 'bin', 'python')
    decrypt_script_path = os.path.join(installation_path, 'ancillary', 'decryption', 'decrypt.py')

    # Read in all of the data that the DropboxWriter output to disk. Ignore the .pem files.
    files = list(filter(lambda name: name.endswith('.bin'), os.listdir(tmp_path)))
    files.sort() # Sort them into [test_file0.bin, test_file1.bin, ...]
    written_data = ''.encode()
    for file_name in files:
        in_path = os.path.join(tmp_path, file_name)
        out_path = os.path.join(tmp_path, file_name + '.dec')

        # Decrypt each file using the decrypt.py program.
        subprocess.call([python_exec_path, decrypt_script_path,
                        '-k', private_key_path,
                        '-i', in_path,
                        '-o', out_path])
        
        # Append the decrypted data.
        with open(out_path, 'rb') as f:
            written_data += f.read()
            
    # Assert that multiple files were written to disk.
    assert(len(files) > 1)
    assert(len(files) == math.ceil(len(random_data)/dropbox_writer.DEFAULT_FILE_CHUNK_SIZE))
    # Assert the writer's input data is identical to the data output to disk.
    assert(written_data == random_data)

# ---- Fixtures

@pytest.fixture
def random_data():
    return os.urandom(1024*1024*10) # 10 megabytes

@pytest.fixture
def writer(tmp_path):
    return dropbox_writer.DropboxWriter(os.path.join(tmp_path, 'test_file.bin'),
                                        dropbox_token="",
                                        test_dropbox_uploader=MockDropboxUploader())

@pytest.fixture
def encrypted_writer(tmp_path):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding

    # Generate a private and public key and save these in the tmp_path.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    private_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                            format=serialization.PrivateFormat.PKCS8,
                                            encryption_algorithm=serialization.NoEncryption())
    with open(os.path.join(tmp_path, 'private.pem'), 'wb') as private_out:
        private_out.write(private_pem)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(os.path.join(tmp_path, 'public.pem'), 'wb') as public_out:
        public_out.write(public_pem)
    
    return dropbox_writer.DropboxWriter(os.path.join(tmp_path, 'test_file.bin'),
                                        dropbox_token="",
                                        public_pem_path=os.path.join(tmp_path, 'public.pem'),
                                        test_dropbox_uploader=MockDropboxUploader())

# ---- Mock objects

class MockDropboxUploader():
    """
    Mock object to be used in place of a dropbox object. Each call to
    files_upload will create a new file on disk.
    """
    def files_upload(self, bts, path):
        writer = DiskWriter(path)
        writer.append_bytes(bts, close=True)
