#!/bin/bash
cd "$1"; F=/opt/homebrew/bin/ffmpeg; C="-hide_banner -v error -y"
V="-f lavfi -i testsrc2=size=320x240:rate=30:duration=10"; A="-f lavfi -i sine=frequency=440:sample_rate=48000:duration=10"
$F $C $V $A -c:v libvpx-vp9 -b:v 300k -g 60 -keyint_min 60 -deadline realtime -cpu-used 8 -c:a libopus -b:a 64k -shortest vp9_opus.webm
$F $C $V $A -c:v libvpx -b:v 300k -g 60 -keyint_min 60 -deadline realtime -cpu-used 8 -c:a vorbis -strict -2 -ac 2 -shortest vp8_vorbis.webm
$F $C -f lavfi -i "testsrc2=size=320x240:rate=30:duration=10" -vf "format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(lt(X,W/2),0,255*Y/H)'" -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 300k -g 60 -keyint_min 60 -deadline realtime -cpu-used 8 vp9_alpha.webm
$F $C $V $A -c:v libsvtav1 -g 60 -preset 10 -crf 40 -c:a libopus -b:a 64k -shortest av1_opus.webm
$F $C $V $A -c:v libx264 -g 60 -keyint_min 60 -preset veryfast -c:a aac -b:a 96k -shortest h264_aac.mkv
$F $C $A -c:a libopus -b:a 64k opus_only.webm
ls -la
for f in *.webm *.mkv; do echo == $f; /opt/homebrew/bin/ffprobe -v error -show_entries format=duration:stream=codec_name,pix_fmt:stream_tags=alpha_mode -of compact $f; done
