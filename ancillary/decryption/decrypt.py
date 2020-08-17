import argparse
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

"""
John Newman
April 8, 2019

This program is used for decrypting files encrypted by watchtower. The first
bytes of the file contain the character length (int) of the encrypted Fernet
key. The key is expected to be base64 encoded and to appear in the file
following the length and a space.

File format:
"{length_int} {encoded_encrypted_key}{encrypted_data}"

The supplied private pem path is used to decrypt the Fernet key.
"""

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--private-pem', type=str, help='path to the private key', required=True)
parser.add_argument('-i', '--file-path', type=str, help='path to encrypted file', required=True)
parser.add_argument('-o', '--output-path', type=str, help='path to output decrypted file', required=True)
supplied_args = vars(parser.parse_args())


with open(supplied_args['private_pem'], 'rb') as key_file:
    private_key = serialization.load_pem_private_key(key_file.read(),
                                                     password=None,
                                                     backend=default_backend())
    with open(supplied_args['file_path'], 'rb') as encrypted_file:
        file_string = encrypted_file.read()
        separator = file_string.find(b' ')
        key_size = int(file_string[:separator])
        encrypted_key = base64.b64decode(file_string[separator+1:key_size+separator+1])
        decrypted_key = private_key.decrypt(encrypted_key,
                                            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                         algorithm=hashes.SHA256(),
                                                         label=None))
        f = Fernet(decrypted_key)
        decrypted_data = f.decrypt(file_string[separator + key_size:])
        with open(supplied_args['output_path'], 'ab') as output_file:
            output_file.write(decrypted_data)
