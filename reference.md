
## ProRes-444_OriRes_25_UHQ
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 1.4992459 -filter_complex scale=w=7952:h=5304,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v prores_ks -pix_fmt yuv444p10le -threads 0 -profile:v 4 -q:v 5 -an -metadata creation_time="2020-08-11T14:54:41" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_3619160922468951329.mov


## H265-444_4K_25_UHQ.mov
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_01/LRT_%05d.jpg -aspect 1.497076 -filter_complex scale=w=4096:h=2736,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=8 -an -metadata creation_time="2020-08-10T12:47:22" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 20200809_01_H265-444_4K_25_UHQ.mov


## H265-444_4K_25_.mov
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 3:2 -filter_complex scale=w=3840:h=2560,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=8 -an -metadata creation_time="2020-08-11T15:49:50" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_3244195673715032054.mov


## H265-444_1080p_25_UHQ
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 3:2 -filter_complex scale=w=1920:h=1280,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=8 -an -metadata creation_time="2020-08-12T01:20:08" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_6015015324474100745.mov


## H265-420_1080p_25_LQ
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -i /Users/nut/Pictures/Resource/preset/LRT_20200809_02/LRT_%05d.jpg -aspect 3:2 -filter_complex scale=w=1920:h=1280,setsar=sar=1/1,unsharp=luma_msize_x=7:luma_msize_y=7:luma_amount=0.4 -c:v libx265 -pix_fmt yuv420p10le -threads 0 -tag:v hvc1 -x265-params crf=22 -an -metadata creation_time="2020-08-12T00:20:51" -color_primaries 9 -colorspace 9 -color_range 2 -color_trc 14 -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_1698314705367251662.mov




## preview
ffmpeg -y -r 25 -analyzeduration 2147483647 -probesize 2147483647 -safe 0 -f concat -i /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/lrt_5428120666686487090/ccdemux4c002ebe4062.txt -aspect 3:2 -filter_complex scale=w=1024:h=680,setsar=sar=1/1 -c:v libx264 -pix_fmt yuvj420p -threads 0 -profile:v high -preset slow -crf 15 -an -metadata creation_time="2020-08-10T19:48:26" -r 25 /var/folders/wt/18htw47j3lg6mzk6s5gdbfhw0000gn/T/LRT_Render_8067025049657372312.mp4
