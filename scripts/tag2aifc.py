#!/usr/bin/env python3
import sys
import os
import struct
import pathlib

import myth_headers
import myth_sound

AIFC_VERSION_1 = 2726318400
SAMPLE_RATE_80_FLOAT_22050 = b'\x40\x0D\xAC\x44\x00\x00\x00\x00\x00\x00'
IMA4_BYTES_PER_FRAME = 34
IMA_COMPRESSION_RATIO = 4

DEBUG = (os.environ.get('DEBUG') == '1')

def main(tag_path, aifc_path):
    """
    Parse a Myth TFL or Myth II soun tag file and output the aifc file
    """
    data = myth_headers.load_file(tag_path)

    (game_version, tag_id, permutations) = parse_soun_tag(data)

    if not aifc_path:
        aifc_path = f'../output/aifc/{game_version}-{tag_id}.aifc'
        path = pathlib.Path(sys.path[0], aifc_path).resolve()
    else:
        path = pathlib.Path(aifc_path).with_suffix('.aifc')

    perm_count = len(permutations)

    if prompt(path, perm_count):
        for i, (desc, num_channels, sample_size, num_sample_frames, sound_data) in enumerate(permutations):
            aifc = generate_aifc(num_channels, sample_size, num_sample_frames, sound_data)
            
            perm_path = path
            if (perm_count > 1):
                perm_path = path.with_stem(f'{path.stem}-{i}')

            pathlib.Path(perm_path.parent).mkdir(parents=True, exist_ok=True)
            with open(perm_path, 'wb') as aifc_file:
                aifc_file.write(aifc)
                print(f"AIFC extracted. Output saved to {perm_path} ({desc})")


def prompt(prompt_path, perm_count):
    # return True
    prefix = ''
    suffix = ''
    if (perm_count > 1):
        prompt_path = prompt_path.with_stem(f'{prompt_path.stem}-n')
        prefix = f'{perm_count}x permutations '
        suffix = ' (n=permutation)'
    response = input(f"Write {prefix}to: {prompt_path}{suffix} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_soun_tag(data):
    try:
        data_size = len(data)

        header = myth_headers.parse_header(data)

        soun_header_size = myth_sound.SOUN_HEADER_SIZE
        soun_header_end = myth_headers.TAG_HEADER_SIZE + soun_header_size

        soun_header = myth_sound.parse_soun_header(data)

        permutation_end = soun_header_end + soun_header.permutations_size
        meta_struct = """>
            H H
            H
            H
            H
            I
            H
            I
            H H H H H H
        """
        perm_size = 32
        check_perm_size = soun_header.permutation_count * perm_size
        actual_perm_size = permutation_end - soun_header_end
        meta_length = struct.calcsize(meta_struct)
        total_meta_length = (soun_header.permutation_count * meta_length)

        header_end = permutation_end + total_meta_length
        sound_data = data[header_end:]
        sound_length = len(sound_data)

        # Accumulators
        p_descs = []
        p_metas = []
        permutations = []

        sound_data_offset = 0
        total_sample_frames = 0
        for perm_i in range(soun_header.permutation_count):
            start = soun_header_end + (perm_i * perm_size)
            end = start + perm_size
            (p1, p2, p3, p_desc,) = struct.unpack(">H H H 26s", data[start:end])
            p_desc = myth_headers.decode_string(p_desc)
            p_descs.append((p1, p2, p3, p_desc))

            meta_start = permutation_end + (perm_i * meta_length)
            meta_end = meta_start + meta_length
            p_meta = (
                m1, m2,
                sample_size,
                m3,
                num_channels,
                sample_rate,
                m4,
                num_sample_frames,
                m5, m6, m7, m8, m9, m10
            ) = struct.unpack(meta_struct, data[meta_start:meta_end])
            permutation_sound_length = num_sample_frames * IMA4_BYTES_PER_FRAME
            permutation_sound_end = sound_data_offset + permutation_sound_length
            perm_sound_data = sound_data[sound_data_offset:permutation_sound_end]

            permutations.append((p_desc, num_channels, sample_size, num_sample_frames, perm_sound_data))
            p_metas.append(p_meta)

            sound_data_offset = permutation_sound_end
            total_sample_frames = total_sample_frames + num_sample_frames

        total_sample_frames * IMA4_BYTES_PER_FRAME

        if DEBUG:
            print(f"""Total data length: {data_size}
perm_size = {soun_header.permutation_count} x 32 = {soun_header.permutations_size} ({check_perm_size} = {actual_perm_size})
meta_size = {soun_header.permutation_count} x {meta_length} = {total_meta_length}
  header[{myth_headers.TAG_HEADER_SIZE}] + soun_header[{soun_header_size}]
+ perm_size[{soun_header.permutations_size}] + meta_size[{total_meta_length}]
= header_end[{header_end}]
sound length: {sound_length}
-----
 Tag: [{header.name}]
Type: [{header.tag_type}]
  ID: [{header.tag_id}]
TDOF: {header.tag_data_offset}
TDSZ: {header.tag_data_size}
head: {header}
Vers: [{header.signature}]
----- 0:{myth_headers.TAG_HEADER_SIZE} = {myth_headers.TAG_HEADER_SIZE}
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
PSIZ: {soun_header.permutations_size}
  d6: {soun_header.d6}
  d7: {soun_header.d7}
  d8: {soun_header.d8}
  d9: {soun_header.d9}
----- {myth_headers.TAG_HEADER_SIZE}:{soun_header_end} = {soun_header_size}
----- 0:{soun_header_end-myth_headers.TAG_HEADER_SIZE} = {soun_header_size}
Perm: {len(p_descs)}"""
            )
            for (p1, p2, p3, p_desc) in p_descs:
                print(f"""      {p1} {p2} {p3} [{p_desc}]""")
            print(
                "----- "
                f"""{soun_header_end}:{permutation_end} = {soun_header.permutations_size} = {actual_perm_size}
----- {soun_header_end-myth_headers.TAG_HEADER_SIZE}:{permutation_end-myth_headers.TAG_HEADER_SIZE} = {soun_header.permutations_size} = {actual_perm_size}
Meta: {len(p_metas)}"""
            )
            for (
                m1, m2,
                sample_size,
                m3,
                num_channels,
                sample_rate,
                m4,
                num_sample_frames,
                m5, m6, m7, m8, m9, m10
            ) in p_metas:
                perm_size = num_sample_frames * IMA4_BYTES_PER_FRAME
                perm_s = round((IMA_COMPRESSION_RATIO * sample_size * num_sample_frames) / (num_channels * sample_rate), 3)
                perm_m = round(perm_s // 60)
                perm_rem_s = round(perm_s % 60, 3)

                print(f"""  unknown1: {m1} {m2}
  channels: {num_channels}
  unknown2: {m3}
 samp_size: {sample_size}
 samp_rate: {sample_rate}
  unknown4: {m4}
samp_frame: {num_sample_frames}
  unknown5: {m5} {m6} {m7} {m8} {m9} {m10}
[soun_len]: {num_sample_frames} * {IMA4_BYTES_PER_FRAME} = {perm_size}
[soun_dur]: {perm_s}s / {perm_m}m{perm_rem_s}s
      -----"""
                )
            print(
                "----- "
                f"""{permutation_end}:{header_end} = {total_meta_length}
----- {permutation_end-myth_headers.TAG_HEADER_SIZE}:{header_end-myth_headers.TAG_HEADER_SIZE} = {total_meta_length}
AIFC: length = {sound_length}
----- {header_end}:{data_size} = {sound_length}
----- {header_end-myth_headers.TAG_HEADER_SIZE}:{data_size-myth_headers.TAG_HEADER_SIZE} = {sound_length}"""
                )

        return (header.signature, header.tag_id, permutations)
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
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
