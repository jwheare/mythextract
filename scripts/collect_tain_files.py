#!/usr/bin/env python3
import sys
import csv
import pathlib
import zipfile
import shutil

import myth_headers

def main(tain_dir, input_csv, output_dir):
    with open(input_csv, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for [filename, slug, version] in csvreader:
            filepath = tain_dir / filename
            tain_url = f'https://tain.totalcodex.net/items/show/{slug}'
            if filepath.exists():
                try:
                    with zipfile.ZipFile(filepath) as plugin_zip:
                        for file_info in plugin_zip.infolist():
                            if not file_info.is_dir():
                                try:
                                    with plugin_zip.open(file_info) as info_file:
                                        plugin_name = pathlib.Path(file_info.filename).name
                                        header_data = info_file.read(128)
                                        valid = False
                                        try:
                                            myth_headers.parse_mono_header(
                                                plugin_name, header_data
                                            )
                                            valid = True
                                        except ValueError:
                                            pass
                                        if valid:
                                            with open(output_dir / plugin_name, 'wb') as plugin_out:
                                                plugin_out.write(header_data)
                                                shutil.copyfileobj(info_file, plugin_out)
                                                print(f'"{plugin_out.name}",{version},{slug}')
                                except NotImplementedError as exc:
                                    print('!!!', exc, file_info, filename, tain_url)
                except zipfile.BadZipFile:
                    print('!!! not zip', filename, tain_url)
            else:
                print('!!! missing', filename, tain_url)

    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <tain_dir> <input_csv> <output_dir>")
        sys.exit(1)
    
    tain_dir = pathlib.Path(sys.argv[1])
    input_csv = sys.argv[2]
    output_dir = pathlib.Path(sys.argv[3])

    try:
        main(tain_dir, input_csv, output_dir)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
