from ctypes import c_int

# Lookup table for our hashin'
HASH_LOOKUP = {
    "sockets" : [
        #############
        # Sockets
        #############
        # Characters
        "RightHand",
        "Head",
        "Eyes",
        "Back",
        "Nose",
        "Chin",
        "LeftHand",
        "LeftFoot",
        
        "RightFoot",
        "Snowmobile",
        "Motorcycle",
    ],

    "animations" : [
        #############
        # Animations
        #############
        # Characters
        "base",
        "StandHip",
        # Weapons
        "SelectMelee",
        "AltIdle_0",
        "AltFire",
        "AltFire1",
        "AltIdle_1",
        "AltIdle_2",
        "AltDeselect",
        "Select1",
        "Idle_0",
        "Idle_1",
        "Idle_2",
        "Deselect",
        "Fire",
        "AltSelect",
        "Select"
    ]
}

'''
HashLookUp
Original hash code reverse engineered from NOLF PS2 rez module
Ported to Python, it relies on overflowing signed integers, hence the ctypes!
'''
class HashLookUp(object):
    def __init__(self, magic_number):
        self._magic_number = magic_number
        pass

    def lookup_hash(self, hash_value, category):
        for string in HASH_LOOKUP[category]:

            hashed = self.hash(string)
            if hashed == c_int(hash_value).value:
                return string

        return None

    def hash(self, name):
        hash_value = c_int(0)
        for char in name:
            char = char.upper()
            byte_char = ord(char)
            byte_char = byte_char & 0xFF
            if (byte_char == 0x2F):
                byte_char = 0x5C
            hash_value.value = hash_value.value + c_int(byte_char).value + hash_value.value * c_int(self._magic_number).value
        return hash_value.value

# End Class

