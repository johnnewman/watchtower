import dropbox
from streamer.writer import ByteWriter
import logging

logger = None


class DropboxWriter(ByteWriter.ByteWriter):
    """
    A class that creates an upload session on Dropbox and writes all bytes to
    that session.
    """

    def __init__(self, full_path, dropbox_token):
        super(DropboxWriter, self).__init__(full_path)
        self.__dropbox_token = dropbox_token
        self.__dbx = dropbox.Dropbox(dropbox_token)
        self.__cursor = None
        self.__commit = None

    def append_bytes(self, byte_string, close=False):
        global logger
        if logger is None:
            logger = logging.getLogger(__name__)

        if self.__cursor is None:
            session_start_result = self.__dbx.files_upload_session_start(byte_string)
            self.__cursor = dropbox.files.UploadSessionCursor(session_start_result.session_id, offset=len(byte_string))
            self.__commit = dropbox.files.CommitInfo(self.full_path, mode=dropbox.files.WriteMode.add)
            return

        if close:
            self.__dbx.files_upload_session_finish(byte_string, self.__cursor, self.__commit)
            logger.debug('Closed Dropbox file \"%s\"' % self.full_path)
        else:
            self.__dbx.files_upload_session_append_v2(byte_string, self.__cursor)
            self.__cursor.offset = self.__cursor.offset + len(byte_string)
