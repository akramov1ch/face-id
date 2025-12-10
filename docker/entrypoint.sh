#!/bin/sh

echo "PostgreSQL ishga tushishini kutyapman..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL ishga tushdi!"

# Migratsiyalarni bajarish (agar kerak bo'lsa)
# alembic upgrade head

echo "Dastur ishga tushmoqda..."
exec "$@"