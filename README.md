
# video-clipper

Provides a web service that clips videos stored on S3.

## Use

* `/clip/frameaccurate/<START>/<END>/<SIGNED_URL>` -- create a frame-accurate clip given the START and END time codes.  This involves transcoding the video, and may result in some quality loss.  It also takes longer.
* `/clip/keyframe/<START>/<END>/<SIGNED_URL>` -- clip the video at the key frame closest to or before the START time code, to the end time code.  The video and audio are copied without re-encoding.  This is faster, and preserves the original video quality.  For WNE videos, key frames are about every 0.5 sec, so this should be preferred.

The START and END time codes can be expressed as either seconds from the start, with millisecond precision (e.g. 25.912).  Or it can be expressed in hours, minutes, and seconds (e.g. 00:01:05.293).

The SIGNED_URL should be an s3 pre-signed URL for the object.  The application has full access to the bucket, but access will not be provided to the caller unless they can demonstrate access to the requested source video, via a signed URL.  Before providing the video, the application will check that the signed URL is valid, but access the video through the goofys mount, since this does not require streaming all of the original video and allows ffmpeg to seek efficiently within the file.  The SIGNED_URL will be parsed to check the domain against the authorized DOMAIN_LIST.  The domain for the SIGNED_URL, and for any final redirect for the url, need to be on the domain whitelist.  Otherwise the server can be used to make arbitrary requests to third party domains.  


## Configuration

The application uses Goofys to mount an S3 file system.  You need to provide a SOURCE_BUCKET environment parameter, and the container will need credentials that allow mounting the bucket.  The SIGNED_URL will be checked to ensure it matches the SOURCE_BUCKET.  Because the container uses a FUSE mount, you will need to add mknod and sys_admin capabilities and add a device mapping for /dev/fuse.  For example:

```
version: '2'
services:
  fileproc:
    mem_limit: 1024M
    image: vidclipper:dev
    ports:
      - "8581:80"
    environment:
      - SOURCE_BUCKET=my_bucket
      - DOMAIN_LIST=mydomain1,mydomain2
    cap_add:
      - mknod
      - sys_admin
    devices:
      - /dev/fuse
```
