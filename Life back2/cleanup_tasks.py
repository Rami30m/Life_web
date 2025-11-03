"""
Фоновые задачи для очистки истекших данных SSO

Этот модуль можно запускать как отдельный процесс или через cron
"""

from sqlalchemy.orm import Session
from datetime import datetime
from database import SessionLocal
from models import (
    OAuthAuthorizationCode,
    OAuthDeviceCode,
    OAuthVerificationCode
)

def cleanup_expired_codes(db: Session):
    """
    Очищает истекшие коды из БД
    
    - Удаляет истекшие authorization codes
    - Удаляет истекшие device codes
    - Удаляет истекшие verification codes
    """
    now = datetime.utcnow()
    deleted_count = 0
    
    # 1. Удаляем истекшие authorization codes
    expired_auth_codes = db.query(OAuthAuthorizationCode).filter(
        OAuthAuthorizationCode.expires_at < now
    ).all()
    for code in expired_auth_codes:
        db.delete(code)
        deleted_count += 1
    
    # 2. Удаляем истекшие device codes (только expired статус)
    expired_device_codes = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.expires_at < now,
        OAuthDeviceCode.status == 'expired'
    ).all()
    for code in expired_device_codes:
        db.delete(code)
        deleted_count += 1
    
    # Также помечаем как expired pending коды, которые истекли
    expired_pending_device_codes = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.expires_at < now,
        OAuthDeviceCode.status == 'pending'
    ).all()
    for code in expired_pending_device_codes:
        code.status = 'expired'
        deleted_count += 1
    
    # 3. Удаляем истекшие verification codes
    expired_verification_codes = db.query(OAuthVerificationCode).filter(
        OAuthVerificationCode.expires_at < now
    ).all()
    for code in expired_verification_codes:
        db.delete(code)
        deleted_count += 1
    
    db.commit()
    return deleted_count

def run_cleanup():
    """Запускает очистку истекших кодов"""
    db = SessionLocal()
    try:
        deleted = cleanup_expired_codes(db)
        print(f"✅ Очищено {deleted} истекших кодов")
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Можно запускать как скрипт
    run_cleanup()


