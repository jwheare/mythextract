#!/usr/bin/env python3
import signal
import sys
import struct
import pathlib
from collections import namedtuple

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

GOR_HEADER_SIZE = 64
SB_MONO_HEADER_SIZE = 128
TAG_HEADER_SIZE = 64
PRE_TAG_HEADER_SIZE = 112

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
# 2: pre tag count (at offset 100)
# 
# 001A
# 2: tag count (at offset 102)
# 
# 8194 DA46 0000 0000 03A6 99D0 A9C6 F5AF 4200 0028
# 20: unknown
# 
#  d n g 2
# 646E6732
# 4: myth 2 tag format signature
#  
# list of tags starts here
SBMonoHeaderFmt = """>
    h h
    32s
    64s
    H H
    H H I H H H H H H
    4s
"""
SBMonoHeader = namedtuple('SBMonoHeader', [
    'u1', 'u2',
    'name',
    'description',
    'pre_tag_count',
    'tag_list_count',
    'u3', 'u4', 'u5', 'u6', 'u7', 'u8', 'u9', 'u10', 'u11',
    'identifier'
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
    'u1', 'u2',
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

def main(mono_path, tag_type, tag_id, output_file):
    """
    Parse a Myth TFL or Myth II monolith file and export provided tag.
    If no tag provided, list all tags
    """
    try:
        with open(mono_path, 'rb') as infile:
            data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {mono_path}")
        sys.exit(1)

    try:
        data_size = len(data)

        is_tfl = data[:4] == b'\x00\x01\x00\x01'
        is_sb = data[124:128] == b'dng2'

        if not is_tfl and not is_sb:
            raise ValueError("Incompatible game version")

        if is_tfl:
            header = parse_gor_header(data[:GOR_HEADER_SIZE])
            print(header)
            print(header.name)

            tag_count = header.tag_list_count
            header_size = header.header_size

            pre_tag_count = 0
            pre_tag_list_start = header_size
            pre_tag_size = 0

            tag_list_start = header.tag_list_offset
        elif is_sb:
            header = parse_sb_mono_header(data[:SB_MONO_HEADER_SIZE])
            print(header)
            print(header.name)
            print(header.description)
            tag_count = header.tag_list_count
            header_size = SB_MONO_HEADER_SIZE

            pre_tag_count = header.pre_tag_count
            pre_tag_list_start = header_size
            pre_tag_size = pre_tag_count * PRE_TAG_HEADER_SIZE

            tag_list_start = pre_tag_list_start + pre_tag_size

        tag_list_size = tag_count * TAG_HEADER_SIZE
        print('total file length', data_size)
        print('      header size', header_size)
        if pre_tag_count:
            print('    pre tag start', pre_tag_list_start)
            print('    pre tag count', pre_tag_count)
            print('     pre tag size', pre_tag_size)
        print('   tag list start', tag_list_start)
        print('        tag count', tag_count)
        print('    tag list size', tag_list_size)

        if pre_tag_count:
            print(
                """
Pre tags
------+----------------------------------+------------------------------------------------------------------+
 id   | name                             | long
------+----------------------------------+------------------------------------------------------------------+"""
            )
        for i in range(pre_tag_count):
            start = pre_tag_list_start + (i * PRE_TAG_HEADER_SIZE)
            end = start + PRE_TAG_HEADER_SIZE
            pre_tag_header_data = data[start:end]
            (p_tag_id, p_tag_name, p_tag_long_name) = struct.unpack('>16s 32s 64s', pre_tag_header_data)
            p_tag_id = p_tag_id.split(b'\0', 1)[0].decode('mac-roman')
            p_tag_name = p_tag_name.split(b'\0', 1)[0].decode('mac-roman')
            p_tag_long_name = p_tag_long_name.split(b'\0', 1)[0].decode('mac-roman')
            print(f' {p_tag_id: <4} | {p_tag_name: <32} | {p_tag_long_name: <64}')

        print(
            """
Tags
-----+------+------+------+-------
 idx | game | type | id   | name 
-----+------+------+------+-------"""
        )
        for i in range(tag_count):
            start = tag_list_start + (i * TAG_HEADER_SIZE)
            end = start + TAG_HEADER_SIZE
            tag_header_data = data[start:end]
            if is_tfl:
                tag_header = parse_tfl_header(tag_header_data)
            elif is_sb:
                tag_header = parse_sb_header(tag_header_data)
            if (
                (not tag_id and not tag_type)
                or (tag_type == tag_header.tag_type and tag_id == tag_header.tag_id)
            ):
                print(
                    f' {i:03} | '
                    f'{tag_header.tag_version} | '
                    f'{tag_header.tag_type} | '
                    f'{tag_header.tag_id} | '
                    f'{tag_header.name}'
                )
                if tag_id and tag_type:
                    export_tag(tag_header_data, tag_header, data, output_file)

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def export_tag(tag_header_data, tag_header, data, output_file):
    tag_start = tag_header.tag_data_offset
    tag_end = tag_start + tag_header.tag_data_size
    tag_data = data[tag_start:tag_end]

    if not output_file:
        output_file = f'./tags/{tag_header.tag_version}-{tag_id}'

    tag_path = pathlib.Path(output_file)

    if prompt(tag_path):
        pathlib.Path(tag_path.parent).mkdir(parents=True, exist_ok=True)
        with open(tag_path, 'wb') as tag_file:
            tag_file.write(tag_header_data)
            tag_file.write(tag_data)
            print(f"Tag extracted. Output saved to {tag_path}")

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_gor_header(header):
    gor = GORHeader._make(struct.unpack(GORHeaderFmt, header))
    return gor._replace(
        name=gor.name.split(b'\0', 1)[0].decode('mac-roman'),
    )
def parse_sb_mono_header(header):
    mono = SBMonoHeader._make(struct.unpack(SBMonoHeaderFmt, header))
    return mono._replace(
        name=mono.name.split(b'\0', 1)[0].decode('mac-roman'),
        description=mono.description.split(b'\0', 1)[0].decode('mac-roman'),
    )

def parse_tfl_header(header):
    return decode_header(TFLHeader._make(struct.unpack(TFLHeaderFmt, header)))

def parse_sb_header(header):
    return decode_header(SBHeader._make(struct.unpack(SBHeaderFmt, header)))

def decode_header(header):
    return header._replace(
        name=header.name.split(b'\0', 1)[0].decode('mac-roman'),
        tag_type=header.tag_type.decode('mac-roman'),
        tag_id=header.tag_id.decode('mac-roman'),
        tag_version=header.tag_version.decode('mac-roman')
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mono2tag.py <input_file> [<tag_type> <tag_id> [<output_file>]]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    tag_type = None
    tag_id = None
    output_file = None

    if len(sys.argv) >= 4:
        tag_type = sys.argv[2]
        tag_id = sys.argv[3]
        if len(sys.argv) == 5:
            output_file = sys.argv[4]
    
    try:
        main(input_file, tag_type, tag_id, output_file)
    except KeyboardInterrupt:
        sys.exit(130)
