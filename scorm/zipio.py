import shutil
from typing import BinaryIO, Union

AssetData = Union[bytes, bytearray, BinaryIO]


def write_asset(zf, path: str, data: AssetData) -> None:
    """
    Write one entry into an open zipfile.ZipFile.

    File-like sources (e.g. a Streamlit UploadedFile backing a 300-600MB
    video) are streamed through in chunks via shutil.copyfileobj instead of
    being materialized as one giant bytes object first -- avoids doubling
    peak memory on top of whatever the upload itself already holds.
    """
    if isinstance(data, (bytes, bytearray)):
        zf.writestr(path, data)
        return
    if hasattr(data, "seek"):
        data.seek(0)
    with zf.open(path, "w") as dest:
        shutil.copyfileobj(data, dest, length=1024 * 1024)
