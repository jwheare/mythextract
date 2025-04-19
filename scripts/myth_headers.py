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

TagTypes = {
    'amso': "Ambient Sounds",
    'arti': "Artifacts",
    'core': "Collection References",
    '.256': "Collections",
    'conn': "Connectors",
    'ditl': "Dialog String Lists",
    'd256': "Detail Collections",
    'dmap': "Detail Maps",
    'dtex': "Detail Textures",
    'bina': "Dialogs",
    'font': "Fonts",
    'form': "Formations",
    'geom': "Geometries",
    'inte': "Interface",
    'ligh': "Lightning",
    'phys': "Local Physics",
    'lpgr': "Local Projectile Groups",
    'medi': "Media Types",
    'meef': "Mesh Effect",
    'meli': "Mesh Lighting",
    'mesh': "Meshes",
    'anim': "Model Animations",
    'mode': "Models",
    'mons': "Monsters",
    'obje': "Objects",
    'obpc': "Observer Constants",
    'part': "Particle Systems",
    'pref': "Preferences",
    'prel': "Preloaded Data",
    'prgr': "Projectile Groups",
    'proj': "Projectiles",
    'reco': "Recordings",
    'save': "Saved Games",
    'scen': "Scenery",
    'scri': "Scripts",
    'soli': "Sound Lists",
    'soun': "Sounds",
    'stli': "String Lists",
    'temp': "Templates",
    'text': "Text",
    'unit': "Units",
    'wind': "Wind",
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
SBMonoHeaderFmt = """>
    h H
    32s
    64s
    H H
    4s
    L
    L
    4s
    4x
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
    L
    L
    H
    H
    H
    2x
    L
    8x
"""
GORHeader = namedtuple('GORHeader', [
    # 0001 0001
    'type', 'version',
    # 7075626C69632E676F7200000000000000000000000000000000000000000000
    'name',
    # A91A76C1
    'checksum',
    # 131A9884
    'tag_list_offset',
    # 02FE
    'tag_list_count',
    # 0040
    'header_size',
    # 0001
    'flags',
    # 0000 pad ignored
    # 00000000
    'mod_time'
    # 0000000000000000 unused
])

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

TFLHeaderFmt = """>
    32s 4s 4s
    L H H
    i l
    L
    4s
"""
TFLHeader = namedtuple('TFLHeader', [
    # 3033206E6172726174696F6E0000000000000000000000000000000000000000
    'name',
    # 736F756E   30336E61
    'tag_type', 'tag_id',
    # 00000001  0005           0002
    'version', 'tag_version', 'flags',
    # 00000040          000B0D8A
    'tag_data_offset', 'tag_data_size',
    # 00000000
    'user_data',
    # 6D797468
    'signature'
])

SBHeaderFmt = """>
    x b b b
    32s 4s 4s
    i l
    L h b b
    4s
"""
SBHeader = namedtuple('SBHeader', [
    # FF unused
    # FF            00       00
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
    'signature'
])

def tfl2sb(tfl_header, tag_content):
    sb_header = SBHeader(
        identifier=-1,
        flags=0,
        type=ArchiveType.TAG,
        name=tfl_header.name,
        tag_type=tfl_header.tag_type,
        tag_id=tfl_header.tag_id,
        tag_data_offset=tfl_header.tag_data_offset,
        tag_data_size=len(tag_content),
        user_data=tfl_header.user_data,
        version=tfl_header.version,
        destination=-1,
        owner_index=-1,
        signature='mth2'
    )
    return encode_header(sb_header) + tag_content


def local_folder(tag_header):
    return tag_type_name(tag_header.tag_type)

def tag_type_name(tag_type):
    return TagTypes[tag_type.lower()].lower()

def all_on(val):
    return all(f == b'' for f in val.split(b'\xff'))

def all_off(val):
    return all(f == b'' for f in val.split(b'\x00'))

def load_file(path, length=None):
    try:
        with open(path, 'rb') as infile:
            if length:
                data = infile.read(length)
            else:
                data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {path}")
        sys.exit(1)

    return data

def parse_gor_header(header):
    header_data = header[:GOR_HEADER_SIZE]
    if len(header_data) < GOR_HEADER_SIZE:
        raise ValueError("Invalid header")
    gor = GORHeader._make(struct.unpack(GORHeaderFmt, header_data))
    return gor._replace(
        name=decode_string(gor.name),
    )

def decode_string(s):
    return s.split(b'\0', 1)[0].decode('mac-roman')

def encode_string(b):
    if b is None:
        return b''
    else:
        return b.encode('mac-roman')


def parse_sb_mono_header(header):
    header_data = header[:SB_MONO_HEADER_SIZE]
    if len(header_data) < SB_MONO_HEADER_SIZE:
        raise ValueError("Invalid header")

    mono = SBMonoHeader._make(struct.unpack(SBMonoHeaderFmt, header_data))
    return mono._replace(
        name=decode_string(mono.name),
        description=decode_string(mono.description),
        type=ArchiveType(mono.type),
        signature=decode_string(mono.signature),
    )

def encode_sb_mono_header(mono):
    return struct.pack(SBMonoHeaderFmt, *mono._replace(
        name=encode_string(mono.name),
        description=encode_string(mono.description),
        type=mono.type.value,
        signature=encode_string(mono.signature),
    ))

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
    return decode_header(TFLHeader._make(struct.unpack(TFLHeaderFmt, header)))

def parse_sb_header(header):
    return decode_header(SBHeader._make(struct.unpack(SBHeaderFmt, header)))

def parse_text_tag(data):
    header = parse_header(data)

    text = data[TAG_HEADER_SIZE:]

    return (header, text)

def game_version(header_tuple):
    if header_tuple.signature == 'myth':
        return 1
    elif header_tuple.signature == 'mth2':
        return 2

def normalise_tag_header(header_tuple):
    return header_tuple._replace(
        tag_data_offset=TAG_HEADER_SIZE,
        identifier=-1,
        type=0,
        destination=-1,
        owner_index=-1,
    )

def tag_header_fmt(header_tuple):
    version = game_version(header_tuple)
    if version == 1:
        return TFLHeaderFmt
    elif version == 2:
        return SBHeaderFmt

def encode_header(header):
    encoded = normalise_tag_header(header)._replace(
        name=encode_string(header.name),
        tag_type=encode_string(header.tag_type),
        tag_id=encode_string(header.tag_id),
        signature=encode_string(header.signature)
    )
    return struct.pack(tag_header_fmt(header), *encoded)

def decode_header(header):
    return header._replace(
        name=decode_string(header.name),
        tag_type=decode_string(header.tag_type),
        tag_id=decode_string(header.tag_id),
        signature=decode_string(header.signature)
    )
