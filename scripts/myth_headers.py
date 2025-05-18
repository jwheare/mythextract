#!/usr/bin/env python3
import enum
from collections import namedtuple

import utils

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
ArchivePriority = {
    ArchiveType.FOUNDATION: -3,
    ArchiveType.CACHE: -2,
    ArchiveType.PATCH: -2,
    ArchiveType.ADDON: -1,
    ArchiveType.PLUGIN: 0,
    ArchiveType.INTERFACE: 0,
    ArchiveType.TAG: 0,
    ArchiveType.METASERVER: 0,
}

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
SBMonoHeaderFmt = ('SBMonoHeader', [
    ('h', 'type', ArchiveType),
    ('H', 'version'),
    ('32s', 'name', utils.StringCodec),
    ('64s', 'description', utils.StringCodec),
    ('H', 'entry_tag_count'),
    ('H', 'tag_list_count'),
    ('4s', 'checksum'),
    ('L', 'flags'),
    ('L', 'size'),
    ('4s', 'header_checksum'),
    ('4x', None),
    ('4s', 'signature', utils.StringCodec),
])
SBMonoHeader = utils.codec(SBMonoHeaderFmt)

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
GORHeaderFmt = ('GORHeader', [
    ('H', 'type'),
    ('H', 'version'),
    ('32s', 'name', utils.StringCodec),
    ('L', 'checksum'),
    ('L', 'tag_list_offset'),
    ('H', 'tag_list_count'),
    ('H', 'header_size'),
    ('H', 'flags'),
    ('2x', None),
    ('L', 'mod_time'),
    ('8x', None),
])
GORHeader = utils.codec(GORHeaderFmt)

UnifiedHeader = namedtuple('UnifiedHeader', [
    'filename',
    'game_version',
    'type',
    'version',
    'name',
    'description',
    'header',
    'header_size',
    'entry_tag_count',
    'entry_tag_list_start',
    'tag_count',
    'tag_list_start',
    'tag_list_size',
    'flags',
    'checksum',
])

TFLHeaderFmt = ('TFLHeader', [
    ('32s', 'name', utils.StringCodec),
    ('4s', 'tag_type', utils.StringCodec),
    ('4s', 'tag_id', utils.StringCodec),
    ('L', 'version'),
    ('H', 'tag_version'),
    ('H', 'flags'),
    ('i', 'tag_data_offset'),
    ('l', 'tag_data_size'),
    ('L', 'user_data'),
    ('4s', 'signature', utils.StringCodec),
])
TFLHeader = utils.codec(TFLHeaderFmt)

SBHeaderFmt = ('SBHeader', [
    ('h', 'identifier'),
    ('b', 'flags'),
    ('b', 'type'),
    ('32s', 'name', utils.StringCodec),
    ('4s', 'tag_type', utils.StringCodec),
    ('4s', 'tag_id', utils.StringCodec),
    ('i', 'tag_data_offset'),
    ('l', 'tag_data_size'),
    ('L', 'user_data'),
    ('h', 'version'),
    ('b', 'destination'),
    ('b', 'owner_index'),
    ('4s', 'signature', utils.StringCodec),
])
SBHeader = utils.codec(SBHeaderFmt)

def tfl2sb(tfl_header, tag_content):
    SBHeaderT = utils.make_nt(SBHeaderFmt)
    sb_header_values = SBHeaderT(
        identifier=-1,
        flags=0,
        type=ArchiveType.TAG.value,
        name=tfl_header.name.value,
        tag_type=tfl_header.tag_type.value,
        tag_id=tfl_header.tag_id.value,
        tag_data_offset=tfl_header.tag_data_offset,
        tag_data_size=len(tag_content),
        user_data=tfl_header.user_data,
        version=tfl_header.version,
        destination=-1,
        owner_index=-1,
        signature=b'mth2'
    )
    sb_header = SBHeader(values=sb_header_values)
    return normalise_tag_header(sb_header).value + tag_content

def parse_gor_header(header):
    header_data = header[:GOR_HEADER_SIZE]
    if len(header_data) < GOR_HEADER_SIZE:
        raise ValueError("Invalid header")
    return GORHeader(header_data)

def parse_sb_mono_header(header):
    header_data = header[:SB_MONO_HEADER_SIZE]
    if len(header_data) < SB_MONO_HEADER_SIZE:
        raise ValueError("Invalid header")

    return SBMonoHeader(header_data)

def encode_sb_mono_header(mono):
    return mono.value

def mono_header_size(header):
    if type(header).__name__ == 'GORHeader':
        return GOR_HEADER_SIZE
    elif type(header).__name__ == 'SBMonoHeader':
        return SB_MONO_HEADER_SIZE

def parse_mono_header(filename, data):
    is_sb = data[124:128] == b'dng2'
    is_tfl = not is_sb and data[:4] == b'\x00\x01\x00\x01'

    if not is_tfl and not is_sb:
        raise ValueError("Incompatible game version")

    if is_tfl:
        version = 1
        header = parse_gor_header(data)
        description = None

        tag_count = header.tag_list_count
        header_size = header.header_size
        header_type = ArchiveType.FOUNDATION

        entry_tag_count = 0
        entry_tag_list_start = header_size

        tag_list_start = header.tag_list_offset
    elif is_sb:
        version = 2
        header = parse_sb_mono_header(data)
        description = header.description
        tag_count = header.tag_list_count
        header_size = SB_MONO_HEADER_SIZE
        header_type = header.type

        entry_tag_count = header.entry_tag_count
        entry_tag_list_start = header_size

        tag_list_start = entry_tag_list_start + (entry_tag_count * ENTRY_TAG_HEADER_SIZE)

    # print(header.name)
    # print(description)

    tag_list_size = tag_count * TAG_HEADER_SIZE

    return UnifiedHeader(
        filename=filename,
        game_version=version,
        type=header_type,
        version=header.version,
        name=header.name,
        description=description,
        header=header,
        header_size=header_size,
        entry_tag_count=entry_tag_count,
        entry_tag_list_start=entry_tag_list_start,
        tag_count=tag_count,
        tag_list_start=tag_list_start,
        tag_list_size=tag_list_size,
        flags=header.flags,
        checksum=header.checksum,
    )
    return (
        version, header, header_size,
        entry_tag_count, entry_tag_list_start,
        tag_count, tag_list_start, tag_list_size
    )

def parse_header(data):
    version = data[60:64]
    is_tfl = version == b'myth'
    is_sb = version == b'mth2'

    if not is_tfl and not is_sb:
        raise ValueError(f"Incompatible game version: {version}")

    if is_tfl:
        return parse_tfl_header(data[:TAG_HEADER_SIZE])
    elif is_sb:
        return parse_sb_header(data[:TAG_HEADER_SIZE])

def parse_tfl_header(header):
    return TFLHeader(header)


def parse_sb_header(header):
    return SBHeader(header)

def parse_text_tag(data):
    header = parse_header(data)

    text = data[TAG_HEADER_SIZE:]

    return (header, text)

def game_version(header):
    if header.signature == 'myth':
        return 1
    elif header.signature == 'mth2':
        return 2

def normalise_tag_header(header, **kwargs):
    return header._replace(
        tag_data_offset=TAG_HEADER_SIZE,
        identifier=-1,
        type=0,
        destination=-1,
        owner_index=-1,
        **kwargs
    )

def encode_header(header):
    return normalise_tag_header(header).value
