#!/bin/bash
# Muxed A/V that satisfies Chromium MSE: 25 fps video, video track delayed 5 ms so that ffmpeg's
# Opus CodecDelay compensation never puts an audio block before an earlier-timestamped video block.
W=$1; cd $W/src2; F="/opt/homebrew/bin/ffmpeg -hide_banner -v error -y"
VP9="-c:v libvpx-vp9 -b:v 300k -g 50 -keyint_min 50 -deadline realtime -cpu-used 8"
$F -f lavfi -i testsrc2=size=320x240:rate=25:duration=10 $VP9 _v.webm
$F -f lavfi -i sine=frequency=440:sample_rate=48000:duration=10 -c:a libopus -b:a 64k _a1.webm
$F -f lavfi -i sine=frequency=880:sample_rate=48000:duration=10 -c:a libopus -b:a 64k _a2.webm
$F -itsoffset 0.005 -i _v.webm -i _a1.webm -map 0:v -map 1:a -c copy ffx_vp9_opus.webm
$F -itsoffset 0.005 -i _v.webm -i _a1.webm -map 0:v -map 1:a -c copy -reserve_index_space 1024 ffx_vp9_opus_cf.webm
$F -itsoffset 0.005 -i _v.webm -i _a1.webm -i _a2.webm -i subs.vtt -map 0:v -map 1:a -map 2:a -map 3:s -c:v copy -c:a copy -c:s webvtt ffx_multi.webm
$F -itsoffset 0.005 -i _v.webm -i _a1.webm -i _a2.webm -map 0:v -map 1:a -map 2:a -c copy ffx_2audio.webm
$W/dl/MKVToolNix.app/Contents/MacOS/mkvmerge -q --webm -o mm_vp9_opus.webm ffx_vp9_opus.webm
$F -i mr_vp9_opus.webm -c copy mr_vp9_opusR.webm
# long 1080p 120 s
$F -f lavfi -i testsrc2=size=1920x1080:rate=25:duration=120 -c:v libvpx-vp9 -b:v 2500k -g 50 -keyint_min 50 -deadline realtime -cpu-used 8 -row-mt 1 -threads 8 _vl.webm
$F -f lavfi -i sine=frequency=440:sample_rate=48000:duration=120 -c:a libopus -b:a 96k _al.webm
$F -itsoffset 0.005 -i _vl.webm -i _al.webm -map 0:v -map 1:a -c copy long1080_vp9_opus.webm
rm -f _v.webm _a1.webm _a2.webm _vl.webm _al.webm
ls -la
