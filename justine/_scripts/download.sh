#!/bin/zsh
# Download one resized (max 1600x1600) copy of every base image via the Jetpack CDN into mirror/img-src/
# Usage: download.sh <mirror_dir>
set -u
M=$1
python3 -I -c "
import json,os,sys
for m in json.load(open('$M/manifest.json')):
    ext=os.path.splitext(m['base'])[1]
    out='$M/img-src/'+os.path.splitext(m['local'])[0][4:]+ext   # strip leading 'img/'
    print(m['download']+'?fit=1600%2C1600&strip=all\t'+out)
" > $M/dl.list
wc -l $M/dl.list
cat $M/dl.list | xargs -P 8 -L 1 sh -c 'u="$0"; o="$1"; [ -s "$o" ] && exit 0; mkdir -p "$(dirname "$o")"; code=$(curl -s -L --retry 3 -o "$o" -w "%{http_code}" "$u"); [ "$code" = 200 ] || { echo "FAIL $code $u"; rm -f "$o"; }'
echo "done: $(find $M/img-src -type f | wc -l) files, $(du -sh $M/img-src | cut -f1)"
