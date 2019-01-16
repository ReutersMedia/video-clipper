#!/bin/sh
mkdir -p $S3_MOUNT_POINT

/usr/bin/supervisord -c /supervisord.conf

