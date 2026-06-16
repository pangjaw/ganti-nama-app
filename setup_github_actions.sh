#!/bin/bash
export PATH="$PATH:/c/Program Files/nodejs:/c/Users/SINTEL 1.21 BOO/AppData/Roaming/npm"
export GCLOUD="/c/Users/SINTEL 1.21 BOO/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud"
export FIREBASE_TOKEN=$(firebase login:ci --non-interactive || echo "")
echo "Token Firebase CI: $FIREBASE_TOKEN"

echo "Memulai inisiasi otomatis Firebase ke Github..."
firebase init hosting:github --project ganti-nama-file
