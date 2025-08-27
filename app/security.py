import hashlib
import hmac
import json
import re
from typing import Any, Dict, List, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from datetime import datetime

from .config import settings
from .models import DataSensitivityLevel

class DataEncryption:
    """Handle encryption and decryption of sensitive data"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key from environment"""
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            # Generate a new key if not provided
            key = Fernet.generate_key()
            # In production, this should be stored securely
            print(f"Generated new encryption key: {key.decode()}")
            print("Please store this key securely in your environment variables as ENCRYPTION_KEY")
        else:
            key = key.encode() if isinstance(key, str) else key
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return data
        encrypted_data = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return encrypted_data
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception:
            # Return original data if decryption fails (might not be encrypted)
            return encrypted_data

class DataMasking:
    """Handle masking of sensitive data for display purposes"""
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address"""
        if not email or '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number"""
        if not phone:
            return phone
        
        # Remove non-digit characters
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 4:
            return '*' * len(phone)
        
        # Keep first 3 and last 4 digits, mask the rest
        if len(digits) >= 10:
            return f"{digits[:3]}***{digits[-4:]}"
        else:
            return f"{digits[:2]}***{digits[-2:]}"
    
    @staticmethod
    def mask_ssn(ssn: str) -> str:
        """Mask Social Security Number"""
        if not ssn:
            return ssn
        
        digits = re.sub(r'\D', '', ssn)
        if len(digits) == 9:
            return f"***-**-{digits[-4:]}"
        return '*' * len(ssn)
    
    @staticmethod
    def mask_credit_card(card_number: str) -> str:
        """Mask credit card number"""
        if not card_number:
            return card_number
        
        digits = re.sub(r'\D', '', card_number)
        if len(digits) >= 12:
            return f"****-****-****-{digits[-4:]}"
        return '*' * len(card_number)
    
    @staticmethod
    def mask_bank_account(account: str) -> str:
        """Mask bank account number"""
        if not account:
            return account
        
        if len(account) <= 4:
            return '*' * len(account)
        return f"****{account[-4:]}"
    
    @staticmethod
    def mask_medical_id(medical_id: str) -> str:
        """Mask medical ID number"""
        if not medical_id:
            return medical_id
        
        if len(medical_id) <= 4:
            return '*' * len(medical_id)
        return f"{medical_id[:2]}***{medical_id[-2:]}"
    
    @staticmethod
    def mask_generic_id(id_value: str, show_chars: int = 4) -> str:
        """Generic ID masking"""
        if not id_value or len(id_value) <= show_chars:
            return '*' * len(id_value) if id_value else id_value
        
        return '*' * (len(id_value) - show_chars) + id_value[-show_chars:]

class SensitiveFieldHandler:
    """Handle sensitive fields based on data sensitivity levels"""
    
    # Define sensitive field patterns
    SENSITIVE_PATTERNS = {
        'email': ['email', 'email_address', 'user_email'],
        'phone': ['phone', 'phone_number', 'mobile', 'telephone'],
        'ssn': ['ssn', 'social_security', 'social_security_number'],
        'credit_card': ['credit_card', 'card_number', 'cc_number'],
        'bank_account': ['bank_account', 'account_number', 'routing_number'],
        'medical_id': ['medical_id', 'patient_id', 'mrn', 'medical_record_number'],
        'address': ['address', 'street_address', 'home_address'],
        'name': ['full_name', 'first_name', 'last_name', 'patient_name'],
        'dob': ['date_of_birth', 'birth_date', 'dob'],
        'password': ['password', 'hashed_password', 'pwd']
    }
    
    def __init__(self):
        self.encryptor = DataEncryption()
        self.masker = DataMasking()
    
    def identify_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Identify sensitive fields in data and return their types"""
        sensitive_fields = {}
        
        for field_name, value in data.items():
            if not isinstance(value, str) or not value:
                continue
            
            field_lower = field_name.lower()
            
            for field_type, patterns in self.SENSITIVE_PATTERNS.items():
                if any(pattern in field_lower for pattern in patterns):
                    sensitive_fields[field_name] = field_type
                    break
        
        return sensitive_fields
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any], 
                               sensitivity_level: DataSensitivityLevel = DataSensitivityLevel.CONFIDENTIAL) -> Dict[str, Any]:
        """Encrypt sensitive fields based on sensitivity level"""
        if sensitivity_level in [DataSensitivityLevel.PUBLIC, DataSensitivityLevel.INTERNAL]:
            return data
        
        sensitive_fields = self.identify_sensitive_fields(data)
        encrypted_data = data.copy()
        
        for field_name, field_type in sensitive_fields.items():
            if field_name in encrypted_data and isinstance(encrypted_data[field_name], str):
                if sensitivity_level == DataSensitivityLevel.RESTRICTED:
                    # Encrypt all sensitive fields for restricted data
                    encrypted_data[field_name] = self.encryptor.encrypt(encrypted_data[field_name])
                elif sensitivity_level == DataSensitivityLevel.CONFIDENTIAL:
                    # Encrypt only highly sensitive fields
                    if field_type in ['ssn', 'credit_card', 'bank_account', 'medical_id', 'password']:
                        encrypted_data[field_name] = self.encryptor.encrypt(encrypted_data[field_name])
        
        return encrypted_data
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields"""
        sensitive_fields = self.identify_sensitive_fields(data)
        decrypted_data = data.copy()
        
        for field_name in sensitive_fields.keys():
            if field_name in decrypted_data and isinstance(decrypted_data[field_name], str):
                decrypted_data[field_name] = self.encryptor.decrypt(decrypted_data[field_name])
        
        return decrypted_data
    
    def mask_sensitive_fields(self, data: Dict[str, Any], 
                            user_permissions: List[str] = None) -> Dict[str, Any]:
        """Mask sensitive fields for display"""
        from .models import Permission
        
        # Check if user has permission to view sensitive data
        if user_permissions and Permission.READ_SENSITIVE.value in user_permissions:
            return data
        
        sensitive_fields = self.identify_sensitive_fields(data)
        masked_data = data.copy()
        
        for field_name, field_type in sensitive_fields.items():
            if field_name in masked_data and isinstance(masked_data[field_name], str):
                value = masked_data[field_name]
                
                # Try to decrypt first if it's encrypted
                decrypted_value = self.encryptor.decrypt(value)
                
                # Apply appropriate masking
                if field_type == 'email':
                    masked_data[field_name] = self.masker.mask_email(decrypted_value)
                elif field_type == 'phone':
                    masked_data[field_name] = self.masker.mask_phone(decrypted_value)
                elif field_type == 'ssn':
                    masked_data[field_name] = self.masker.mask_ssn(decrypted_value)
                elif field_type == 'credit_card':
                    masked_data[field_name] = self.masker.mask_credit_card(decrypted_value)
                elif field_type == 'bank_account':
                    masked_data[field_name] = self.masker.mask_bank_account(decrypted_value)
                elif field_type == 'medical_id':
                    masked_data[field_name] = self.masker.mask_medical_id(decrypted_value)
                elif field_type in ['name', 'address']:
                    # Partial masking for names and addresses
                    if len(decrypted_value) > 4:
                        masked_data[field_name] = decrypted_value[:2] + '*' * (len(decrypted_value) - 4) + decrypted_value[-2:]
                    else:
                        masked_data[field_name] = '*' * len(decrypted_value)
                elif field_type == 'password':
                    masked_data[field_name] = '********'
                else:
                    # Generic masking
                    masked_data[field_name] = self.masker.mask_generic_id(decrypted_value)
        
        return masked_data
    
    def sanitize_for_external_api(self, data: Dict[str, Any], 
                                integration_type: str = 'general') -> Dict[str, Any]:
        """Sanitize data for external API consumption"""
        sanitized_data = data.copy()
        
        # Remove internal fields
        internal_fields = ['hashed_password', 'stripe_customer_id', 'stripe_subscription_id']
        for field in internal_fields:
            sanitized_data.pop(field, None)
        
        # Apply specific rules based on integration type
        if integration_type == 'finance':
            # For financial integrations, mask but don't remove financial data
            sensitive_fields = self.identify_sensitive_fields(sanitized_data)
            for field_name, field_type in sensitive_fields.items():
                if field_type in ['credit_card', 'bank_account', 'ssn']:
                    if field_name in sanitized_data:
                        value = sanitized_data[field_name]
                        decrypted_value = self.encryptor.decrypt(value)
                        if field_type == 'credit_card':
                            sanitized_data[field_name] = self.masker.mask_credit_card(decrypted_value)
                        elif field_type == 'bank_account':
                            sanitized_data[field_name] = self.masker.mask_bank_account(decrypted_value)
                        elif field_type == 'ssn':
                            sanitized_data[field_name] = self.masker.mask_ssn(decrypted_value)
        
        elif integration_type == 'medical':
            # For medical integrations, handle PHI carefully
            sensitive_fields = self.identify_sensitive_fields(sanitized_data)
            for field_name, field_type in sensitive_fields.items():
                if field_type in ['medical_id', 'ssn', 'dob']:
                    if field_name in sanitized_data:
                        value = sanitized_data[field_name]
                        decrypted_value = self.encryptor.decrypt(value)
                        if field_type == 'medical_id':
                            sanitized_data[field_name] = self.masker.mask_medical_id(decrypted_value)
                        elif field_type == 'ssn':
                            sanitized_data[field_name] = self.masker.mask_ssn(decrypted_value)
                        elif field_type == 'dob':
                            # For DOB, only show year
                            try:
                                if '-' in decrypted_value:
                                    year = decrypted_value.split('-')[0]
                                    sanitized_data[field_name] = f"{year}-**-**"
                            except:
                                sanitized_data[field_name] = '****-**-**'
        
        return sanitized_data

# Global instance
sensitive_field_handler = SensitiveFieldHandler()

def encrypt_model_data(model_data: Dict[str, Any], 
                      sensitivity_level: DataSensitivityLevel = DataSensitivityLevel.CONFIDENTIAL) -> Dict[str, Any]:
    """Helper function to encrypt model data"""
    return sensitive_field_handler.encrypt_sensitive_fields(model_data, sensitivity_level)

def decrypt_model_data(model_data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to decrypt model data"""
    return sensitive_field_handler.decrypt_sensitive_fields(model_data)

def mask_model_data(model_data: Dict[str, Any], user_permissions: List[str] = None) -> Dict[str, Any]:
    """Helper function to mask model data"""
    return sensitive_field_handler.mask_sensitive_fields(model_data, user_permissions)

def sanitize_for_api(data: Dict[str, Any], integration_type: str = 'general') -> Dict[str, Any]:
    """Sanitize data for external API integration based on integration type"""
    handler = SensitiveFieldHandler()
    sanitized = data.copy()
    
    # Define sensitivity levels for different integration types
    sensitivity_mapping = {
        'financial': DataSensitivityLevel.CONFIDENTIAL,
        'medical': DataSensitivityLevel.RESTRICTED,
        'general': DataSensitivityLevel.INTERNAL,
        'public': DataSensitivityLevel.PUBLIC
    }
    
    sensitivity_level = sensitivity_mapping.get(integration_type, DataSensitivityLevel.INTERNAL)
    
    # Get sensitive fields
    sensitive_fields = handler.identify_sensitive_fields(sanitized)
    
    # Apply field-level sanitization
    for key, field_type in sensitive_fields.items():
        if key in sanitized and isinstance(sanitized[key], str):
            value = sanitized[key]
            
            if integration_type == 'financial':
                # For financial integrations, mask SSN, bank accounts, but keep emails partially visible
                if field_type == 'ssn':
                    sanitized[key] = handler.masker.mask_ssn(value)
                elif field_type == 'bank_account':
                    sanitized[key] = handler.masker.mask_bank_account(value)
                elif field_type == 'email':
                    sanitized[key] = handler.masker.mask_email(value)
                elif field_type == 'phone':
                    sanitized[key] = handler.masker.mask_phone(value)
                else:
                    sanitized[key] = handler.masker.mask_generic_id(value, show_chars=4)
            
            elif integration_type == 'medical':
                # For medical integrations, apply strict masking
                if field_type == 'medical_id':
                    sanitized[key] = handler.masker.mask_medical_id(value)
                elif field_type == 'ssn':
                    sanitized[key] = handler.masker.mask_ssn(value)
                elif field_type == 'email':
                    sanitized[key] = handler.masker.mask_email(value)
                elif field_type == 'phone':
                    sanitized[key] = handler.masker.mask_phone(value)
                else:
                    sanitized[key] = '*' * len(value) if value else value
            
            else:
                # For general integrations, apply standard masking
                if sensitivity_level == DataSensitivityLevel.INTERNAL:
                    sanitized[key] = handler.masker.mask_generic_id(value, show_chars=4)
                elif sensitivity_level in [DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.RESTRICTED]:
                    sanitized[key] = '*' * len(value) if value else value
    
    # Remove highly sensitive fields for external integrations
    sensitive_fields_to_remove = {
        'password', 'password_hash', 'secret_key', 'private_key', 
        'api_secret', 'webhook_secret', 'encryption_key'
    }
    
    for field in sensitive_fields_to_remove:
        if field in sanitized:
            del sanitized[field]
    
    return sanitized

def sanitize_response(data: Dict[str, Any], sensitivity_level: DataSensitivityLevel = DataSensitivityLevel.PUBLIC) -> Dict[str, Any]:
    """Sanitize data for API responses based on sensitivity level"""
    if sensitivity_level == DataSensitivityLevel.PUBLIC:
        return data
    
    sanitized = data.copy()
    handler = SensitiveFieldHandler()
    
    sensitive_fields = handler.identify_sensitive_fields(sanitized)
    
    for key, field_type in sensitive_fields.items():
        if key in sanitized and isinstance(sanitized[key], str):
            value = sanitized[key]
            
            if sensitivity_level == DataSensitivityLevel.INTERNAL:
                # Apply partial masking for internal use
                if field_type == 'email':
                    sanitized[key] = handler.masker.mask_email(value)
                elif field_type == 'phone':
                    sanitized[key] = handler.masker.mask_phone(value)
                else:
                    sanitized[key] = handler.masker.mask_generic_id(value, show_chars=4)
            
            elif sensitivity_level in [DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.RESTRICTED]:
                # Apply full masking for confidential/restricted data
                if field_type == 'ssn':
                    sanitized[key] = handler.masker.mask_ssn(value)
                elif field_type == 'credit_card':
                    sanitized[key] = handler.masker.mask_credit_card(value)
                elif field_type == 'bank_account':
                    sanitized[key] = handler.masker.mask_bank_account(value)
                elif field_type == 'medical_id':
                    sanitized[key] = handler.masker.mask_medical_id(value)
                elif field_type == 'password':
                    sanitized[key] = '********'
                else:
                    sanitized[key] = '*' * len(value) if value else value
    
    return sanitized