#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2021 Snowflake Computing Inc. All right reserved.

#

import io
import subprocess
import zlib
from logging import getLogger
from typing import IO

CHUNK_SIZE = 16384
MAGIC_NUMBER = 16  # magic number from .vendored.requests/packages/urllib3/response.py

logger = getLogger(__name__)


def decompress_raw_data(raw_data_fd: IO, add_bracket: bool = True) -> bytes:
    """Decompresses raw data from file like object with zlib.

    Args:
        raw_data_fd: File descriptor object.
        add_bracket: Whether, or not to add brackets around the output. (Default value = True)

    Returns:
        A byte array of the decompressed file.
    """
    obj = zlib.decompressobj(MAGIC_NUMBER + zlib.MAX_WBITS)
    writer = io.BytesIO()
    if add_bracket:
        writer.write(b'[')
    d = raw_data_fd.read(CHUNK_SIZE)
    while d:
        writer.write(obj.decompress(d))
        while obj.unused_data != b'':
            unused_data = obj.unused_data
            obj = zlib.decompressobj(MAGIC_NUMBER + zlib.MAX_WBITS)
            writer.write(obj.decompress(unused_data))
        d = raw_data_fd.read(CHUNK_SIZE)
        writer.write(obj.flush())
    if add_bracket:
        writer.write(b']')
    return writer.getvalue()


def decompress_raw_data_by_zcat(raw_data_fd: IO, add_bracket: bool = True):
    """Experimental: Decompresses raw data from file like object with zcat. Otherwise same as decompress_raw_data.

    Args:
        raw_data_fd: File descriptor object.
        add_bracket: Whether, or not to add brackets around the output. (Default value = True)

    Returns:
        A byte array of the decompressed file.
    """
    writer = io.BytesIO()
    if add_bracket:
        writer.write(b'[')
    p = subprocess.Popen(["zcat"],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE)
    writer.write(p.communicate(input=raw_data_fd.read())[0])
    if add_bracket:
        writer.write(b']')
    return writer.getvalue()


class IterStreamer(object):
    """File-like streaming iterator."""

    def __init__(self, generator):
        self.generator = generator
        self.iterator = iter(generator)
        self.leftover = ''

    def __len__(self):
        return self.generator.__len__()

    def __iter__(self):
        return self.iterator

    def next(self):
        return next(self.iterator)

    def read(self, size):
        data = self.leftover
        count = len(self.leftover)
        try:
            while count < size:
                chunk = next(self)
                data += chunk
                count += len(chunk)
        except StopIteration:
            self.leftover = ''
            return data

        if count > size:
            self.leftover = data[size:]

        return data[:size]


def decompress_raw_data_to_unicode_stream(raw_data_fd: IO):
    """Decompresses a raw data in file like object and yields a Unicode string.

    Args:
        raw_data_fd: File descriptor object.

    Yields:
        A string of the decompressed file in chunks.
    """
    obj = zlib.decompressobj(MAGIC_NUMBER + zlib.MAX_WBITS)
    yield '['
    d = raw_data_fd.read(CHUNK_SIZE)
    while d:
        yield obj.decompress(d).decode('utf-8')
        while obj.unused_data != b'':
            unused_data = obj.unused_data
            obj = zlib.decompressobj(MAGIC_NUMBER + zlib.MAX_WBITS)
            yield obj.decompress(unused_data).decode('utf-8')
        d = raw_data_fd.read(CHUNK_SIZE)
    yield obj.flush().decode('utf-8') + ']'
