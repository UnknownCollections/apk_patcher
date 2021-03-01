import functools
import os
from subprocess import Popen
from typing import Optional, Type
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import dotenv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hashes import HashAlgorithm, SHA1


def print_subprocess_output(proc: Popen, prefix: str = '\t'):
    for line in iter(proc.stdout.readline, b''):
        line = line.decode().strip()
        print(f'{prefix}{line}')
    proc.wait()


def change_url_query_param(url: str, key: str, value: str, single_value: bool = True) -> str:
    parsed_url = urlparse(url)
    queries = parse_qs(parsed_url.query)
    if key not in queries:
        queries.setdefault(key, [value])
    elif key in queries and single_value:
        queries[key].clear()
        queries[key].append(value)
    return urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        urlencode(dict(queries), doseq=True),
        parsed_url.fragment
    ))


def hash_file(file_path: str, hasher: Type[HashAlgorithm], buffer_size: int = 1024 * 1024) -> bytes:
    with open(file_path, 'rb') as f:
        digest = hashes.Hash(hasher())
        chunker = functools.partial(f.read, buffer_size - (buffer_size % digest.algorithm.block_size))
        for chunk in iter(chunker, b''):
            digest.update(chunk)
        return digest.finalize()


def git_hash_file(file_path: str, buffer_size: int = 1024 * 1024) -> bytes:
    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f:
        digest = hashes.Hash(hashes.SHA1())
        # See: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects#_object_storage
        digest.update(b'blob %d\0' % file_size)
        chunker = functools.partial(f.read, buffer_size - (buffer_size % SHA1.block_size))
        for chunk in iter(chunker, b''):
            digest.update(chunk)
        return digest.finalize()


def dotenv_get_set(key: str, default: Optional[str]) -> Optional[str]:
    # If env has key, use that value first, it overrides .env
    value = os.getenv(key, None)
    if value is not None:
        return value

    # find dot env file, make one in cwd if one doesn't exist
    dotenv_file = dotenv.find_dotenv()
    if dotenv_file == '':
        open('.env', 'w').close()
        dotenv_file = dotenv.find_dotenv()

    # Get the value from the .env, will be None if it doesn't exist
    value = dotenv.get_key(dotenv_file, key)

    # Treat empty values in .env as None
    if value == '':
        value = None

    # If value is not in .env set the default, will not use sys env
    if value is None:
        print(f'\tSetting default value for {key} to {default}')
        dotenv.set_key(dotenv_file, key, default or '', quote_mode='never')
        return default

    return value
