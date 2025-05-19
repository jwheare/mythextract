#!/usr/bin/env python3
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
SoundHeaderFmt = ('SoundHeader', [
    ('L', 'flags'),
    ('h', 'loudness'),
    ('h', 'play_fraction'),
    ('H', 'external_frequency_modifier'),
    ('H', 'pitch_lower_bound'),
    ('H', 'pitch_delta'),
    ('H', 'volume_lower_bound'),
    ('H', 'volume_delta'),
    ('h', 'first_subtitle_within_string_list_index'),
    ('L', 'sound_offset'),
    ('L', 'sound_size'),
    ('4s', 'subtitle_string_list_tag'),
    ('H', 'subtitle_string_list_index'),
    ('H', 'unused'),
    ('L', 'permutation_count'),
    ('L', 'permutations_offset'),
    ('L', 'permutations_size'),
    ('I', 'd6'),
    ('I', 'd7'),
    ('I', 'd8'),
    ('I', 'd9'),
])

PERM_DESC_SIZE = 32
PermDescFmt = """>
    H H H 26s
"""
PERM_META_SIZE = 32
PermMetaFmt = ('PermMeta', [
    ('H', 'm1'),
    ('H', 'm2'),
    ('H', 'sample_size'),
    ('H', 'm3'),
    ('H', 'num_channels'),
    ('I', 'sample_rate'),
    ('H', 'm4'),
    ('I', 'num_sample_frames'),
    ('H', 'm5'),
    ('H', 'm6'),
    ('H', 'm7'),
    ('H', 'm8'),
    ('H', 'm9'),
    ('H', 'm10'),
])

MAX_AMSO_SOUN = 6
AmsoFmt = ('Amso', [
    ('L', 'flags'),
    ('h', 'inner_radius'),
    ('h', 'outer_radius'),
    ('h', 'period_lower_bound'),
    ('h', 'period_delta'),
    ('24s', 'sound_tags', utils.list_pack("AmsoSoundTags", MAX_AMSO_SOUN, ">4s")),
    ('h', 'random_sound_radius'),
    ('10x', None),
    ('12s', 'sound_indexes', utils.list_pack("AmsoSoundIndexes", MAX_AMSO_SOUN, ">h")),
    ('h', 'phase'),
    ('h', 'period'),
])

def parse_soun_header(data):
    return myth_headers.parse_tag(SoundHeaderFmt, data)

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
        p_desc = utils.decode_string(p_desc)
        p_descs.append(p_desc)

    for i, p_meta in enumerate(utils.iter_decode(
        permutation_end, soun_header.permutation_count,
        PermMetaFmt, data
    )):
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
    return myth_headers.parse_tag(AmsoFmt, data)

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
