#!/usr/bin/env python3
import struct
import enum
import sys
from collections import namedtuple

GOR_HEADER_SIZE = 64
SB_MONO_HEADER_SIZE = 128
TAG_HEADER_SIZE = 64
ENTRY_TAG_HEADER_SIZE = 112

class ArchiveType(enum.Enum):
    TAG = 0
    PLUGIN = enum.auto()
    PATCH = enum.auto()
    FOUNDATION = enum.auto()
    CACHE = enum.auto()
    INTERFACE = enum.auto()
    ADDON = enum.auto()
    METASERVER = enum.auto()

# 
# Myth II: monolith header
# 
# 0003          0000
# 2: unknown    2: unknown
# 
# 696E7465726E6174696F6E616C206C6172676520696E7374616C6C0005920848
# 0000000000000000000000000000000000000000000000000000000000000000
# 0000000000000000000000000000000000000000000000000000000000000000
# 96: name
# 
# 0000
# 2: entrypoint tag count (at offset 100)
# 
# 001A
# 2: tag count (at offset 102)
# 
# 8194DA46
# 4: checksum
# 
# 00000000
# 4: flags
# 
# 03A699D0
# 4: size
# 
# A9C6F5AF
# 4: header_checksum
# 
# 42000028
# 4: unused
# 
#  d n g 2
# 646E6732
# 
# 4: myth 2 tag format signature
#  
# list of tags starts here
SBMonoHeaderFmt = """>
    h h
    32s
    64s
    H H
    L
    L
    L
    L
    L
    4s
"""
SBMonoHeader = namedtuple('SBMonoHeader', [
    'type', 'version',
    'name',
    'description',
    'entry_tag_count',
    'tag_list_count',
    'checksum',
    'flags',
    'size',
    'header_checksum',
    'unused',
    'signature'
])

#
# artsound.gor header
#
# 0001 0001
# 7075626C69632E676F7200000000000000000000000000000000000000000000
# A91A 76C1
# 131A 9884 <- tag headers offset
# 02FE      <- tag count
# 0040      <- header size
# 0001
# 00000000 00000000 00000000 0000
GORHeaderFmt = """>
    H H
    32s
    H H
    I
    H
    H
    H
    I I I H
"""
GORHeader = namedtuple('GORHeader', [
    # 0001 0001
    'type', 'version',
    # 7075626C69632E676F7200000000000000000000000000000000000000000000
    'name',
    # A91A 76C1
    'u3', 'u4',
    # 131A9884
    'tag_list_offset',
    # 02FE
    'tag_list_count',
    # 0040
    'header_size',
    # 0001
    'u5',
    # 00000000 00000000 00000000 0000
    'u6',     'u7',    'u8',    'u9'
])

TFLHeaderFmt = """>
    32s 4s 4s
    H H H H
    i l
    H H
    4s
"""
TFLHeader = namedtuple('TFLHeader', [
    # 3033206E6172726174696F6E0000000000000000000000000000000000000000
    'name',
    # 736F756E   30336E61
    'tag_type', 'tag_id',
    # 0000 0001  0005  0002
    'u1', 'u2', 'u3', 'u4',
    # 00000040          000B0D8A
    'tag_data_offset', 'tag_data_size',
    # 0000 0000
    'u5', 'u6',
    # 6D797468
    'tag_version'
])

SBHeaderFmt = """>
    h b b
    32s 4s 4s
    i l
    L h b b
    4s
"""
SBHeader = namedtuple('SBHeader', [
    # FFFF         00       00
    'identifier', 'flags', 'type',
    # 6E61722030320000000000000000000000000000000000000000000000000000
    'name',
    # 736F756E   6E613032
    'tag_type', 'tag_id',
    # 00000040          001A5CB4
    'tag_data_offset', 'tag_data_size',
    # 00000000    0001       FF             FF
    'user_data', 'version', 'destination', 'owner_index',
    # 6D746832
    'tag_version'
])

def load_file(path):
    try:
        with open(path, 'rb') as infile:
            data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {path}")
        sys.exit(1)

    return data

def parse_gor_header(header):
    gor = GORHeader._make(struct.unpack(GORHeaderFmt, header[:GOR_HEADER_SIZE]))
    return gor._replace(
        name=decode_string(gor.name),
    )

def decode_string(s):
    return s.split(b'\0', 1)[0].decode('mac-roman')

def encode_string(b):
    return b.encode('mac-roman')


def parse_sb_mono_header(header):
    mono = SBMonoHeader._make(struct.unpack(SBMonoHeaderFmt, header[:SB_MONO_HEADER_SIZE]))
    return mono._replace(
        name=decode_string(mono.name),
        description=decode_string(mono.description),
        type=ArchiveType(mono.type)
    )

def parse_mono_header(data):
    is_sb = data[124:128] == b'dng2'
    is_tfl = not is_sb and data[:4] == b'\x00\x01\x00\x01'

    if not is_tfl and not is_sb:
        raise ValueError("Incompatible game version")

    if is_tfl:
        header = parse_gor_header(data)
        # print(header.name)

        tag_count = header.tag_list_count
        header_size = header.header_size

        entry_tag_count = 0
        entry_tag_list_start = header_size
        entry_tag_size = 0

        tag_list_start = header.tag_list_offset
    elif is_sb:
        header = parse_sb_mono_header(data)
        # print(header.name)
        # print(header.description)
        tag_count = header.tag_list_count
        header_size = SB_MONO_HEADER_SIZE

        entry_tag_count = header.entry_tag_count
        entry_tag_list_start = header_size
        entry_tag_size = entry_tag_count * ENTRY_TAG_HEADER_SIZE

        tag_list_start = entry_tag_list_start + entry_tag_size

    tag_list_size = tag_count * TAG_HEADER_SIZE

    return (
        header, header_size,
        entry_tag_count, entry_tag_list_start, entry_tag_size,
        tag_count, tag_list_start, tag_list_size
    )

def parse_header(data):
    game_version = data[60:64]
    is_tfl = game_version == b'myth'
    is_sb = game_version == b'mth2'

    if not is_tfl and not is_sb:
        raise ValueError(f"Incompatible game version: {game_version}")

    if is_tfl:
        return parse_tfl_header(data[:TAG_HEADER_SIZE])
    elif is_sb:
        return parse_sb_header(data[:TAG_HEADER_SIZE])

def parse_tfl_header(header):
    return decode_header(TFLHeader._make(struct.unpack(TFLHeaderFmt, header)))

def parse_sb_header(header):
    return decode_header(SBHeader._make(struct.unpack(SBHeaderFmt, header)))

def fix_tag_header_offset(header_tuple):
    return header_tuple._replace(tag_data_offset=TAG_HEADER_SIZE)

def tag_header_fmt(header_tuple):
    if header_tuple.tag_version == 'myth':
        return TFLHeaderFmt
    elif header_tuple.tag_version == 'mth2':
        return SBHeaderFmt

def encode_header(header):
    encoded = header._replace(
        name=encode_string(header.name),
        tag_type=encode_string(header.tag_type),
        tag_id=encode_string(header.tag_id),
        tag_version=encode_string(header.tag_version)
    )
    return struct.pack(tag_header_fmt(header), *encoded)

def decode_header(header):
    return header._replace(
        name=decode_string(header.name),
        tag_type=decode_string(header.tag_type),
        tag_id=decode_string(header.tag_id),
        tag_version=decode_string(header.tag_version)
    )
