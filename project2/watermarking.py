import numpy as np
import cv2
from PIL import Image, ImageEnhance
import hashlib
import os
import matplotlib.pyplot as plt
from scipy.fft import fft2, ifft2, fftshift, ifftshift


class WatermarkSystem:
    def __init__(self, secret_key=12345):
        """初始化水印系统，设置密钥和随机数生成器"""
        self.secret_key = secret_key
        self.rng = np.random.default_rng(secret_key)

    def generate_watermark(self, shape, type='binary'):
        """生成水印图案"""
        if type == 'binary':
            return self.rng.integers(0, 2, size=shape[:2], dtype=np.uint8)
        elif type == 'perlin':
            # 此处可实现Perlin噪声水印
            pass
        return None

    def embed_spatial_lsb(self, image, watermark, alpha=1.0):
        """在空间域使用LSB方法嵌入水印"""
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = image.astype(np.int32)
        watermark = (watermark * 255).astype(np.int32)

        # 嵌入水印
        watermarked = image.copy()
        watermarked = (watermarked & 0xFE) | ((watermark >> 7) & 0x01)
        return watermarked.astype(np.uint8)

    def extract_spatial_lsb(self, watermarked, original=None):
        """从空间域提取LSB水印"""
        if len(watermarked.shape) == 3:
            watermarked = cv2.cvtColor(watermarked, cv2.COLOR_BGR2GRAY)
        extracted = (watermarked & 0x01) * 255
        return extracted.astype(np.uint8)

    def embed_frequency_dct(self, image, watermark, alpha=0.1):
        """在频域使用DCT方法嵌入水印"""
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 确保图像尺寸是8的倍数
        h, w = image.shape
        h = h - (h % 8)
        w = w - (w % 8)
        image = image[:h, :w]

        watermarked = np.zeros_like(image, dtype=np.float32)  # 使用float32类型避免溢出
        h, w = image.shape

        # 8x8分块处理
        for i in range(0, h - 7, 8):
            for j in range(0, w - 7, 8):
                block = image[i:i + 8, j:j + 8].astype(np.float32)  # 转换为float32进行计算
                dct_block = cv2.dct(block)

                # 选择中频系数嵌入水印
                if i // 8 < watermark.shape[0] and j // 8 < watermark.shape[1]:
                    # 确保水印值为0或1
                    wm_value = 1.0 if watermark[i // 8, j // 8] > 0 else -1.0
                    dct_block[4, 4] += alpha * wm_value

                watermarked[i:i + 8, j:j + 8] = cv2.idct(dct_block)

        return np.clip(watermarked, 0, 255).astype(np.uint8)  # 转换回uint8并裁剪到有效范围


    def extract_frequency_dct(self, watermarked, original, alpha=0.1):
        """从频域提取DCT水印"""
        if len(watermarked.shape) == 3:
            watermarked = cv2.cvtColor(watermarked, cv2.COLOR_BGR2GRAY)
        if len(original.shape) == 3:
            original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)

        h, w = watermarked.shape
        watermark = np.zeros((h // 8, w // 8), dtype=np.float32)

        # 8x8分块处理
        for i in range(0, h - 7, 8):
            for j in range(0, w - 7, 8):
                if i // 8 < watermark.shape[0] and j // 8 < watermark.shape[1]:
                    # 原始图像DCT
                    orig_block = original[i:i + 8, j:j + 8].astype(np.float32)
                    orig_dct = cv2.dct(orig_block)

                    # 水印图像DCT
                    wm_block = watermarked[i:i + 8, j:j + 8].astype(np.float32)
                    wm_dct = cv2.dct(wm_block)

                    # 提取水印
                    watermark[i // 8, j // 8] = (wm_dct[4, 4] - orig_dct[4, 4]) / alpha

        # 二值化水印
        watermark = (watermark > 0).astype(np.uint8)
        return (watermark * 255).astype(np.uint8)

    def embed_frequency_dft(self, image, watermark, alpha=0.01):
        """在频域使用DFT方法嵌入水印"""
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 傅里叶变换
        f = fft2(image)
        fshift = fftshift(f)

        # 扩展水印到与图像相同大小
        h, w = image.shape
        watermark_resized = np.zeros((h, w), dtype=np.float32)
        h_wm, w_wm = watermark.shape
        watermark_resized[:h_wm, :w_wm] = watermark * 2 - 1

        # 嵌入水印
        fshift_wm = fshift.copy()
        fshift_wm[h // 4:3 * h // 4, w // 4:3 * w // 4] += alpha * watermark_resized[h // 4:3 * h // 4,
                                                                   w // 4:3 * w // 4]

        # 逆变换
        f_ishift = ifftshift(fshift_wm)
        img_back = ifft2(f_ishift)
        img_back = np.abs(img_back)

        return np.clip(img_back, 0, 255).astype(np.uint8)

    def extract_frequency_dft(self, watermarked, original, alpha=0.01):
        """从频域提取DFT水印"""
        if len(watermarked.shape) == 3:
            watermarked = cv2.cvtColor(watermarked, cv2.COLOR_BGR2GRAY)
        if len(original.shape) == 3:
            original = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)

        # 调整尺寸匹配
        if watermarked.shape != original.shape:
            original = cv2.resize(original, (watermarked.shape[1], watermarked.shape[0]))


        h, w = watermarked.shape

        # 原始图像傅里叶变换
        f_orig = fft2(original)
        fshift_orig = fftshift(f_orig)

        # 水印图像傅里叶变换
        f_wm = fft2(watermarked)
        fshift_wm = fftshift(f_wm)

        # 提取水印
        watermark = (fshift_wm - fshift_orig) / alpha

        # 取中间部分作为水印
        watermark = watermark[h // 4:3 * h // 4, w // 4:3 * w // 4]

        # 二值化水印
        watermark = (watermark > 0).astype(np.uint8)
        return (watermark * 255).astype(np.uint8)

    def calculate_ncc(self, original, extracted):
        """计算归一化相关系数(NCC)"""
        if original.shape != extracted.shape:
            extracted = cv2.resize(extracted, (original.shape[1], original.shape[0]))

        original = original.flatten().astype(np.float32)
        extracted = extracted.flatten().astype(np.float32)

        # 归一化
        original = (original - np.mean(original)) / (np.std(original) * len(original))
        extracted = (extracted - np.mean(extracted)) / (np.std(extracted))

        # 计算NCC
        ncc = np.sum(original * extracted)
        return ncc

    def calculate_psnr(self, original, processed):
        """计算峰值信噪比(PSNR)"""
        mse = np.mean((original - processed) ** 2)
        if mse == 0:
            return float('inf')
        max_pixel = 255.0
        psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
        return psnr