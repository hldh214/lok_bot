#!/usr/bin/env sh

set -e

DATA_FOLDER=/app/data
OUTPUT_LOG_FILE=$DATA_FOLDER/output.log

# if the output log file exists, backup it with timestamp suffix
if [ -f "$OUTPUT_LOG_FILE" ]; then
  mv $OUTPUT_LOG_FILE $OUTPUT_LOG_FILE.$(date +%Y%m%d%H%M%S)
else
  mkdir -p $DATA_FOLDER
  touch $OUTPUT_LOG_FILE
fi

exec "$@"
