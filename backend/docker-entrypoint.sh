#!/bin/sh
set -eu

# Inicialização automática apenas do servidor de desenvolvimento.
# Outros comandos (test, check, shell etc.) são executados sem carregar dados.
if [ "${1:-}" = "python" ] && [ "${2:-}" = "manage.py" ] && [ "${3:-}" = "runserver" ]; then
    python manage.py migrate --noinput
    python manage.py seed
fi

exec "$@"
