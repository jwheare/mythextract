requires 60 "6D 74 68 32" ;# mth2
big_endian
int16 "Identifier"
int8 "Flags"
int8 "Type"
ascii 32 "Tag name"
ascii 4 "Tag type"
ascii 4 "Tag ID"
set td_off [int32 "Tag data offset"]
set td_siz [int32 "Tag data size"]
uint32 "User data"
int16 "Version"
int8 "Destination"
int8 "Owner index"
ascii 4 "Tag version"