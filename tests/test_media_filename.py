import os
import tempfile

from base.media import BaseMedia


def test_short_name_is_untouched():
    assert BaseMedia.fit_filename('video', '-[compress.libx265.slow]_1.mp4') == 'video-[compress.libx265.slow]_1.mp4'


def test_long_name_fits_one_path_component():
    # 真实失败样例的字节宽度: 输入名 250B + 后缀 26B 会让 ffmpeg 以 ENAMETOOLONG 退出
    title = 'I.Break.the.Maid.s.Ass.for.Being.a.Bad.Max.Betancur.and.Salome.Gil.r.n.Anal.r.n.Babe.r.n.Doggy_' * 2
    name = BaseMedia.fit_filename(title, '-[compress.libx265.slow]_1.mp4')
    assert len(name.encode()) <= BaseMedia.NAME_MAX
    assert name.endswith('-[compress.libx265.slow]_1.mp4')
    # 截断必须落在完整的 UTF-8 字符边界上, 多字节字符不能被切成半个
    name.encode().decode('utf-8')


def test_multibyte_title_is_cut_on_char_boundary():
    name = BaseMedia.fit_filename('至' * 100, '-[compress.libx265.slow]_1.mp4')
    assert len(name.encode()) <= BaseMedia.NAME_MAX
    assert name.startswith('至')


def test_create_file_path_stays_within_limit():
    # 端到端: 调用点本身不再产出超长输出路径
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, '至' * 100 + '.mp4')
        new_path = BaseMedia.create_file_path(source, suffix='[compress.libx265.slow]', ext='mp4')
        assert len(os.path.basename(new_path).encode()) <= BaseMedia.NAME_MAX
