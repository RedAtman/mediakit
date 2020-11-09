
## ProRes-444_OriRes_25_UHQ
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 1.4992459 -filter_complex scale=w=7952:h=5304,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v prores_ks -pix_fmt yuv444p10le -threads 0 -profile:v 4 -q:v 5 -an -metadata creation_time="2020-08-11T14:54:41" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_3619160922468951329.mov


ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/LRT_20200903/LRT_%05d.jpg -aspect 1.4992459 -filter_complex scale=w=7952:h=5304,setsar=sar=1/1 -c:v prores_ks -pix_fmt yuv444p10le -threads 0 -profile:v 4 -q:v 5 -an -metadata creation_time="2020-09-06T19:42:01" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /Volumes/ssd2t/time-lapse/20200903_ProRes.mov


## H265-444_4K_25_LQ.mov
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/LRT_20200903/LRT_%05d.jpg -aspect 1.497076 -filter_complex scale=w=4096:h=2736,setsar=sar=1/1 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=22 -an -metadata creation_time="2020-09-26T08:55:24" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_1613365000285316124.mov
  501 20778  6972   0  8:56AM ttys012    0:00.01 grep --color=auto --exclude-dir=.bzr --exclude-dir=CVS --exclude-dir=.git --exclude-dir=.hg --exclude-dir=.svn --exclude-dir=.idea --exclude-dir=.tox ffmpeg


## H265-444_1080p_25_UHQ
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 3:2 -filter_complex scale=w=1920:h=1280,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=8 -an -metadata creation_time="2020-08-12T01:20:08" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_6015015324474100745.mov


## H265-420_1080p_25_LQ
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 3:2 -filter_complex scale=w=1920:h=1280,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=22 -an -metadata creation_time="2020-08-12T00:20:51" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_1698314705367251662.mov




## preview
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -safe 0 -f concat -i /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/lrt_5428120666686487090/ccdemux4c002ebe4062.txt -aspect 3:2 -filter_complex scale=w=1024:h=680,setsar=sar=1/1 -c:v libx264 -pix_fmt yuvj420p -threads 0 -profile:v high -preset slow -crf 15 -an -metadata creation_time="2020-08-10T19:48:26" -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_8067025049657372312.mp4



## combine: logo & audio
ffmpeg -y \
    -i /Users/nut/Downloads/video/_trim/videoHelper-trim_1.mp4 \
    -i /Users/nut/Downloads/In\ the\ Autumn.m4a \
    -i /Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png \
    -shortest \
    -filter_complex "\
    amix=inputs=2:duration=shortest; \
    [1:a]afade=t=in:st=0:d=0,afade=t=out:st=10:d=0[out1];\
    [2][0]scale2ref=h=ow/mdar:w=iw/7[logo][video];\
    [logo]format=argb,colorchannelmixer=aa=0.3[logotransparent];\
    [video][logotransparent]overlay=(main_w-w)*0.7:(main_h-h)*0.7[videoout] \
    " \
    -map "[videoout]:v" -map "[out1]:a" \
    /Users/nut/Downloads/video/_trim/output.mp4

ffmpeg -y \
    -i /Users/nut/Downloads/video/_trim/videoHelper-trim_1.mp4 \
    -i /Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png \
    -ss 99.5 \
    -to 104.5 \
    -i /Users/nut/Downloads/In\ the\ Autumn.m4a \
    -filter_complex "\
    [0:v]crop=1700:1080,reverse[video_step_one];\
    [1:v][video_step_one]scale2ref=h=ow/mdar:w=iw/7[logo][video];\
    [logo]format=argb,colorchannelmixer=aa=0.3[logo];\
    [video][logo] overlay=(main_w-w)*0.7:(main_h-h)*0.7;\
    [2:a]afade=t=in:st=0:d=1,afade=t=out:st=4:d=1\
    " \
    /Users/nut/Downloads/video/_trim/output.mp4



ffmpeg -y \
    -i /Users/nut/Pictures/Resource/20200809_荇桥_02_H265-420_1080p_25_LQ_voice.mov \
    -i /Users/nut/Dropbox/pic/logo/aQuantum/aQuantum_white.png \
    -ss 99.5 \
    -i /Users/nut/Downloads/In\ the\ Autumn.m4a \
    -filter_complex "\
    [1:v][0:v]scale2ref=h=ow/mdar:w=iw/7[logo][video];\
    [logo]format=argb,colorchannelmixer=aa=0.3[logo];\
    [video][logo] overlay=(main_w-w)*0.7:(main_h-h)*0.7;\
    [0:a]aeval=0:c=same[audio];\
    [2:a]afade=t=in:st=0:d=1,afade=t=out:st=14:d=1,volume=12dB[music];\
    [audio][music]amix=inputs=2:duration=shortest:dropout_transition=2 \
    " \
    /Users/nut/Pictures/Resource/output.mp4



ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -safe 0 -f concat -i /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/lrt_5767642783963316146/ccdemux3ef7f3ddeff6f.txt -aspect 3:2 -filter_complex scale=w=3840:h=2560,setsar=sar=1/1 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=8 -an -metadata creation_time="2020-08-24T22:40:35" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_7970991395103234445.mov