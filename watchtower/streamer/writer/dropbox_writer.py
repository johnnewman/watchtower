import base64
import dropbox
import logging
import os
from . import byte_writer
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

logger = None


class DropboxWriter(byte_writer.ByteWriter):
    """
    A class that accumulates bytes up to the ``file_chunk_size`` to upload to
    Dropbox as an individual file. Creates additional files as the chunk size
    is reached. If a public key pem path is supplied, the video data will be
    encrypted and the random symmetric encryption key will be padded to the
    front of the file. Fernet encryption is used. The key itself is encrypted
    using the public key.
    """

    def __init__(self, full_path, dropbox_token, file_chunk_size=3, public_pem_path=None):
        """
        :param full_path: The full path of the file.
        :param dropbox_token: Token that will be supplied to Dropbox.
        :param file_chunk_size: A maximum size, in bytes, before a new file
        will be created. Actual size will be larger if encryption is used.
        :param public_pem_path: A path to the public key to encrypt each file's
        encryption key.
        """
        super(DropboxWriter, self).__init__(full_path)
        self.__dropbox_token = dropbox_token
        self.__dbx = dropbox.Dropbox(dropbox_token)
        self.__file_chunk_size = file_chunk_size
        self.__file_count = 0
        self.__byte_pool = ''.encode()
        self.__public_key = None
        if public_pem_path:
            with open(public_pem_path, "rb") as public_key_file:
                self.__public_key = serialization.load_pem_public_key(public_key_file.read(), backend=default_backend())

    def append_bytes(self, bts, close=False):
        self.__append_bytes(bts, close, False)

    def __append_bytes(self, bts, close=False, ignore_previous_bytes=False):
        """
        Private function that allows us to ignore the data that has accumulated
        in the ``__byte_pool``. This is only useful when breaking the data into
        files.

        :param bts: The bytes to append to the pool.
        :param close: If true, this uploads all the data supplied.
        :param ignore_previous_bytes: If true, ignores what is stored in
        ``__byte_pool``.
        """
        global logger
        if logger is None:
            logger = logging.getLogger(__name__)

        if not ignore_previous_bytes:
            bts = self.__byte_pool + bts
            total_available_space = self.__file_chunk_size - len(bts)
            if len(bts) > total_available_space:
                # Break the bytes into max sized smaller chunks.
                logger.debug('Attempting to upload beyond max size. Splitting.')
                sub_bytes = bts[:self.__file_chunk_size]
                while len(sub_bytes) == self.__file_chunk_size:
                    self.__append_bytes(sub_bytes, close=True, ignore_previous_bytes=True)  # Save each slice.
                    bts = bts[self.__file_chunk_size:]  # Remove the slice.
                    sub_bytes = bts[:self.__file_chunk_size]  # Fetch the next slice.
                bts = sub_bytes  # This will now be the last chunk, under the size limit.
            self.__byte_pool = bts

        if close:
            if self.__public_key:
                fernet_key = Fernet.generate_key()
                encrypted_fernet_key = self.__public_key.encrypt(fernet_key,
                                                                 padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                                              algorithm=hashes.SHA256(),
                                                                              label=None))
                encoded_fernet_key = base64.b64encode(encrypted_fernet_key)
                encrypted_bytes = Fernet(fernet_key).encrypt(bts)
                bts = str(len(encoded_fernet_key)).encode() + ' '.encode() + encoded_fernet_key + encrypted_bytes

            path, extension = os.path.splitext(self.full_path)
            full_path = path + str(self.__file_count) + extension
            self.__dbx.files_upload(bts, full_path)
            logger.debug('Uploaded file \"%s\"' % full_path)
            self.__file_count += 1
