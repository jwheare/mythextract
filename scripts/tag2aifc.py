#!/usr/bin/env python3
import sys
import struct


def main(tag_path, aifc_path):
    """
    Parse a Myth TFL soun tag file and output the aifc file
    
    Args:
        tag_path (str): Path to the soun tag file
        aifc_path (str): Path to save the aifc
    """
    try:
        with open(tag_path, 'rb') as infile:
            data = infile.read()

        (tag_id, num_sample_frames, sound_data) = parse_soun_tag(data)

        if not aifc_path:
            aifc_path = f'./aifc/{tag_id}.aifc'

        aifc = generate_aifc(num_sample_frames, sound_data)
        
        if prompt(aifc_path):
            with open(aifc_path, 'wb') as aifc_file:
                aifc_file.write(aifc)
                print(f"AIFC extracted. Output saved to {aifc_path}")
    
    except FileNotFoundError:
        print(f"Error: File not found - {tag_path}")


def prompt(aifc_path):
    # return True
    response = input(f"Write {aifc_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

# [000:032] 32: text - name - right packed with null
# [032:036]  4: text - tag type
# [036:040]  4: text - tag ID
# [040:052] 12: unknown
# [052:056]  4: unsigned long - length_a
# [056:060]  4: unknown
# [060:064]  4: text - tag version
# [064:088] 24: unknown
# [088:092]  4: unsigned long - length_b
# [092:132] 40: unknown
# [132:134]  2: unknown
# [134:148] 14: text - desc
# [148:176] 28: unknown
# [176:180]  4: unsigned long - numSampleFrames
# [180:192] 12: unknown
# [192:]    --: soundData


def parse_soun_tag(data):
    data_length = len(data)
    print("Total data length: %i" % data_length)
    header_size = 192

    if data_length < header_size:
        raise ValueError(
            "Binary data is too short for expected header format (%i)" %
            header_size
        )
    try:
        (
            name, tag_type, tag_id,
            a1, a2, a3,
            length_a,
            b1,
            tag_version,
            c1, c2, c3, c4, c5, c6,
            length_b,
            d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11,
            desc,
            e1, e2, e3, e4, e5, e6, e7,
            num_sample_frames,
            f1, f2, f3,
        ) = struct.unpack(""">
            32s 4s 4s
            3I
            I
            I
            4s
            6I
            I
            10I h
            14s
            7I
            I
            3I
        """, data[:header_size])
        name = name.rstrip(b'\0').decode('mac-roman')
        tag_type = tag_type.decode('mac-roman')
        desc = desc.decode('mac-roman')
        tag_id = tag_id.decode('mac-roman')
        tag_version = tag_version.decode('mac-roman')

        sound_data = data[header_size:]
        sound_length = len(sound_data)
        print(""" Tag: [%s]
Type: [%s]
  ID: [%s]
Vers: [%s]
Desc: [%s]
length_a=%i [diff=%i] length_b=%i [diff=%i]
numSampleFrames: %i
sound length: %i""" % (
            name,
            tag_type, tag_id,
            tag_version, desc,
            length_a, data_length - length_a, length_b, data_length - length_b,
            num_sample_frames, sound_length
        ))
        print('a', a1, a2, a3)
        print('b', b1)
        print('c', c1, c2, c3, c4, c5, c6)
        print('d', d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11)
        print('e', e1, e2, e3, e4, e5, e6, e7)
        print('f', f1, f2, f3)
        print('from length_a', data[length_a:].hex())
        print('from length_b', data[length_b:].hex())
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

    return (tag_id, num_sample_frames, sound_data)


def generate_aifc(num_sample_frames, sound_data):
    AIFC_VERSION_1 = 2726318400
    sample_rate_80_float = b'\x40\x0D\xAC\x44\x00\x00\x00\x00\x00\x00'
    num_channels = 1
    sample_size = 16
    offset = 0
    block_size = 0
    comm_data = struct.pack(
        ">h L h 10s 4s 8p", 
        num_channels, num_sample_frames, sample_size, sample_rate_80_float,
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
