import base64
import dropbox
import logging
import os
import queue
import sys
import time
from . import byte_writer
from collections import namedtuple
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from threading import Thread, Lock

THREAD_COUNT = 1
DEFAULT_FILE_CHUNK_SIZE = 512*1024 # 512 KB
NumberedFile = namedtuple('NumberedFile', 'priority_number bytes close')


class DropboxWriter(byte_writer.ByteWriter):
    """
    A class that accumulates bytes to upload to Dropbox and uploads chunks sized
    according to the ``file_chunk_size``. If the provided size is <= 0, the file
    is not broken apart and only one upload thread is used. Otherwise, this
    class creates additional files as the chunk size is reached.
    
    If the path to a public key file is supplied, the bytes will be encrypted
    and the random symmetric encryption key used to encrypt the data will
    itself be encrypted and prepended to the front of the file. Fernet
    encryption is used. The key itself is encrypted using the public key.
    """

    def __init__(self, full_path, dropbox_token, file_chunk_size=DEFAULT_FILE_CHUNK_SIZE, public_pem_path=None, test_dropbox_uploader=None):
        """
        :param full_path: The full path of the file.
        :param dropbox_token: Token that will be supplied to Dropbox.
        :param file_chunk_size: A maximum size, in bytes, before a new file
        will be created. Actual size will be larger if encryption is used.
        :param public_pem_path: A path to the public key to encrypt each file's
        encryption key.
        :param test_dropbox_uploader: An object that will be used in place of
        the normal Dropbox uploader. Useful for testing. Object must implement
        the files_upload(bytes, path) method.
        """
        super(DropboxWriter, self).__init__(full_path)
        if file_chunk_size <= 0:
            self.__file_chunk_size = sys.maxsize
        else:
            self.__file_chunk_size = file_chunk_size
        
        self.__file_count = 0
        self.__byte_pool = ''.encode()

        dbx = None
        if test_dropbox_uploader is None:
            dbx = dropbox.Dropbox(dropbox_token)
        else:
            dbx = test_dropbox_uploader
        public_key = None
        if public_pem_path:
            with open(public_pem_path, "rb") as public_key_file:
                public_key = serialization.load_pem_public_key(public_key_file.read(), backend=default_backend())
                
        if public_key is not None:
            logging.getLogger(__name__).debug('Using encryption!')

        path, extension = os.path.splitext(full_path)
        self.__uploader_threads = []
        thread_count = THREAD_COUNT if file_chunk_size > 0 else 1
        for i in range(thread_count):
            uploader = DropboxFileUploader(dbx, path, extension, public_key, i)
            self.__uploader_threads.append(uploader)
            uploader.start()
        self.__thread_index = 0

    def append_bytes(self, bts, close=False):
        """
        This method will append the bytes to a small array. When enough bytes
        have been appended, one or more chunks is broken off and distributed to
        an uploader thread.
        """
        self.__byte_pool += bts
        logging.getLogger(__name__).debug('Byte pool length: %i bytes' % len(self.__byte_pool))
        if len(self.__byte_pool) < self.__file_chunk_size and not close:
            return # Wait for more data.
        
        # Break apart the bytes and distribute each chunk to an uploader.
        sub_bytes = self.__byte_pool[:self.__file_chunk_size]
        while len(sub_bytes) == self.__file_chunk_size:
            self.__distribute_file_bytes(sub_bytes)
            self.__byte_pool = self.__byte_pool[self.__file_chunk_size:]  # Remove the chunk.
            sub_bytes = self.__byte_pool[:self.__file_chunk_size]  # Fetch the next chunk.
        self.__byte_pool = sub_bytes  # The last chunk, smaller than file_chunk_size.
        
        if close == True:
            # Dump the remaining data.
            if len(self.__byte_pool) > 0:
                self.__distribute_file_bytes(self.__byte_pool, close=True)
            # Stop all threads.
            list(map(lambda x: x.stop(), self.__uploader_threads))

    def is_finished_writing(self):
        for uploader_thread in self.__uploader_threads:
            if uploader_thread.is_alive():
                return False
        return True
    
    def __distribute_file_bytes(self, bts, close=False):
        """
        Creates a unique file with the supplied bytes and passes this to an
        uploader thread in a round robin fashion.
        """
        numbered_file = NumberedFile(self.__file_count, bts, close)
        self.__uploader_threads[self.__thread_index].append_file(numbered_file)
        logging.getLogger(__name__).debug('Distributed file to DropboxFileUploader #%i' % self.__thread_index)
        self.__file_count += 1
        if self.__thread_index == len(self.__uploader_threads) - 1:
            self.__thread_index = 0
        else:
            self.__thread_index += 1


class DropboxFileUploader(Thread):
    """
    Threaded class used to accumulate data that needs to be uploaded to Dropbox.
    If a public key is supplied, this class will optionally encrypt the data
    before uploading.
    """

    def __init__(self, dbx: dropbox.Dropbox, path: str, extension: str, public_key=None, log_number=0):
        super(DropboxFileUploader, self).__init__()
        self.__dbx = dbx
        self.__path = path
        self.__extension = extension
        self.__log_number = log_number
        self.__stop = False
        self.__lock = Lock()
        self.__queue = queue.PriorityQueue()
        self.__upload_session = None
        self.__cursor = None
        self.__key = None

        if public_key is not None:
            # Generate the key for encryption.
            self.__key = Fernet.generate_key()

            # Encrypt and base64-encode the key.
            encrypted_fernet_key = public_key.encrypt(
                self.__key,
                padding.OAEP(
                    mgf=padding.MGF1(
                        algorithm=hashes.SHA256()
                    ),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            self.__encoded_key = base64.b64encode(encrypted_fernet_key)

    def __should_stop(self):
        self.__lock.acquire()
        should_stop = self.__stop
        self.__lock.release()
        return should_stop

    def stop(self):
        self.__lock.acquire()
        self.__stop = True
        self.__lock.release()

    def append_file(self, numbered_file: NumberedFile):
        self.__queue.put(numbered_file)

    def __logger(self) -> logging.Logger:
        return logging.getLogger("%s.%i" % (__name__, self.__log_number))

    def __encrypt(self, numbered_file: NumberedFile):
        """
        Encrypts the supplied file's data using the encryption key.
        """
        if self.__key is None:
            self.__logger().debug('Skipping encryption.')
            return numbered_file

        start_time = time.time()

        # --Chunk <size>
        # <encrypted data>
        # --Chunk <size>
        # ...
        encrypted_bytes = Fernet(self.__key).encrypt(numbered_file.bytes)
        encrypted_bytes = b'\n--Chunk ' + str(len(encrypted_bytes)).encode() + \
            b'\n' + encrypted_bytes

        self.__logger().debug('Done encrypting. Took %.2f sec.' % (time.time() - start_time))

        # For the first chunk, prepend the key.
        if numbered_file.priority_number == 0: 
            encrypted_bytes = self.__encoded_key + encrypted_bytes

        return numbered_file._replace(bytes=encrypted_bytes)

    def __upload(self, numbered_file: NumberedFile):
        """
        The final step in the upload process. When this is passed the file, the
        data is already encrypted & prepared for upload.
        """

        # Single file upload.
        if numbered_file.priority_number == 0 and numbered_file.close:
            full_path = self.__path + self.__extension
            self.__logger().info('Uploading a single file: \"%s\".' % full_path)
            self.__dbx.files_upload(numbered_file.bytes, full_path)
            return

        # Start the upload session.
        if self.__upload_session is None:
            self.__logger().debug('Creating an upload session with Dropbox.')
            self.__upload_session = self.__dbx.files_upload_session_start(numbered_file.bytes)
            self.__cursor = dropbox.files.UploadSessionCursor(
                session_id=self.__upload_session.session_id,
                offset=len(numbered_file.bytes)
            )
            return

        # Append more chunks.
        if not numbered_file.close:
            self.__logger().debug('Appending chunk %i.', numbered_file.priority_number)
            self.__dbx.files_upload_session_append_v2(
                numbered_file.bytes,
                self.__cursor
            )
            self.__cursor.offset += len(numbered_file.bytes)
            return

        # Commit & close the session.
        full_path = self.__path + self.__extension
        commit = dropbox.files.CommitInfo(
            path=full_path,
            mode=dropbox.files.WriteMode.add
        )
        self.__dbx.files_upload_session_finish(
            numbered_file.bytes,
            self.__cursor, 
            commit
        )
        self.__logger().info('Done uploading file: \"%s\".' % full_path)

    def run(self):
        self.__logger().debug('Uploader thread running.')
        # Only stop if the queue is also empty.
        while not self.__should_stop() or not self.__queue.empty():
            try:
                numbered_file = self.__queue.get(block=True, timeout=0.5)
                self.__logger().debug('Ready to process file %i' % numbered_file.priority_number)
                self.__upload(self.__encrypt(numbered_file))
            except queue.Empty:
                pass
            except Exception as e:
                logging.getLogger(__name__).debug('Exception %s.' % e)
        self.__logger().debug('Uploader thread stopped.')
