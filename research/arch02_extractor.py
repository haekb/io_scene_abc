# 
# Arch 02 Extractor
# Created by HeyThereCoffeee
# Special thanks to thecanonmaster 
# https://github.com/thecanonmaster/ArchExtractor
#

import os
import struct
import zlib

#
# Helpers
#

'''
Utility functions for reading from the file.

fmt reference:
https://docs.python.org/3/library/struct.html#format-characters
'''
def unpack(fmt, f):
    return struct.unpack(fmt, f.read(struct.calcsize(fmt)))


def pack(fmt, f, values):
    f.write(struct.pack(fmt, values))

# Big-Endian unpack
def bunpack(fmt, f):
    fmt = ">%s" % fmt 
    return unpack(fmt, f)

def read_string(length, f):
    return f.read(length).decode('ascii')

#
# Arch Class
# 
class Arch02(object):
    def __init__(self):
        self.header = None
        self.string_table = None
        self.files = []
        self.directories = []

        self.archive_name = ""
        self.file_pointer = None

    ###################################################################################
    # Start of class zone
    ###################################################################################

    class Header(object):
        def __init__(self):
            self.tag = ""
            self.version = -1
            self.string_table_count = 0
            self.directory_count = 0
            self.file_count = 0
            self.unk_1 = 0
            self.unk_2 = 0
            self.unk_3 = 0
            self.hash = ''

        def read(self, f):
            self.tag = read_string(4, f)
            self.version = bunpack('I', f)[0]
            self.string_table_count = bunpack('I', f)[0]
            self.directory_count = bunpack('I', f)[0]
            self.file_count = bunpack('I', f)[0]
            self.unk_1 = bunpack('I', f)[0]
            self.unk_2 = bunpack('I', f)[0]
            self.unk_3 = bunpack('I', f)[0]
            self.hash = bunpack('16B', f)

    class StringTable(object):
        def __init__(self):
            self.table = ""

        def read(self, length, f):
            self.table = read_string(length, f)

        def get_string(self, offset):
            value = self.table[offset:]

            # Okay we need to find the next null character now!
            null_terminator = -1
            for (index, char) in enumerate(value):
                if char == '\x00':
                    null_terminator = index
                    break

            # Make sure we actually ran through the string
            assert(null_terminator != -1)

            length = offset + null_terminator
                
            return self.table[offset:length]

    class FileInfo(object):
        def __init__(self, string_table):
            self.name = ""
            self.name_offset = 0
            self.file_offset = 0
            self.compressed_size = 0
            self.uncompressed_size = 0
            self.compression = -1

            self.string_table = string_table
        
        def read(self, f):
            self.name_offset = bunpack('I', f)[0]
            self.file_offset = bunpack('Q', f)[0] 
            self.compressed_size = bunpack('Q', f)[0] 
            self.uncompressed_size = bunpack('Q', f)[0] 
            self.compression = bunpack('I', f)[0]

            # Grab the name from the string table
            self.name = self.string_table.get_string(self.name_offset)
            #print("Discovered file: %s" % self.name)

    class DirectoryInfo(object):
        def __init__(self, string_table):
            self.name = ""
            self.name_offset = 0
            self.first_sub_index = 0
            self.next_index = 0
            self.file_count = 0

            self.string_table = string_table

        def read(self, f):
            self.name_offset = bunpack('I', f)[0]
            self.first_sub_index = bunpack('I', f)[0]
            self.next_index = bunpack('I', f)[0]
            self.file_count = bunpack('I', f)[0]

            # Grab the name from the string table
            self.name = self.string_table.get_string(self.name_offset)
            #print("Discovered directory: %s" % self.name)

    ###################################################################################
    # End of class zone
    ###################################################################################

    #
    # Extract the files/folders from the archive
    #
    def extract(self, out_folder = './out'):
        print("Extracting %s to %s" % (self.archive_name, out_folder))
        
        # Create the output folder if needed
        if not os.path.isdir(out_folder):
            print("Could not find %s, creating it now..." % out_folder)
            os.makedirs(out_folder)


        # Keyed by directory!
        files_in_directories = {}
        total_files_processed = 0

        # Now create the folders, and process the files
        for directory in self.directories:
            directory_path = os.path.join(out_folder, directory.name)
            if not os.path.isdir(directory_path):
                os.makedirs(directory_path)

            files_in_directories[directory.name] = []
            for i in range(directory.file_count):
                current_file_index = i + total_files_processed

                files_in_directories[directory.name].append(self.files[current_file_index])

            # Okay remember how many files we've processed so far...
            total_files_processed += directory.file_count

        # Now we can finally extract!

        # Re-open our file
        archive_fp = open(self.archive_path, 'rb')
        # Seek to the binary position
        archive_fp.seek(self.binary_position, 0)

        errors = []

        for (directory, file_list) in files_in_directories.items():
            for file in file_list:

                # Oh boy...
                file_path = os.path.join(os.path.join(out_folder, directory), file.name)

                with open(file_path, 'wb') as f:
                    
                    # No compression? That's okay, just copy the file as-is.
                    if file.compression == 0:
                        f.write(archive_fp.read(file.uncompressed_size))
                    else:
                        # Debug
                        #f.write(archive_fp.read(file.compressed_size))

                        current_size = 0
                        chunks = 0

                        while current_size < file.compressed_size:
                            size_compressed = bunpack('I', archive_fp)[0]
                            size_uncompressed = bunpack('I', archive_fp)[0]

                            data = archive_fp.read(size_compressed)
                            try:
                                # Data needs to be deflated (not standard decompress!)
                                f.write(zlib.decompress(data, wbits= -zlib.MAX_WBITS))
                            except Exception:
                                errors.append(file_path)
                                # For some reason we couldn't deflate...
                                print("Error decompressing data, dumping compressed")
                                f.write(data)

                            # Fix offset
                            offset = archive_fp.tell() % 4
                            if offset: archive_fp.read(4 - offset)

                            current_size += size_compressed + 8 + (4 - offset)
                            chunks += 1

                            #print("FTELL ", archive_fp.tell())

                        print("Wrote %s in %d chunks" % (file.name, chunks))


        # Close the archive
        archive_fp.close()
                        
        if len(errors) > 0:
            print("Couldn't decompress the %d files" % len(errors))
            print(errors)

        print("Finished!")
            

    # 
    # Actually read the archive
    #
    def read(self, path = "./Layer.Arch02"):

        self.archive_path = path
        self.archive_name = os.path.basename(path)

        with open(path, 'rb') as f:
            self.header = self.Header()
            self.header.read(f)

            self.string_table = self.StringTable()
            self.string_table.read(self.header.string_table_count, f)

            self.files = []
            for _ in range(self.header.file_count):
                file = self.FileInfo(self.string_table)
                file.read(f)
                self.files.append(file)

            self.directories = []
            for _ in range(self.header.directory_count):
                directory = self.DirectoryInfo(self.string_table)
                directory.read(f)
                self.directories.append(directory)

            self.binary_position = f.tell()

            print("Finished reading archive headers")







#
# Init
# 

arch_02 = Arch02()
arch_02.read('D:/GameDev/io_scene_lithtech/research/test files/Layer.Arch02')
arch_02.extract('D:/GameDev/io_scene_lithtech/research/test files/arch_out')
