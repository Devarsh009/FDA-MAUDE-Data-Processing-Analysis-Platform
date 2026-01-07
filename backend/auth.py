"""
Authentication module for MAUDE Data Processor.
Handles user management, login, registration, and password recovery.
"""
import os
import json
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# User data storage (JSON file for simplicity)
USERS_FILE = os.path.join("data", "users.json")
RESET_TOKENS_FILE = os.path.join("data", "reset_tokens.json")

# Ensure data directory exists
os.makedirs("data", exist_ok=True)


class User(UserMixin):
    """User class for Flask-Login."""
    
    def __init__(self, user_id: str, email: str, password_hash: str, name: str = ""):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.name = name
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches the stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class AuthManager:
    """Manages user authentication and password recovery."""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.serializer = URLSafeTimedSerializer(secret_key)
        self._ensure_users_file()
        self._ensure_tokens_file()
    
    def _ensure_users_file(self):
        """Ensure users.json exists."""
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w') as f:
                json.dump({}, f)
    
    def _ensure_tokens_file(self):
        """Ensure reset_tokens.json exists."""
        if not os.path.exists(RESET_TOKENS_FILE):
            with open(RESET_TOKENS_FILE, 'w') as f:
                json.dump({}, f)
    
    def _load_users(self) -> Dict:
        """Load users from JSON file."""
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_users(self, users: Dict):
        """Save users to JSON file."""
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    
    def _load_tokens(self) -> Dict:
        """Load reset tokens from JSON file."""
        try:
            with open(RESET_TOKENS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_tokens(self, tokens: Dict):
        """Save reset tokens to JSON file."""
        with open(RESET_TOKENS_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
    
    def register_user(self, email: str, password: str, name: str = "") -> Tuple[bool, str]:
        """
        Register a new user.
        Returns: (success: bool, message: str)
        """
        users = self._load_users()
        
        # Check if user already exists
        if email.lower() in users:
            return False, "Email already registered"
        
        # Validate email format (basic check)
        if '@' not in email or '.' not in email.split('@')[1]:
            return False, "Invalid email format"
        
        # Validate password strength
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        # Create user
        user_id = email.lower()
        password_hash = User.hash_password(password)
        
        users[user_id] = {
            "email": email.lower(),
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_users(users)
        return True, "Registration successful"
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user.
        Returns: User object if successful, None otherwise.
        """
        users = self._load_users()
        user_id = email.lower()
        
        if user_id not in users:
            return None
        
        user_data = users[user_id]
        user = User(
            user_id=user_id,
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            name=user_data.get('name', '')
        )
        
        if user.check_password(password):
            return user
        
        return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        users = self._load_users()
        
        if user_id not in users:
            return None
        
        user_data = users[user_id]
        return User(
            user_id=user_id,
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            name=user_data.get('name', '')
        )
    
    def generate_reset_token(self, email: str) -> Optional[str]:
        """
        Generate a password reset token for a user.
        Returns: token string if user exists, None otherwise.
        """
        users = self._load_users()
        user_id = email.lower()
        
        if user_id not in users:
            return None
        
        # Generate token
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(seconds=3600)).isoformat()
        
        tokens = self._load_tokens()
        tokens[token] = {
            "email": user_id,
            "expires_at": expires_at,
            "used": False
        }
        self._save_tokens(tokens)
        
        return token
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """
        Verify a password reset token.
        Returns: email if token is valid, None otherwise.
        """
        tokens = self._load_tokens()
        
        if token not in tokens:
            return None
        
        token_data = tokens[token]
        
        # Check if already used
        if token_data.get('used', False):
            return None
        
        # Check if expired
        expires_at = datetime.fromisoformat(token_data['expires_at'])
        if datetime.now() > expires_at:
            return None
        
        return token_data['email']
    
    def reset_password(self, token: str, new_password: str) -> Tuple[bool, str]:
        """
        Reset password using a token.
        Returns: (success: bool, message: str)
        """
        email = self.verify_reset_token(token)
        if not email:
            return False, "Invalid or expired token"
        
        # Validate password strength
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters long"
        
        # Update password
        users = self._load_users()
        if email not in users:
            return False, "User not found"
        
        users[email]['password_hash'] = User.hash_password(new_password)
        self._save_users(users)
        
        # Mark token as used
        tokens = self._load_tokens()
        if token in tokens:
            tokens[token]['used'] = True
            self._save_tokens(tokens)
        
        return True, "Password reset successful"
    
    def user_exists(self, email: str) -> bool:
        """Check if a user exists."""
        users = self._load_users()
        return email.lower() in users
