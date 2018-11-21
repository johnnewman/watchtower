import dropbox
import logging
import os
from streamer.writer import byte_writer

logger = None


class DropboxWriter(byte_writer.ByteWriter):
    """
    A class that creates an upload session on Dropbox and writes all bytes to
    that session.  When ``file_chunk_size`` is reached, the session is closed
    and a new session opened.
    """

    def __init__(self, full_path, dropbox_token, file_chunk_size=None):
        """
        :param full_path: The full path of the file.
        :param dropbox_token: Token that will be supplied to Dropbox.
        :param file_chunk_size: A maximum size, in bytes, before a new file
        will be created.
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

        if self.__file_chunk_size is not None:
            current_offset = self.__cursor.offset if self.__cursor is not None else 0
            total_available_space = self.__file_chunk_size - current_offset
            if len(byte_string) > total_available_space:
                # Break the byte_string into max sized smaller chunks.
                logger.debug('Attempting to upload beyond max size. Splitting.')
                substring = byte_string[:total_available_space]
                while len(substring) == total_available_space:
                    self.append_bytes(substring, True)  # Save each individual substring.
                    byte_string = byte_string[total_available_space:]  # Remove the substring.
                    # Update the space now that at least the first chunk is uploaded.
                    total_available_space = self.__file_chunk_size
                    substring = byte_string[:total_available_space]  # Fetch the next substring.
                byte_string = substring  # This will now be the last chunk, under the size limit.

        if self.__cursor is None:
            session_start_result = self.__dbx.files_upload_session_start(byte_string)
            self.__cursor = dropbox.files.UploadSessionCursor(session_start_result.session_id, offset=len(byte_string))
            path, extension = os.path.splitext(self.full_path)
            full_path = path + str(self.__file_count) + extension
            self.__commit = dropbox.files.CommitInfo(full_path, mode=dropbox.files.WriteMode.add)
            byte_string = ''

        if close:
            self.__dbx.files_upload_session_finish(byte_string, self.__cursor, self.__commit)
            logger.debug('Closed file \"%s\"' % self.__commit.path)
            self.__cursor = None
            self.__file_count += 1
        elif len(byte_string) > 0:
            self.__dbx.files_upload_session_append_v2(byte_string, self.__cursor)
            self.__cursor.offset = self.__cursor.offset + len(byte_string)
