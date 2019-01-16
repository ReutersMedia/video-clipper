import logging
import os
import subprocess
import re
import urllib.parse
import sys
import datetime
import random
import urllib.request

from flask import Flask, Response
from flask_api import status

app = Flask(__name__)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

FFMPEG_KEYFRAME_CMD = "/usr/bin/ffmpeg -loglevel panic -ss {0} -i {1} -c:v copy -c:a copy -f mp4 -movflags frag_keyframe+empty_moov -to {2} -copyts pipe:1 > {3}"

FFMPEG_FRAMEACC_CMD = "/usr/bin/ffmpeg -loglevel panic -ss {0} -i {1} -c:v libx264 -crf 18 -c:a aac -b:a 128k -f mp4 -movflags frag_keyframe+empty_moov -t {2} pipe:1 > {3}"


def sec_to_tdelta(sec):
    if ':' in sec:
        rem,s = sec.rsplit(':',1)
        if ':' in rem:
            h,m = rem.rsplit(':',1)
        else:
            h = 0
            m = rem
        return datetime.timedelta(seconds=float(s)+int(m)*60+int(h)*3600)
    return datetime.timedelta(seconds=float(sec))

def generate_clip(key, t_start, t_stop, frame_accurate):
    LOGGER.info("clipping {0}, frame_accurate={1}".format(key,frame_accurate))
    parsed_key = urllib.parse.unquote(key)
    source_fname = os.path.join(os.getenv('S3_MOUNT_POINT'),parsed_key)
    tmp_fname = os.path.join('/tmp',urllib.parse.quote_plus(key)+'-'+str(random.randint(0,1000000000)))
    t_start = sec_to_tdelta(t_start)
    t_stop = sec_to_tdelta(t_stop)
    if frame_accurate:
        cmd = FFMPEG_FRAMEACC_CMD.format(t_start,
                                         source_fname,
                                         t_stop-t_start,  # uses duration, not stop time
                                         tmp_fname)
    else:
        cmd = FFMPEG_KEYFRAME_CMD.format(t_start,
                                         source_fname,
                                         t_stop,
                                         tmp_fname)
    try:
        os.mkfifo(tmp_fname)
        p = subprocess.Popen(cmd,shell=True)
        LOGGER.info("Executing command: {0}".format(cmd))
        # read from pipe and return
        bytes_total = 0
        with open(tmp_fname,'rb') as f:
            while True:
                d = f.read(100000)
                if len(d) == 0:
                    LOGGER.info("Reached end of file")
                    break
                bytes_total += len(d)
                yield d
        LOGGER.info("Finished generating response, {0} bytes written".format(bytes_total))
        p.wait()
        rc = p.returncode
        LOGGER.info("ffmpeg return code: {0}".format(rc))
    except:
        LOGGER.exception("Error processing video {0}".format(key))
    finally:
        os.unlink(tmp_fname)


@app.route('/clip/frameaccurate/<string:start_sec>/<string:stop_sec>/<path:signed_url>',
           methods=['GET'])
def clip_frame_accurate(signed_url=None, start_sec=None, stop_sec=None):
    return clip(signed_url=signed_url, start_sec=start_sec, stop_sec=stop_sec, frame_accurate=True)

        
@app.route('/clip/keyframe/<string:start_sec>/<string:stop_sec>/<path:signed_url>',
           methods=['GET'])
def clip_keyframe(signed_url=None, start_sec=None, stop_sec=None):
    return clip(signed_url=signed_url, start_sec=start_sec, stop_sec=stop_sec, frame_accurate=False)


def clip(signed_url=None, start_sec=None, stop_sec=None, frame_accurate=False):
    LOGGER.info("Request received, start={0}, stop={1}, signed_url={2}".format(start_sec,stop_sec,signed_url))
    if '://' not in signed_url:
        # fix some weirdness with how uwsgi passes this parameter
        if ':/' in signed_url:
            signed_url = signed_url.replace(':/','://',1)
    parsed_url = urllib.parse.urlsplit(signed_url)
    netloc = parsed_url.netloc.lower()
    # same bucket?
    source_bucket = os.getenv('SOURCE_BUCKET').lower()
    m = re.match('(.*)\.s3\.amazonaws\.com$',netloc)
    if m and m.groups()[0] == source_bucket:
        # check permission
        r = urllib.request.urlopen(signed_url)
        LOGGER.info("GET request status code: {0}".format(r.status))
        if r.status == 200:
            path = urllib.parse.unquote(parsed_url.path)
            if path.startswith('/'):
                path = path[1:]
            gen = generate_clip(path,start_sec,stop_sec,frame_accurate)
            return Response(gen,mimetype="video/mp4")
        else:
            LOGGER.info("HEAD request failed")
            return 'error: object not found', status.HTTP_404_NOT_FOUND
    else:
        LOGGER.info("Invalid domain {0}, doesn't match configured source {1}".format(netloc,source_bucket))
        return 'invalid domain, does not match configured domain', status.HTTP_403_FORBIDDEN
    
        
if __name__=="__main__":
    logging.basicConfig(stream=sys.stdout,level=logging.INFO)
    LOGGER.info("starting server")
    app.run(debug=False,host='0.0.0.0',port=80)
