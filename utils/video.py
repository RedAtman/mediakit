from enum import Enum


class VideoResolution(Enum):
    """
    视频分辨率枚举类，支持通过尺寸查找分辨率名称，并提供多种比较方式
    包含常见分辨率：QVGA, VGA, SVGA, WSXGA, HD, FHD, UHD_4K
    """

    QVGA = (320, 240)  # Quarter VGA
    VGA = (640, 480)  # Video Graphics Array
    SVGA = (800, 600)  # Super VGA
    XGA = (1024, 768)  # Extended Graphics Array
    WXGA = (1280, 800)  # Wide XGA
    SXGA = (1280, 1024)  # Super XGA
    UXGA = (1600, 1200)  # Ultra XGA
    WSXGA = (1680, 1050)  # Wide Super XGA
    HD = (1280, 720)  # High Definition (720p)
    FHD = (1920, 1080)  # Full HD (1080p)
    WQHD = (2560, 1440)  # Wide Quad HD
    UHD = (3840, 2160)  # Ultra HD (4K)
    DCI_4K = (4096, 2160)  # Digital Cinema Initiatives 4K
    WQUXGA = (3840, 2400)  # Wide Ultra Extended Graphics Array
    # 8K = (7680, 4320)        # 8K Ultra HD

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._pixels = width * height

    @property
    def pixels(self):
        """返回分辨率的总像素数"""
        return self._pixels

    def is_larger_in_dimensions(self, width, height):
        """
        判断当前分辨率是否在两个维度上都大于等于目标尺寸
        :param width: 目标宽度
        :param height: 目标高度
        :return: bool
        """
        return self.width >= width and self.height >= height

    def compare_pixels(self, width, height):
        """
        比较像素总数（面积比较）
        :return: 1（当前更大）0（相等） -1（当前更小）
        """
        other_pixels = width * height
        if self.pixels > other_pixels:
            return 1
        elif self.pixels < other_pixels:
            return -1
        return 0

    @classmethod
    def get_resolution(cls, width, height):
        """
        根据精确尺寸获取对应分辨率
        :return: VideoResolution枚举成员或None
        """
        for resolution in cls:
            if resolution.width == width and resolution.height == height:
                return resolution
        return None

    @classmethod
    def find_closest_resolutions(cls, width, height, by_pixels=True):
        """
        查找所有大于等于当前尺寸的分辨率
        :param by_pixels: True按像素面积比较，False按双维度比较
        :return: 符合条件的枚举成员列表
        """
        if by_pixels:
            target = width * height
            return [res for res in cls if res.pixels >= target]
        return [res for res in cls if res.width >= width and res.height >= height]

    def __str__(self):
        return f"{self.name} ({self.width}x{self.height})"

    def __eq__(self, obj):
        return self.pixels == obj.pixels

    def __lt__(self, obj):
        return self.pixels < obj.pixels

    def __gt__(self, obj):
        return self.pixels > obj.pixels


if __name__ == "__main__":
    # 获取VGA分辨率信息
    vga = VideoResolution.VGA
    print(f"标准分辨率: {vga}")
    print(f"尺寸验证: {vga.width}x{vga.height}")
    print(f"像素总数: {vga.pixels}\n")

    # 尺寸比较示例
    test_width, test_height = 800, 600
    print(f"测试尺寸: {test_width}x{test_height}")

    # 双维度比较
    print("\n能够包含该尺寸的分辨率:")
    for res in VideoResolution.find_closest_resolutions(test_width, test_height, False):
        print(f"- {res}")

    # 像素比较
    print("\n像素数更大的分辨率:")
    for res in VideoResolution.find_closest_resolutions(test_width, test_height):
        if res.compare_pixels(test_width, test_height) == 1:
            print(f"- {res}")

    # 精确匹配查找
    matched = VideoResolution.get_resolution(1920, 1080)
    print(f"\n全高清匹配结果: {matched if matched else '无匹配'}")

    not_valid_resolution = VideoResolution(100, 100)
