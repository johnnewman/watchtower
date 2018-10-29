import dropbox
import logging
import os
from streamer.writer import ByteWriter

logger = None


class DropboxWriter(ByteWriter.ByteWriter):
    """
    A class that creates an upload session on Dropbox and writes all bytes to
    that session.  When ``file_chunk_size`` is reached, the session is closed
    and a new session opened.
    """

    def __init__(self, full_path, dropbox_token, file_chunk_size=None):
        """
        :param full_path: The full path of the file.
        :param dropbox_token: Token that will be supplied to Dropbox.
        :param file_chunk_size: A maximum size before a new file will be
        created.
        """
        super(DropboxWriter, self).__init__(full_path)
        self.__dropbox_token = dropbox_token
        self.__dbx = dropbox.Dropbox(dropbox_token)
        self.__file_chunk_size = file_chunk_size
        self.__file_count = 0
        self.__cursor = None
        self.__commit = None

    def append_bytes(self, byte_string, close=False):
        global logger
        if logger is None:
            logger = logging.getLogger(__name__)

        if self.__cursor is None:
            session_start_result = self.__dbx.files_upload_session_start(byte_string)
            self.__cursor = dropbox.files.UploadSessionCursor(session_start_result.session_id, offset=len(byte_string))
            path, extension = os.path.splitext(self.full_path)
            full_path = path + str(self.__file_count) + extension
            self.__commit = dropbox.files.CommitInfo(full_path, mode=dropbox.files.WriteMode.add)
            return

        if self.__file_chunk_size is not None and self.__cursor.offset + len(byte_string) >= self.__file_chunk_size:
            close = True
            logger.debug('Reached max file chunk size.')

        if close:
            self.__dbx.files_upload_session_finish(byte_string, self.__cursor, self.__commit)
            logger.debug('Closed file \"%s\"' % self.__commit.path)
            self.__cursor = None
            self.__file_count += 1
        elif len(byte_string) > 0:
            self.__dbx.files_upload_session_append_v2(byte_string, self.__cursor)
            self.__cursor.offset = self.__cursor.offset + len(byte_string)
