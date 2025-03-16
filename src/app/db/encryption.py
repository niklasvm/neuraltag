from cryptography.fernet import Fernet
import base64


def encrypt_token(token: str, key: bytes) -> str:
    """Encrypts an access token."""
    f = Fernet(key)
    encrypted_token = f.encrypt(token.encode())
    return base64.urlsafe_b64encode(encrypted_token).decode()


def decrypt_token(encrypted_token: str, key: bytes) -> str:
    """Decrypts an access token."""
    f = Fernet(key)
    encrypted_token_bytes = base64.urlsafe_b64decode(encrypted_token)
    decrypted_token = f.decrypt(encrypted_token_bytes).decode()
    return decrypted_token


# Example Usage:


# key = os.environ["ENCRYPTION_KEY"]

# key_bytes = key.encode()

# # Store the key securely

# token = "your_access_token_here"
# encrypted_token = encrypt_token(token, key_bytes)
# decrypted_token = decrypt_token(encrypted_token, key_bytes)

# print(f"Original Token: {token}")
# print(f"Encrypted Token: {encrypted_token}")
# print(f"Decrypted Token: {decrypted_token}")

# assert token == decrypted_token
# #Store the encrypted token in the database.
# #Retrive the encryped token, and the key from their secure locations, and then decrypt the token.
