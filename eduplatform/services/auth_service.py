import logging
import secrets
from typing import Optional, Dict, Any, Type, Union
from datetime import datetime, timedelta
import jwt
from ..models.user import User, UserRole
from ..models.student import Student
from ..models.teacher import Teacher
from ..models.parent import Parent
from ..models.admin import Admin
from ..repositories.user_repository import UserRepository
from ..repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication and user management."""
    
    def __init__(self, 
                 user_repository: UserRepository,
                 notification_repository: NotificationRepository,
                 jwt_secret: str,
                 jwt_expire_hours: int = 24):
        """Initialize the auth service with required repositories and configuration."""
        self.user_repo = user_repository
        self.notification_repo = notification_repository
        self.jwt_secret = jwt_secret
        self.jwt_expire_hours = jwt_expire_hours
    
    import logging
import secrets
from typing import Optional, Dict, Any, Type, Union
from datetime import datetime, timedelta
import jwt
...

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, user_repository, notification_repository, jwt_secret, jwt_expire_hours=24):
        ...
        self._reset_tokens: Dict[str, Dict[str, Any]] = {}   # used by fix #2 below

    def register_user(self, user_type, full_name, email, password, **kwargs):
        logger.info("Registering new %s (email=%s)", user_type.__name__, email)

        if self.user_repo.email_exists(email):
            raise ValueError("Email already registered")

        user = self._create_user_instance(user_type, full_name, email, password, kwargs)
        self._apply_optional_profile_fields(user, kwargs)

        self.user_repo.add(user)
        logger.info("User %s persisted successfully", user._id)

        self._send_welcome_notification(user, full_name)

        token = self._generate_token(user)
        return {'user': user, 'token': token, 'user_type': self.user_repo.get_user_type(user)}

    def _create_user_instance(self, user_type, full_name, email, password, kwargs):
        """Instantiate the correct User subclass for the requested user_type."""
        if user_type == Student:
            if 'grade' not in kwargs:
                raise ValueError("Grade is required for student registration")
            return Student(full_name, email, password, kwargs['grade'])
        if user_type == Teacher:
            return Teacher(full_name, email, password)
        if user_type == Parent:
            return Parent(full_name, email, password)
        if user_type == Admin:
            return Admin(full_name, email, password)
        raise ValueError(f"Invalid user type: {user_type.__name__}")

    def _apply_optional_profile_fields(self, user, kwargs):
        """Copy optional profile fields (phone, address) onto a newly created user."""
        if 'phone' in kwargs:
            user._phone = kwargs['phone']
        if 'address' in kwargs:
            user._address = kwargs['address']

    def _send_welcome_notification(self, user, full_name):
        """Best-effort welcome notification: failure here must not undo registration."""
        welcome_message = f"Welcome to EduPlatform, {full_name}! Your account has been successfully created."
        try:
            self.notification_repo.create_notification(
                recipient_id=user._id, title="Welcome to EduPlatform",
                message=welcome_message, notification_type="system"
            )
        except Exception:
            logger.exception("Failed to send welcome notification to user %s", user._id)

    def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user and return user data with auth token.
        
        Args:
            email: User's email
            password: User's password
            
        Returns:
            Dictionary with user data and token if authentication succeeds, None otherwise
        """
        user = self.user_repo.authenticate(email, password)
        if not user:
            return None
            
        # Generate auth token
        token = self._generate_token(user)
        
        return {
            'user': user,
            'token': token,
            'user_type': self.user_repo.get_user_type(user)
        }
    
    PASSWORD_RESET_TOKEN_TTL = timedelta(hours=1)   # module-level constant

    def reset_password_request(self, email: str) -> bool:
      user = self.user_repo.get_by_email(email)
      if user:
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + PASSWORD_RESET_TOKEN_TTL
        self._reset_tokens[reset_token] = {'email': email, 'expires_at': expires_at}

        reset_url = f"https://eduplatform.example.com/reset-password?token={reset_token}"
        self.notification_repo.create_notification(
            recipient_id=email, title="Password Reset Request",
            message=f"Click the following link to reset your password: {reset_url}",
            notification_type="system",
            metadata={'expires_at': expires_at.isoformat()}
        )
    return True

    def reset_password(self, token: str, new_password: str) -> bool:
      token_data = self._reset_tokens.get(token)
      if not token_data or datetime.now() > token_data['expires_at']:
        self._reset_tokens.pop(token, None)
        return False

      user = self.user_repo.get_by_email(token_data['email'])
      del self._reset_tokens[token]     # single-use, regardless of outcome
      if not user:
        return False

      user_email = token_data['email']
      user._password_hash, user._salt = user._hash_password(new_password)
      self.user_repo.update(user)
    
      # Notify user of password change
      self.notification_repo.create_notification(
        recipient_id=user_email,
        title="Password Changed",
        message="Your password has been successfully changed. If you didn't make this change, please contact support immediately.",
        notification_type="security"
      )
        
      return True

    def _generate_token(self, user: User) -> str:
        """Generate a JWT token for the user."""
        payload = {
            'user_id': user._email,  # Using email as user ID
            'role': user._role.value if hasattr(user, '_role') else 'user',
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expire_hours)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return the decoded payload if valid."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_current_user(self, token: str) -> Optional[User]:
        """Get the current user from a JWT token."""
        payload = self.verify_token(token)
        if not payload:
            return None
            
        return self.user_repo.get_by_email(payload['user_id'])
    
    def update_profile(self, 
                     user: User, 
                     full_name: Optional[str] = None,
                     email: Optional[str] = None,
                     phone: Optional[str] = None,
                     address: Optional[str] = None) -> User:
        """Update a user's profile information.
        
        Args:
            user: The user to update
            full_name: New full name (if provided)
            email: New email (if provided)
            phone: New phone number (if provided)
            address: New address (if provided)
            
        Returns:
            The updated user object
            
        Raises:
            ValueError: If email is already taken by another user
        """
        if email and email != user._email and self.user_repo.email_exists(email):
            raise ValueError("Email already in use by another account")
            
        if full_name:
            user._full_name = full_name
        if email:
            user._email = email
        if phone is not None:
            user._phone = phone
        if address is not None:
            user._address = address
            
        self.user_repo.update(user)
        
        # Log the profile update
        self.notification_repo.create_notification(
            recipient_id=user._email,
            title="Profile Updated",
            message="Your profile information has been updated successfully.",
            notification_type="account"
        )
        
        return user
