from functools import wraps
from flask import session, jsonify
from models import User
from config import Config
import secrets
from datetime import datetime, timedelta

class AuthManager:
    """Authentication and session management"""
    
    @staticmethod
    def login(username, password):
        """
        Authenticate user by username and create session.
        
        Returns:
            dict: User info if successful, None if failed
        """
        user = User.get_by_username(username)
        
        if not user or not User.verify_password(user, password):
            return None
        
        # Create session
        session_token = secrets.token_urlsafe(32)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['token'] = session_token
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True
        
        return {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email'],
            'token': session_token
        }
    
    @staticmethod
    def login_by_email(email, password):
        """
        Authenticate user by email and create session.
        
        Args:
            email: User's email address
            password: User's password
        
        Returns:
            dict: User info if successful, None if failed
        """
        user = User.get_by_email(email)
        
        if not user or not User.verify_password(user, password):
            return None
        
        # Create session
        session_token = secrets.token_urlsafe(32)
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['token'] = session_token
        session['login_time'] = datetime.now().isoformat()
        session.permanent = True
        
        return {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email'],
            'token': session_token
        }
    
    @staticmethod
    def logout():
        """Clear user session"""
        session.clear()
        return True
    
    @staticmethod
    def get_current_user():
        """Get currently logged in user"""
        if 'user_id' not in session:
            return None
        
        # Check session timeout
        if 'login_time' in session:
            login_time = datetime.fromisoformat(session['login_time'])
            if datetime.now() - login_time > timedelta(seconds=Config.SESSION_TIMEOUT):
                AuthManager.logout()
                return None
        
        user = User.get_by_username(session.get('username'))
        if not user:
            AuthManager.logout()
            return None
        
        return {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'email': user['email']
        }
    
    @staticmethod
    def is_authenticated():
        """Check if user is authenticated"""
        return AuthManager.get_current_user() is not None


def login_required(f):
    """
    Decorator to protect routes that require authentication.
    
    Usage:
        @app.route('/api/protected')
        @login_required
        def protected_route():
            return jsonify({'message': 'This is protected'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AuthManager.is_authenticated():
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please login to access this resource'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def get_user_from_session():
    """
    Helper to get current user in routes.
    
    Usage:
        user = get_user_from_session()
        if user:
            print(f"Current user: {user['username']}")
    """
    return AuthManager.get_current_user()