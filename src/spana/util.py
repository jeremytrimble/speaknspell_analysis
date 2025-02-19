import os
import tempfile


class TempFileMgr:
    def __init__(self):
        self._to_remove = []

    def get_tempfile(self, byts:bytes):
        with tempfile.NamedTemporaryFile(delete=False, delete_on_close=False) as tf:
            tf.write(byts)
            filename = tf.name
            print(f"generated tempfile {filename=}")
            self._to_remove.append(filename)
        return filename

    def close(self):
        for to_remove in self._to_remove:
            try:
                os.unlink(to_remove)
            except Exception as e:
                print(f"failed to remove file: {to_remove} -- {e}")