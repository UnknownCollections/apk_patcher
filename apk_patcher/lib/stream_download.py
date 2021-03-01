import binascii
import os
from typing import Any, Callable, Generator, Iterator, NewType, Optional

import requests

from apk_patcher.lib.progress import ProgressCallback, ProgressCancelled, ProgressData, ProgressStage, ProgressType

DownloadMiddleware = NewType('DownloadMiddleware', Callable[[Iterator], Generator[bytes, None, None]])


def stream_download_progress(url: str, output_file_path: str, buffer_size: int, output_file_size: Optional[int],
                             middleware: Optional[DownloadMiddleware], on_progress: Optional[ProgressCallback],
                             progress_user_var: Optional[Any], **kwargs):
    dl_resp = requests.get(url, stream=True, allow_redirects=True, **kwargs)
    if dl_resp.status_code >= 400:
        raise Exception(dl_resp)

    dl_size = output_file_size
    if dl_size is None and 'Content-Length' in dl_resp.headers:
        dl_size = int(dl_resp.headers['Content-Length'])

    if on_progress is not None:
        desc = f'downloading {os.path.basename(output_file_path)}'
        progress = ProgressData(ProgressStage.START, ProgressType.FILE, desc, 0, dl_size, 0)
        if not on_progress(progress_user_var, progress):
            raise ProgressCancelled()

    os.makedirs(os.path.dirname(output_file_path), 0o755, exist_ok=True)

    with open(output_file_path, 'wb') as f:
        chunker = dl_resp.iter_content(chunk_size=buffer_size)
        if middleware is not None:
            chunker = middleware(chunker)
        for chunk in chunker:
            if not chunk:
                continue
            written_size = f.write(chunk)
            if on_progress is not None:
                # noinspection PyUnboundLocalVariable
                progress.delta = written_size
                progress.current += written_size
                if progress.current > progress.total:
                    progress.total = progress.current
                progress.stage = ProgressStage.PROGRESS
                if not on_progress(progress_user_var, progress):
                    raise ProgressCancelled()

    if on_progress is not None:
        progress.stage = ProgressStage.STOP
        on_progress(progress_user_var, progress)


def stream_decode_response_base64(stream: Iterator) -> Generator[bytes, None, None]:
    partial_chunk_buffer = bytearray()
    for chunk in stream:
        if len(partial_chunk_buffer) > 0:
            chunk = partial_chunk_buffer + chunk
            partial_chunk_buffer.clear()
        chunk_len = len(chunk)
        if chunk_len % 4 == 0:
            yield binascii.a2b_base64(chunk)
        elif chunk_len > 4:
            largest_decodable_len = chunk_len - (chunk_len % 4)
            decoded_data = binascii.a2b_base64(chunk[:largest_decodable_len])
            partial_chunk_buffer.extend(chunk[largest_decodable_len:])
            yield decoded_data
        else:
            partial_chunk_buffer.extend(chunk)
