import zlib, sys

#
# Gotham City Imposters (and probably others) model file seems to be zlib compressed.
# Here's a quick decompress script, it'll skip past some header bytes.
#

# Insert model name here, this expects the file in the current directory
# The file will be saved as out.model00p
fp = open('bat.mdl', 'rb')

#
# Don't touch below here!!
#
fp.seek(8, 1)
file_data = zlib.decompress(fp.read())
f = open('out.model00p', 'wb')
f.write(file_data)
f.close()