set -e
if command -v docker-compose >/dev/null 2>&1; then dc="docker-compose"; else dc="docker compose"; fi
cd ..
git pull
$dc build web
$dc up -d web
echo "run django migrations"
$dc exec -T web python manage.py migrate
echo "collect static"
$dc exec -T web python manage.py collectstatic --noinput
