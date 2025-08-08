"""
Encryption service for ImaniPay Blockchain Service.

This module provides comprehensive encryption and decryption functionality
for protecting sensitive data such as private keys, payment information,
and personal data.
"""

import logging
import os
import base64
import hashlib
from typing import Optional, Union, Dict, Any
from uuid import UUID

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(Exception):
    """Exception raised when decryption fails."""
    pass


class KeyDerivationError(Exception):
    """Exception raised when key derivation fails."""
    pass


class EncryptionService:
    """Comprehensive encryption service for sensitive data protection."""
    
    def __init__(self):
        self.logger = logger
        self._master_key = self._get_or_create_master_key()
        self._backend = default_backend()
    
    # ========================================================================
    # Symmetric Encryption (for general sensitive data)
    # ========================================================================
    
    async def encrypt_sensitive_data(
        self, 
        data: str, 
        user_id: Optional[UUID] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Encrypt sensitive data using symmetric encryption.
        
        Args:
            data: Data to encrypt
            user_id: Optional user ID for key derivation
            additional_context: Optional additional context for key derivation
            
        Returns:
            str: Base64-encoded encrypted data
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Derive encryption key
            encryption_key = self._derive_encryption_key(user_id, additional_context)
            
            # Create Fernet cipher
            fernet = Fernet(encryption_key)
            
            # Encrypt data
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            
            # Return base64-encoded result
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt sensitive data: {e}")
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    async def decrypt_sensitive_data(
        self, 
        encrypted_data: str, 
        user_id: Optional[UUID] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Decrypt sensitive data using symmetric encryption.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            user_id: Optional user ID for key derivation
            additional_context: Optional additional context for key derivation
            
        Returns:
            str: Decrypted data
            
        Raises:
            DecryptionError: If decryption fails
        """
        try:
            # Derive encryption key
            encryption_key = self._derive_encryption_key(user_id, additional_context)
            
            # Create Fernet cipher
            fernet = Fernet(encryption_key)
            
            # Decode base64 data
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt data
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt sensitive data: {e}")
            raise DecryptionError(f"Decryption failed: {str(e)}")
    
    # ========================================================================
    # AES Encryption (for high-performance encryption)
    # ========================================================================
    
    async def encrypt_with_aes(
        self, 
        data: bytes, 
        key: Optional[bytes] = None
    ) -> Dict[str, str]:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            data: Data to encrypt
            key: Optional encryption key (generates random if not provided)
            
        Returns:
            Dict[str, str]: Encrypted data with IV and tag
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Generate key if not provided
            if key is None:
                key = os.urandom(32)  # 256-bit key
            
            # Generate random IV
            iv = os.urandom(12)  # 96-bit IV for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=self._backend
            )
            
            # Encrypt data
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            return {
                "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
                "iv": base64.b64encode(iv).decode('utf-8'),
                "tag": base64.b64encode(encryptor.tag).decode('utf-8'),
                "key": base64.b64encode(key).decode('utf-8')
            }
            
        except Exception as e:
            self.logger.error(f"AES encryption failed: {e}")
            raise EncryptionError(f"AES encryption failed: {str(e)}")
    
    async def decrypt_with_aes(
        self, 
        encrypted_data: Dict[str, str]
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM.
        
        Args:
            encrypted_data: Dictionary with ciphertext, IV, tag, and key
            
        Returns:
            bytes: Decrypted data
            
        Raises:
            DecryptionError: If decryption fails
        """
        try:
            # Decode components
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            iv = base64.b64decode(encrypted_data['iv'])
            tag = base64.b64decode(encrypted_data['tag'])
            key = base64.b64decode(encrypted_data['key'])
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self._backend
            )
            
            # Decrypt data
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"AES decryption failed: {e}")
            raise DecryptionError(f"AES decryption failed: {str(e)}")
    
    # ========================================================================
    # RSA Encryption (for asymmetric encryption)
    # ========================================================================
    
    def generate_rsa_keypair(self, key_size: int = 2048) -> Dict[str, str]:
        """
        Generate RSA key pair.
        
        Args:
            key_size: RSA key size in bits
            
        Returns:
            Dict[str, str]: Private and public keys in PEM format
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=self._backend
            )
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return {
                "private_key": private_pem.decode('utf-8'),
                "public_key": public_pem.decode('utf-8')
            }
            
        except Exception as e:
            self.logger.error(f"RSA key generation failed: {e}")
            raise EncryptionError(f"RSA key generation failed: {str(e)}")
    
    async def encrypt_with_rsa(
        self, 
        data: bytes, 
        public_key_pem: str
    ) -> str:
        """
        Encrypt data using RSA public key.
        
        Args:
            data: Data to encrypt
            public_key_pem: Public key in PEM format
            
        Returns:
            str: Base64-encoded encrypted data
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=self._backend
            )
            
            # Encrypt data
            ciphertext = public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return base64.b64encode(ciphertext).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"RSA encryption failed: {e}")
            raise EncryptionError(f"RSA encryption failed: {str(e)}")
    
    async def decrypt_with_rsa(
        self, 
        encrypted_data: str, 
        private_key_pem: str
    ) -> bytes:
        """
        Decrypt data using RSA private key.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            private_key_pem: Private key in PEM format
            
        Returns:
            bytes: Decrypted data
            
        Raises:
            DecryptionError: If decryption fails
        """
        try:
            # Load private key
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=self._backend
            )
            
            # Decode encrypted data
            ciphertext = base64.b64decode(encrypted_data)
            
            # Decrypt data
            plaintext = private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"RSA decryption failed: {e}")
            raise DecryptionError(f"RSA decryption failed: {str(e)}")
    
    # ========================================================================
    # Hashing and Key Derivation
    # ========================================================================
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
        """
        Hash password using PBKDF2.
        
        Args:
            password: Password to hash
            salt: Optional salt (generates random if not provided)
            
        Returns:
            Dict[str, str]: Hash and salt in base64 format
        """
        try:
            # Generate salt if not provided
            if salt is None:
                salt = os.urandom(32)
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=self._backend
            )
            
            key = kdf.derive(password.encode('utf-8'))
            
            return {
                "hash": base64.b64encode(key).decode('utf-8'),
                "salt": base64.b64encode(salt).decode('utf-8')
            }
            
        except Exception as e:
            self.logger.error(f"Password hashing failed: {e}")
            raise EncryptionError(f"Password hashing failed: {str(e)}")
    
    def verify_password(
        self, 
        password: str, 
        stored_hash: str, 
        stored_salt: str
    ) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Password to verify
            stored_hash: Stored password hash
            stored_salt: Stored salt
            
        Returns:
            bool: True if password is correct
        """
        try:
            # Decode stored values
            salt = base64.b64decode(stored_salt)
            expected_hash = base64.b64decode(stored_hash)
            
            # Derive key from provided password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=self._backend
            )
            
            # Verify password
            try:
                kdf.verify(password.encode('utf-8'), expected_hash)
                return True
            except Exception:
                return False
                
        except Exception as e:
            self.logger.error(f"Password verification failed: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate cryptographically secure random token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            str: Base64-encoded secure token
        """
        try:
            token = os.urandom(length)
            return base64.urlsafe_b64encode(token).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Token generation failed: {e}")
            raise EncryptionError(f"Token generation failed: {str(e)}")
    
    def hash_data(self, data: Union[str, bytes], algorithm: str = "sha256") -> str:
        """
        Hash data using specified algorithm.
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm (sha256, sha512, etc.)
            
        Returns:
            str: Hexadecimal hash
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            if algorithm == "sha256":
                hash_obj = hashlib.sha256(data)
            elif algorithm == "sha512":
                hash_obj = hashlib.sha512(data)
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1(data)
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Data hashing failed: {e}")
            raise EncryptionError(f"Data hashing failed: {str(e)}")
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key."""
        try:
            # Try to get key from environment
            env_key = settings.security.encryption_key
            if env_key:
                return base64.b64decode(env_key)
            
            # Generate new key if not in environment
            master_key = Fernet.generate_key()
            
            # In production, this should be stored securely
            if not settings.app.is_production:
                self.logger.warning(
                    "Using generated master key. In production, set ENCRYPTION_KEY environment variable."
                )
            
            return master_key
            
        except Exception as e:
            self.logger.error(f"Master key initialization failed: {e}")
            raise EncryptionError(f"Master key initialization failed: {str(e)}")
    
    def _derive_encryption_key(
        self, 
        user_id: Optional[UUID] = None,
        additional_context: Optional[str] = None
    ) -> bytes:
        """Derive encryption key from master key and context."""
        try:
            # Create context string
            context_parts = [str(self._master_key)]
            
            if user_id:
                context_parts.append(str(user_id))
            
            if additional_context:
                context_parts.append(additional_context)
            
            context = "|".join(context_parts)
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"imanipay_encryption_salt",  # Fixed salt for deterministic keys
                iterations=100000,
                backend=self._backend
            )
            
            derived_key = kdf.derive(context.encode('utf-8'))
            
            # Return Fernet-compatible key
            return base64.urlsafe_b64encode(derived_key)
            
        except Exception as e:
            self.logger.error(f"Key derivation failed: {e}")
            raise KeyDerivationError(f"Key derivation failed: {str(e)}")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def encrypt_json(self, data: Dict[str, Any], user_id: Optional[UUID] = None) -> str:
        """
        Encrypt JSON data.
        
        Args:
            data: Dictionary to encrypt
            user_id: Optional user ID for key derivation
            
        Returns:
            str: Encrypted JSON string
        """
        import json
        json_str = json.dumps(data, sort_keys=True)
        return self.encrypt_sensitive_data(json_str, user_id)
    
    def decrypt_json(self, encrypted_data: str, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Decrypt JSON data.
        
        Args:
            encrypted_data: Encrypted JSON string
            user_id: Optional user ID for key derivation
            
        Returns:
            Dict[str, Any]: Decrypted dictionary
        """
        import json
        json_str = self.decrypt_sensitive_data(encrypted_data, user_id)
        return json.loads(json_str)
    
    def secure_compare(self, a: str, b: str) -> bool:
        """
        Perform timing-safe string comparison.
        
        Args:
            a: First string
            b: Second string
            
        Returns:
            bool: True if strings are equal
        """
        import hmac
        return hmac.compare_digest(a, b)

