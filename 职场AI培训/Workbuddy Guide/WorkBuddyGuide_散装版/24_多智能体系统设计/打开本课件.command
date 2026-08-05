#!/bin/zsh
cd "$(dirname "$0")"
port=8765
while lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; do
  port=$((port + 1))
done
open "http://127.0.0.1:$port/.routes/24_advanced_multi-agent/"
python3 -m http.server "$port" --bind 127.0.0.1 --directory "$PWD"
