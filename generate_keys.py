
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

private_key = ec.generate_private_key(ec.SECP256R1())

private_numbers = private_key.private_numbers()
public_numbers = private_key.public_key().public_numbers()

def encode_key(value, length):
    raw = value.to_bytes(length, "big")
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

private_value = encode_key(private_numbers.private_value, 32)
public_value = base64.urlsafe_b64encode(
    b"\x04"
    + public_numbers.x.to_bytes(32, "big")
    + public_numbers.y.to_bytes(32, "big")
).decode().rstrip("=")

print("PRIVATE KEY:")
print(private_value)
print("\nPUBLIC KEY:")
print(public_value)
