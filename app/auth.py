import bcrypt


def hash_password(password: str) -> str:
    """Хеширует пароль для безопасного хранения."""
    # Генерация соль+хеш
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    # Возвращаем строку для записи в базу данных
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, совпадает ли захешированный пароль с исходным."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
