#!/bin/bash -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

SAVE_DIR="$1"

COPY_DELIVERY_PHOTOS_TO="$2"
SCRIPT_TO_RUN_ON_COPIED_PHOTOS_DIR="$3"

if [ ! -d "$SAVE_DIR" ]; then
    echo "Invalid save dir argument!" >&2
    exit 1
fi

if [ -n "$COPY_DELIVERY_PHOTOS_TO" ] && [ ! -d "$COPY_DELIVERY_PHOTOS_TO" ]; then
    echo "Invalid copy dir argument!" >&2
    exit 1
fi

shift
shift
shift

python "$SCRIPT_DIR"/main.py --file "$SAVE_DIR"/instacart_orders.json
python "$SCRIPT_DIR"/analyze.py "$SAVE_DIR"/instacart_orders.json "$@"
node "$SCRIPT_DIR"/downloadImages.js "$SAVE_DIR"/instacart_orders.json

if [ -n "$COPY_DELIVERY_PHOTOS_TO" ]; then
    TEMP_DIR="$(mktemp -d)"
    trap "rm -r '$TEMP_DIR'" exit
    rsync -r "$SAVE_DIR"/delivery_photos/ "$TEMP_DIR"/
    if [ -n "$SCRIPT_TO_RUN_ON_COPIED_PHOTOS_DIR" ]; then
        COMMAND="$SCRIPT_TO_RUN_ON_COPIED_PHOTOS_DIR \"$TEMP_DIR\""
        eval "$COMMAND"
    fi
    rsync -r "$TEMP_DIR"/ "$COPY_DELIVERY_PHOTOS_TO"/
fi

echo "$(date)" >"$SAVE_DIR"/lastBackedUp.txt
