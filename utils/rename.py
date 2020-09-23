import os
import re
import sys

file_dir = r"/Users/nut/Pictures/Resource/LRT_20200909_org/"
new_file_dir = r"/Users/nut/Pictures/Resource/new/"

fileList = os.listdir(file_dir)
# 输出此文件夹中包含的文件名称
print("修改前：" + str(fileList))
list.sort(fileList)
print("排序后：" + str(fileList))
# 得到进程当前工作目录
currentpath = os.getcwd()
try:
    # 将当前工作目录修改为待修改文件夹的位置
    os.chdir(new_file_dir)
except Exception as e:
    os.makedirs(new_file_dir)
    os.chdir(new_file_dir)
else:
    os.makedirs(new_file_dir)
    os.chdir(new_file_dir)
finally:
    pass

# 名称序列起始值
num = 7
# 遍历文件夹中所有文件
for fileName in fileList:
    # 匹配文件名正则表达式
    pat = ".+\.(jpg)"
    # 进行匹配
    try:
        pattern = re.findall(pat, fileName)[0]
        print('fileName',fileName,'pattern',pattern)
    except Exception as e:
        print('e',e)
    else:
        print('pattern',pattern)
        # 文件重新命名
        os.rename(file_dir + fileName, ('LRT_' + str(num).zfill(5) + '.' + pattern))
        # 改变编号，继续下一项
        num = num + 1
print("***************************************")
# 改回程序运行前的工作目录
os.chdir(currentpath)
# 刷新
sys.stdin.flush()
# 输出修改后文件夹中包含的文件名称
print("修改后：" + str(os.listdir(r"/Users/nut/Pictures/Resource/new")))
