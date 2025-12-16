echo "PostgreSQL ishga tushishini kutyapman..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL ishga tushdi!"

echo "Dastur ishga tushmoqda..."
exec "$@"