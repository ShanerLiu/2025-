import numpy as np
import cv2
from PIL import Image, ImageEnhance
import hashlib
import os
import matplotlib.pyplot as plt
from scipy.fft import fft2, ifft2, fftshift, ifftshift
from watermarking import WatermarkSystem
from robustness_tests import RobustnessTester
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False  

def main():
    # 初始化水印系统
    watermark_system = WatermarkSystem(secret_key=42)

    # 加载原始图像
    original_image = cv2.imread('lena.jpg')
    if original_image is None:
        print("无法加载图像，请确保lena.jpg存在")
        return

    # 转换为灰度图
    original_gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    # 生成水印
    watermark = watermark_system.generate_watermark(original_gray.shape)

    # 水印嵌入（使用不同方法）
    watermarked_lsb = watermark_system.embed_spatial_lsb(original_gray, watermark)
    watermarked_dct = watermark_system.embed_frequency_dct(original_gray, watermark, alpha=10)
    watermarked_dft = watermark_system.embed_frequency_dft(original_gray, watermark, alpha=100)

    # 初始化鲁棒性测试器
    tester = RobustnessTester(watermark_system)

    # 测试LSB方法
    print("测试LSB水印方法...")
    lsb_results = tester.run_all_tests(
        watermarked_lsb,
        original_gray,
        watermark * 255,
        lambda img, orig: watermark_system.extract_spatial_lsb(img)
    )
    lsb_ncc_table = tester.visualize_results(lsb_results, watermark * 255, "LSB水印鲁棒性测试")

    # 测试DCT方法
    print("\n测试DCT水印方法...")
    dct_results = tester.run_all_tests(
        watermarked_dct,
        original_gray,
        watermark * 255,
        lambda img, orig: watermark_system.extract_frequency_dct(img, orig, alpha=10)
    )
    dct_ncc_table = tester.visualize_results(dct_results, watermark * 255, "DCT水印鲁棒性测试")

    # 测试DFT方法
    print("\n测试DFT水印方法...")
    dft_results = tester.run_all_tests(
        watermarked_dft,
        original_gray,
        watermark * 255,
        lambda img, orig: watermark_system.extract_frequency_dft(img, orig, alpha=100)
    )
    dft_ncc_table = tester.visualize_results(dft_results, watermark * 255, "DFT水印鲁棒性测试")

    print("\n不同水印方法的鲁棒性比较 (NCC值):")
    methods = ["LSB", "DCT", "DFT"]
    tests = list(lsb_ncc_table.keys())

    # 打印表头
    header = "{:<20}".format("测试类型")
    for method in methods:
        header += "{:<15}".format(method)
    print(header)
    print("-" * (20 + 15 * len(methods)))

    # 打印每行数据
    for test in tests:
        row = "{:<20}".format(test)

        for ncc_table in [lsb_ncc_table, dct_ncc_table, dft_ncc_table]:
            ncc = ncc_table.get(test)
            row += "{:<15.4f}".format(ncc) if ncc is not None else "{:<15}".format("N/A")

        print(row)

    # 保存结果
    if not os.path.exists("results"):
        os.makedirs("results")

    cv2.imwrite("results/original.jpg", original_gray)
    cv2.imwrite("results/watermark.jpg", watermark * 255)
    cv2.imwrite("results/watermarked_lsb.jpg", watermarked_lsb)
    cv2.imwrite("results/watermarked_dct.jpg", watermarked_dct)
    cv2.imwrite("results/watermarked_dft.jpg", watermarked_dft)

    print("\n结果已保存到'results'文件夹")


if __name__ == "__main__":
    main()
