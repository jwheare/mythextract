#!/usr/bin/env python3
from collections import namedtuple
import os
import struct

import myth_headers
import utils

AIFC_VERSION_1 = 2726318400
SAMPLE_RATE_80_FLOAT_22050 = b'\x40\x0D\xAC\x44\x00\x00\x00\x00\x00\x00'

IMA4_BYTES_PER_FRAME = 34
IMA_COMPRESSION_RATIO = 4

DEBUG_SOUN = (os.environ.get('DEBUG_SOUN') == '1')

SOUN_HEADER_SIZE = 64
SoundHeaderFmt = """>
    L h h H
    H H H H

    h
    L L

    4s H H
    L L L

    I I I I
"""
SoundHeader = namedtuple('SoundHeader', [
    'flags', 'loudness', 'play_fraction', 'external_frequency_modifier',
    'pitch_lower_bound', 'pitch_delta', 'volume_lower_bound', 'volume_delta',

    'first_subtitle_within_string_list_index',
    'sound_offset', 'sound_size',

    'subtitle_string_list_tag', 'subtitle_string_list_index', 'unused',
    'permutation_count', 'permutations_offset', 'permutations_size',

    'd6', 'd7', 'd8', 'd9'
])

PERM_DESC_SIZE = 32
PermDescFmt = """>
    H H H 26s
"""
PERM_META_SIZE = 32
PermMetaFmt = """>
    H H
    H
    H
    H
    I
    H
    I
    H H H H H H
"""
PermMeta = namedtuple('PermMeta', [
    'm1', 'm2',
    'sample_size',
    'm3',
    'num_channels',
    'sample_rate',
    'm4',
    'num_sample_frames',
    'm5', 'm6', 'm7', 'm8', 'm9', 'm10'
])

AMSO_SIZE = 64
MAX_AMSO_SOUN = 6
AmsoFmt = """>
    L
    h h
    h h
    24s
    h
    10x
    12s
    h h
"""
Amso = namedtuple('Amso', [
    'flags',
    'inner_radius', 'outer_radius',
    'period_lower_bound', 'period_delta',
    'sound_tags',
    'random_sound_radius',
    'sound_indexes',
    'phase', 'period'
])

def parse_soun_header(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + SOUN_HEADER_SIZE
    return SoundHeader._make(struct.unpack(SoundHeaderFmt, data[start:end]))

def parse_permutation_meta(values):
    return PermMeta._make(values)

def parse_soun_tag(data):
    header = myth_headers.parse_header(data)

    soun_header_size = SOUN_HEADER_SIZE
    soun_header_end = myth_headers.TAG_HEADER_SIZE + soun_header_size

    soun_header = parse_soun_header(data)

    permutation_end = soun_header_end + soun_header.permutations_size
    total_meta_length = (soun_header.permutation_count * PERM_META_SIZE)

    header_end = permutation_end + total_meta_length
    sound_data = data[header_end:]

    # Accumulators
    p_descs = []
    permutations = []

    sound_data_offset = 0
    total_sample_frames = 0
    for (p1, p2, p3, p_desc) in utils.iter_unpack(
        soun_header_end, soun_header.permutation_count,
        PermDescFmt, data
    ):
        p_desc = myth_headers.decode_string(p_desc)
        p_descs.append(p_desc)

    for i, values in enumerate(utils.iter_unpack(
        permutation_end, soun_header.permutation_count,
        PermMetaFmt, data
    )):
        p_meta = parse_permutation_meta(values)
        permutation_sound_length = p_meta.num_sample_frames * IMA4_BYTES_PER_FRAME
        permutation_sound_end = sound_data_offset + permutation_sound_length
        perm_sound_data = sound_data[sound_data_offset:permutation_sound_end]

        duration = (
            (IMA_COMPRESSION_RATIO * p_meta.sample_size * p_meta.num_sample_frames) /
            (p_meta.num_channels * p_meta.sample_rate)
        )

        permutation = {
            'desc': p_descs[i],
            'num_channels': p_meta.num_channels,
            'sample_size': p_meta.sample_size,
            'sample_rate': p_meta.sample_rate,
            'num_sample_frames': p_meta.num_sample_frames,
            'size': permutation_sound_length,
            'duration': duration,
            'sound_data': perm_sound_data
        }
        permutations.append(permutation)

        sound_data_offset = permutation_sound_end
        total_sample_frames = total_sample_frames + p_meta.num_sample_frames

    debug_soun(header, soun_header, permutations, sound_data)

    return (header.signature, header.tag_id, permutations)

def debug_soun(header, soun_header, permutations, sound_data):
    if not DEBUG_SOUN:
        return
    perm_desc_size = soun_header.permutation_count * PERM_DESC_SIZE
    perm_meta_size = soun_header.permutation_count * PERM_DESC_SIZE
    print(f""" Tag: [{header.name}]
Type: [{header.tag_type}]
  ID: [{header.tag_id}]
TDOF: {header.tag_data_offset}
TDSZ: {header.tag_data_size}
SDSZ: {len(sound_data)}
Vers: [{header.signature}]
----
flag: {soun_header.flags}
loud: {soun_header.loudness}
  pf: {soun_header.play_fraction}
 efm: {soun_header.external_frequency_modifier}
 plb: {soun_header.pitch_lower_bound}
  pd: {soun_header.pitch_delta}
 vlb: {soun_header.volume_lower_bound}
  vd: {soun_header.volume_delta}
-----
fsli: {soun_header.first_subtitle_within_string_list_index}
SOFF: {soun_header.sound_offset}
SSIZ: {soun_header.sound_size}
 slt: {soun_header.subtitle_string_list_tag}
 sli: {soun_header.subtitle_string_list_index}
unus: {soun_header.unused}
PCNT: {soun_header.permutation_count}
POFF: {soun_header.permutations_offset}
PDSZ: {perm_desc_size}
PMSZ: {perm_meta_size}
PSIZ: {soun_header.permutations_size}"""
    )
    meta_remainder = (
        soun_header.permutations_size -
        perm_desc_size
    )
    remainder = (
        header.tag_data_size -
        SOUN_HEADER_SIZE -
        perm_desc_size -
        perm_meta_size -
        len(sound_data)
    )
    sound_remainder = len(sound_data)
    print('Permutations:')
    for p in permutations:
        sound_remainder -= p['size']
        perm_s = round(p['duration'], 3)
        perm_m = round(perm_s // 60)
        perm_rem_s = round(perm_s % 60, 3)

        print(f"""[{p['desc']}]
  channels: {p['num_channels']}
 samp_size: {p['sample_size']}
 samp_rate: {p['sample_rate']}
samp_frame: {p['num_sample_frames']}
[soun_len]: {p['size']}
[soun_dur]: {perm_s}s / {perm_m}m{perm_rem_s}s
  -----"""
        )
    print("----- ")
    print(f" Total Remainder: {remainder}")
    print(f"  Meta Remainder: {meta_remainder}")
    print(f"Sounds Remainder: {sound_remainder}")
    print("----- ")

def parse_amso(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + AMSO_SIZE
    amso = Amso._make(struct.unpack(AmsoFmt, data[start:end]))
    sound_tags = struct.unpack(f'>{MAX_AMSO_SOUN * "4s"}', amso.sound_tags)
    sound_indexes = struct.unpack(f'>{MAX_AMSO_SOUN}h', amso.sound_indexes)
    return amso._replace(
        sound_tags=sound_tags,
        sound_indexes=sound_indexes,
    )

def generate_aifc(perm):
    offset = 0
    block_size = 0
    comm_data = struct.pack(
        ">h L h 10s 4s 8p", 
        perm['num_channels'], perm['num_sample_frames'], perm['sample_size'], SAMPLE_RATE_80_FLOAT_22050,
        b'ima4', b'IMA 4:1'
    )
    comm_length = len(comm_data)
    sound_length = len(perm['sound_data'])
    form_data = struct.pack(f""">
        4s
        4s I I
        4s I {comm_length}s
        4s l L L
        {sound_length}s
    """,
        b'AIFC',
        b'FVER', 4, AIFC_VERSION_1,
        b'COMM', comm_length, comm_data,
        b'SSND', sound_length+8, offset, block_size,
        perm['sound_data']
    )
    form_length = len(form_data)
    return struct.pack(
        f">4s I {form_length}s",
        b'FORM', form_length, form_data
    )
