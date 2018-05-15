import os
from Crypto.Cipher import AES

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import (
    Cipher, algorithms, modes
)

def decrypt_and_verify(ct, nonce, mac, key):
    cipher = AES.new(key, AES.MODE_GCM, nonce)
    return cipher.decrypt_and_verify(ct, mac)

def encrypt_and_digest(pt, key):
    cipher = AES.new(key, AES.MODE_GCM)
    ct, mac = cipher.encrypt_and_digest(pt)
    return ct, cipher.nonce, mac

cipher = None
def encrypt(key, plaintext, associated_data):
    global cipher

    # Generate a random 96-bit IV.
    iv = os.urandom(12)

    # Construct an AES-GCM Cipher object with the given key and a
    # randomly generated IV.
    if not cipher:
        print("HERE!")
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        )
    else:
#        cipher.algorithm = algorithms.AES(key)
        cipher.mode=modes.GCM(iv)

    encryptor = cipher.encryptor()

    # associated_data will be authenticated but not encrypted,
    # it must also be passed in on decryption.
#    encryptor.authenticate_additional_data(associated_data)

    # Encrypt the plaintext and get the associated ciphertext.
    # GCM does not require padding.
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    return (iv, ciphertext, encryptor.tag)

def decrypt(key, associated_data, iv, ciphertext, tag):
    # Construct a Cipher object, with the key, iv, and additionally the
    # GCM tag used for authenticating the message.
    global cipher
    if not cipher:
        print("HERE!")
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
    else:
#        cipher.algorithm = algorithms.AES(key)
        cipher.mode=modes.GCM(iv, tag)

    decryptor = cipher.decryptor()
    # We put associated_data back in or the tag will fail to verify
    # when we finalize the decryptor.
#    decryptor.authenticate_additional_data(associated_data)

    # Decryption gets us the authenticated plaintext.
    # If the tag does not match an InvalidTag exception will be raised.
    return decryptor.update(ciphertext) + decryptor.finalize()

key = b'x' * 32

import timeit
def openssl_version():
    iv, ciphertext, tag = encrypt(
        key,
        b"a" * 4096,
        b"authenticated but not encrypted payload"
    )

    decrypt(
        key,
        b"authenticated but not encrypted payload",
        iv,
        ciphertext,
        tag
    )


def crypto_version():
    (ct, nonce, mac) = encrypt_and_digest(b"a" * 4096, key)
    decrypt_and_verify(ct, nonce, mac, key)


print("openssl version", timeit.timeit('openssl_version()', number=10000, globals=globals()))
#print("pycrypto version", timeit.timeit('crypto_version()', number=10000, globals=globals()))
