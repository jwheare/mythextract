#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys
import time

TIME = (os.environ.get('TIME') == '1')

def main(input_path, output_path):
    convert(input_path, output_path)

def get_sar(path):
    """Return SAR as a float (height / width)"""
    t = time.perf_counter()
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=sample_aspect_ratio",
        "-of", "json",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    TIME and print('get_sar', f'{(time.perf_counter() - t):.3f}')
    sar_str = data["streams"][0].get("sample_aspect_ratio", "1:1")
    # convert "w:h" string to float
    if ':' in sar_str:
        w, h = map(int, sar_str.split(':'))
        return h / w
    elif sar_str:
        return 1/float(sar_str)
    else:
        return 1.0

def convert(input_path, output_path):
    sar = get_sar(input_path)
    t = time.perf_counter()
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", input_path,
        "-vf", f"scale=iw:ih*{sar}:flags=bicubic,setsar=1:1",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ])
    TIME and print('convert', f'{(time.perf_counter() - t):.3f}')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <input_path> <output_path>")
        sys.exit(1)
    
    input_path = pathlib.Path(sys.argv[1])
    output_path = pathlib.Path(sys.argv[2])

    try:
        main(input_path, output_path)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
