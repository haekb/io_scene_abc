#
# Gotham City Imposters (and probably others) model file seems to be zlib compressed.
# Here's a quick decompress script, it'll skip past some header bytes.
#
# Just drag and drop files here!
#
import zlib, sys, os

if not os.path.isdir('./out'):
    os.makedirs('./out')

file_paths = sys.argv[1:]
for path in file_paths:
    if not os.path.isfile(path):
        continue
    
    file_name = os.path.basename(path)

    fp = open(path, 'rb')
    fp.seek(8, 1)
    out_file_data = zlib.decompress(fp.read())
    f = open('./out/%s' % file_name, 'wb')
    f.write(out_file_data)
    f.close()

    print("Decompressed file to ./out/%s" % file_name)

