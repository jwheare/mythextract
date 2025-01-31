#!/usr/bin/env python3
import sys
import struct
import pathlib
from collections import namedtuple

TAG_HEADER_SIZE = 64

AIFC_VERSION_1 = 2726318400
SAMPLE_RATE_80_FLOAT_22050 = b'\x40\x0D\xAC\x44\x00\x00\x00\x00\x00\x00'
IMA4_BYTES_PER_FRAME = 34

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

def main(tag_path, aifc_path):
    """
    Parse a Myth TFL or Myth II soun tag file and output the aifc file
    """
    try:
        with open(tag_path, 'rb') as infile:
            data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {tag_path}")
        sys.exit(1)

    (game_version, tag_id, permutations) = parse_soun_tag(data)

    if not aifc_path:
        aifc_path = f'./aifc/{game_version}-{tag_id}.aifc'

    path = pathlib.Path(aifc_path).with_suffix('.aifc')

    perm_count = len(permutations)

    if prompt(perm_count, path):
        for i, (desc, num_channels, sample_size, num_sample_frames, sound_data) in enumerate(permutations):
            aifc = generate_aifc(num_channels, sample_size, num_sample_frames, sound_data)
            
            perm_path = path
            if (perm_count > 1):
                perm_path = path.with_stem(f'{path.stem}-{i}')

            with open(perm_path, 'wb') as aifc_file:
                aifc_file.write(aifc)
                print(f"AIFC extracted. Output saved to {perm_path} ({desc})")


def prompt(perm_count, prompt_path):
    # return True
    prefix = ''
    suffix = ''
    if (perm_count > 1):
        prompt_path = prompt_path.with_stem(f'{prompt_path.stem}-n')
        prefix = f'{perm_count}x permutations '
        suffix = ' (n=permutation)'
    response = input(f"Write {prefix}to: {prompt_path}{suffix} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_tfl_header(header):
    return decode_header(TFLHeader._make(struct.unpack(TFLHeaderFmt, header)))

def parse_sb_header(header):
    return decode_header(SBHeader._make(struct.unpack(SBHeaderFmt, header)))

def decode_header(header):
    return header._replace(
        name=header.name.rstrip(b'\0').decode('mac-roman'),
        tag_type=header.tag_type.decode('mac-roman'),
        tag_id=header.tag_id.decode('mac-roman'),
        tag_version=header.tag_version.decode('mac-roman')
    )

def parse_soun_tag(data):
    try:
        data_size = len(data)

        game_version = data[60:64]
        is_tfl = game_version == b'myth'
        is_sb = game_version == b'mth2'

        if not is_tfl and not is_sb:
            raise ValueError(f"Incompatible game version: {game_version}")

        if is_tfl:
            header = parse_tfl_header(data[:TAG_HEADER_SIZE])
        elif is_sb:
            header = parse_sb_header(data[:TAG_HEADER_SIZE])
        soun_header = """>
            L h h H
            H H H H

            h
            L L

            L H H
            L L L

            I I I I
        """
        soun_header_size = struct.calcsize(soun_header)
        soun_header_end = TAG_HEADER_SIZE + soun_header_size
        (
            flags, loudness, play_fraction, external_frequency_modifier,
            pitch_lower_bound, pitch_delta, volume_lower_bound, volume_delta,

            first_subtitle_within_string_list_index,
            sound_offset, sound_size,

            subtitle_string_list_tag, subtitle_string_list_index, unused,
            permutation_count, permutations_offset, permutations_size,

            d6, d7, d8, d9
        ) = struct.unpack(soun_header, data[TAG_HEADER_SIZE:soun_header_end])

        permutation_end = soun_header_end + permutations_size
        meta_struct = """>
            H H
            H
            H
            H
            H
            H
            H H
            H
            H H H H H H
        """
        perm_size = 32
        check_perm_size = permutation_count * perm_size
        actual_perm_size = permutation_end - soun_header_end
        meta_length = struct.calcsize(meta_struct)
        total_meta_length = (permutation_count * meta_length)

        header_end = permutation_end + total_meta_length
        sound_data = data[header_end:]
        sound_length = len(sound_data)

        # Accumulators
        p_descs = []
        p_metas = []
        permutations = []

        sound_data_offset = 0
        total_sample_frames = 0
        for perm_i in range(permutation_count):
            start = soun_header_end + (perm_i * perm_size)
            end = start + perm_size
            (p1, p2, p3, p_desc,) = struct.unpack(">H H H 26s", data[start:end])
            p_desc = p_desc.split(b'\0', 1)[0].decode('mac-roman')
            p_descs.append((p1, p2, p3, p_desc))

            meta_start = permutation_end + (perm_i * meta_length)
            meta_end = meta_start + meta_length
            p_meta = (
                m1, m2,
                sample_size,
                m3,
                num_channels,
                m4,
                sample_rate,
                m5, m6,
                num_sample_frames,
                m7, m8, m9, m10, m11, m12
            ) = struct.unpack(meta_struct, data[meta_start:meta_end])
            permutation_sound_length = num_sample_frames * IMA4_BYTES_PER_FRAME
            permutation_sound_end = sound_data_offset + permutation_sound_length
            perm_sound_data = sound_data[sound_data_offset:permutation_sound_end]

            permutations.append((p_desc, num_channels, sample_size, num_sample_frames, perm_sound_data))
            p_metas.append(p_meta)

            sound_data_offset = permutation_sound_end
            total_sample_frames = total_sample_frames + num_sample_frames

        total_sample_frames * IMA4_BYTES_PER_FRAME

        DEBUG = True
        if DEBUG:
            print(f"""Total data length: {data_size}
perm_size = {permutation_count} x 32 = {permutations_size} ({check_perm_size} = {actual_perm_size})
meta_size = {permutation_count} x {meta_length} = {total_meta_length}
  header[{TAG_HEADER_SIZE}] + soun_header[{soun_header_size}]
+ perm_size[{permutations_size}] + meta_size[{total_meta_length}]
= header_end[{header_end}]
sound length: {sound_length}
-----
 Tag: [{header.name}]
Type: [{header.tag_type}]
  ID: [{header.tag_id}]
TDOF: {header.tag_data_offset}
TDSZ: {header.tag_data_size}
head: {header}
Vers: [{header.tag_version}]
----- 0:{TAG_HEADER_SIZE} = {TAG_HEADER_SIZE}
flag: {flags}
loud: {loudness}
  pf: {play_fraction}
 efm: {external_frequency_modifier}
 plb: {pitch_lower_bound}
  pd: {pitch_delta}
 vlb: {volume_lower_bound}
  vd: {volume_delta}
-----
fsli: {first_subtitle_within_string_list_index}
SOFF: {sound_offset}
SSIZ: {sound_size}
 slt: {subtitle_string_list_tag}
 sli: {subtitle_string_list_index}
unus: {unused}
PCNT: {permutation_count}
POFF: {permutations_offset}
PSIZ: {permutations_size}
  d6: {d6}
  d7: {d7}
  d8: {d8}
  d9: {d9}
----- {TAG_HEADER_SIZE}:{soun_header_end} = {soun_header_size}
----- 0:{soun_header_end-TAG_HEADER_SIZE} = {soun_header_size}
Perm: {len(p_descs)}"""
            )
            for (p1, p2, p3, p_desc) in p_descs:
                print(f"""      {p1} {p2} {p3} [{p_desc}]""")
            print(
                "----- "
                f"""{soun_header_end}:{permutation_end} = {permutations_size} = {actual_perm_size}
----- {soun_header_end-TAG_HEADER_SIZE}:{permutation_end-TAG_HEADER_SIZE} = {permutations_size} = {actual_perm_size}
Meta: {len(p_metas)}"""
            )
            for (
                m1, m2,
                sample_size,
                m3,
                num_channels,
                m4,
                sample_rate,
                m5, m6,
                num_sample_frames,
                m7, m8, m9, m10, m11, m12
            ) in p_metas:
                print(f"""  unknown1: {m1} {m2}
  channels: {num_channels}
  unknown2: {m3}
 samp_size: {sample_size}
  unknown3: {m4}
 samp_rate: {sample_rate}
  unknown4: {m5} {m6}
samp_frame: {num_sample_frames}
  unknown5: {m7} {m7} {m8} {m9} {m10} {m11} {m12}
[soun_len]: {num_sample_frames} * {IMA4_BYTES_PER_FRAME} = {num_sample_frames * IMA4_BYTES_PER_FRAME}
      -----"""
                )
            print(
                "----- "
                f"""{permutation_end}:{header_end} = {total_meta_length}
----- {permutation_end-TAG_HEADER_SIZE}:{header_end-TAG_HEADER_SIZE} = {total_meta_length}
AIFC: length = {sound_length}
----- {header_end}:{data_size} = {sound_length}
----- {header_end-TAG_HEADER_SIZE}:{data_size-TAG_HEADER_SIZE} = {sound_length}"""
                )

        return (header.tag_version, header.tag_id, permutations)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")


def generate_aifc(num_channels, sample_size, num_sample_frames, sound_data):
    offset = 0
    block_size = 0
    comm_data = struct.pack(
        ">h L h 10s 4s 8p", 
        num_channels, num_sample_frames, sample_size, SAMPLE_RATE_80_FLOAT_22050,
        b'ima4', b'IMA 4:1'
    )
    comm_length = len(comm_data)
    sound_length = len(sound_data)
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
        sound_data
    )
    form_length = len(form_data)
    return struct.pack(
        f">4s I {form_length}s",
        b'FORM', form_length, form_data
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tag2aifc.py <input_file> [<output_file>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if len(sys.argv) == 3:
        output_file = sys.argv[2]
    else:
        output_file = None
    
    try:
        main(input_file, output_file)
    except KeyboardInterrupt:
        sys.exit(130)
