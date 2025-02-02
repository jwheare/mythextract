requires 60 "6D 79 74 68" ;# myth
big_endian
ascii 32 "Tag name"
ascii 4 "Tag type"
ascii 4 "Tag ID"
uint16 "Unknown 1"
uint16 "Unknown 2"
uint16 "Unknown 3"
uint16 "Unknown 4"
set td_off [int32 "Tag data offset"]
set td_siz [int32 "Tag data size"]
uint16 "Unknown 5"
uint16 "Unknown 6"
ascii 4 "Tag version"