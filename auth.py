"""
JWT認証システム

このモジュールはFastAPIアプリケーション用のJWT認証機能を提供します。
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import User, get_db

# パスワードハッシュ化の設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT設定
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")  # 本番では環境変数から取得
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# HTTPBearerスキーム
security = HTTPBearer()

class AuthManager:
    """認証管理クラス"""
    
    def __init__(self):
        self.pwd_context = pwd_context
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """パスワードを検証する"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """パスワードをハッシュ化する"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """アクセストークンを作成する"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """トークンを検証する"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: int = payload.get("sub")
            if user_id is None:
                return None
            return {"user_id": user_id}
        except JWTError:
            return None
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """IDでユーザーを取得する"""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        """ユーザー名でユーザーを取得する"""
        return db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """メールアドレスでユーザーを取得する"""
        return db.query(User).filter(User.email == email).first()
    
    def create_user(self, db: Session, username: str, email: str, password: str) -> User:
        """新しいユーザーを作成する"""
        try:
            # ユーザー名とメールアドレスの重複チェック
            if self.get_user_by_username(db, username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ユーザー名が既に存在します"
                )
            
            if self.get_user_by_email(db, email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="メールアドレスが既に存在します"
                )
            
            # パスワードをハッシュ化
            hashed_password = self.get_password_hash(password)
            
            # ユーザーを作成
            db_user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_active=True
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
            
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ユーザーの作成に失敗しました"
            )
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """ユーザーを認証する"""
        user = self.get_user_by_username(db, username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

# AuthManagerのインスタンスを作成
auth_manager = AuthManager()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """現在のユーザーを取得する（依存関数）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証に失敗しました",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # トークンを検証
        token_data = auth_manager.verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        
        # ユーザーを取得
        user = auth_manager.get_user_by_id(db, user_id=token_data["user_id"])
        if user is None:
            raise credentials_exception
        
        return user
        
    except Exception:
        raise credentials_exception

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """現在のアクティブユーザーを取得する（依存関数）"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非アクティブなユーザーです"
        )
    return current_user 