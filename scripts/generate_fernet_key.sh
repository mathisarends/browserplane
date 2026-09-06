#!/usr/bin/env sh

set -eu

if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to generate a Fernet key" >&2
    exit 1
fi

printf 'BACKEND_AUTHENTICATION_STATE_ENCRYPTION_KEY='
openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n'
printf '\n'
