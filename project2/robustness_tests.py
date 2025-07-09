import numpy as np
import cv2
from PIL import Image, ImageEnhance
import hashlib
import os
import matplotlib.pyplot as plt
from scipy.fft import fft2, ifft2, fftshift, ifftshift

class RobustnessTester:
    def __init__(self, watermark_system):
        """初始化鲁棒性测试器"""
        self.watermark_system = watermark_system

    def test_rotation(self, watermarked_image, degrees=45):
        """测试旋转攻击"""
        h, w = watermarked_image.shape[:2]
        center = (w // 2, h // 2)

        # 旋转矩阵
        M = cv2.getRotationMatrix2D(center, degrees, 1.0)
        rotated = cv2.warpAffine(watermarked_image, M, (w, h))

        return rotated

    def test_scaling(self, watermarked_image, scale=0.5):
        """测试缩放攻击"""
        scaled = cv2.resize(watermarked_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        return scaled

    def test_cropping(self, watermarked_image, crop_ratio=0.2):
        """测试裁剪攻击"""
        h, w = watermarked_image.shape[:2]
        crop_h, crop_w = int(h * crop_ratio), int(w * crop_ratio)
        cropped = watermarked_image[crop_h:h - crop_h, crop_w:w - crop_w]
        return cropped

    def test_noise(self, watermarked_image, noise_level=20):
        """测试噪声攻击"""
        row, col = watermarked_image.shape[:2]
        if len(watermarked_image.shape) == 3:
            ch = watermarked_image.shape[2]
            noise = np.random.randint(-noise_level, noise_level, size=(row, col, ch), dtype=np.int8)
        else:
            noise = np.random.randint(-noise_level, noise_level, size=(row, col), dtype=np.int8)

        noisy = np.clip(watermarked_image + noise, 0, 255).astype(np.uint8)
        return noisy

    def test_jpeg_compression(self, watermarked_image, quality=50):
        """测试JPEG压缩攻击"""
        _, encoded = cv2.imencode('.jpg', watermarked_image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        return decoded

    def test_contrast(self, watermarked_image, factor=1.5):
        """测试对比度调整攻击"""
        if len(watermarked_image.shape) == 3:
            img = cv2.cvtColor(watermarked_image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img)
        else:
            pil_img = Image.fromarray(watermarked_image)

        enhancer = ImageEnhance.Contrast(pil_img)
        enhanced_img = enhancer.enhance(factor)

        if len(watermarked_image.shape) == 3:
            return cv2.cvtColor(np.array(enhanced_img), cv2.COLOR_RGB2BGR)
        return np.array(enhanced_img)

    def test_blurring(self, watermarked_image, kernel_size=5):
        """测试模糊攻击"""
        blurred = cv2.GaussianBlur(watermarked_image, (kernel_size, kernel_size), 0)
        return blurred

    def run_all_tests(self, watermarked_image, original_image, original_watermark, extraction_func):
        """运行所有鲁棒性测试并返回结果"""
        tests = {
            "原始": lambda x: x,
            "旋转45度": lambda x: self.test_rotation(x, 45),
            "旋转90度": lambda x: self.test_rotation(x, 90),
            "缩放0.5倍": lambda x: self.test_scaling(x, 0.5),
            "缩放2倍": lambda x: self.test_scaling(x, 2.0),
            "裁剪20%": lambda x: self.test_cropping(x, 0.2),
            "椒盐噪声": lambda x: self.test_noise(x, 20),
            "JPEG压缩(Q=50)": lambda x: self.test_jpeg_compression(x, 50),
            "JPEG压缩(Q=30)": lambda x: self.test_jpeg_compression(x, 30),
            "对比度增强1.5倍": lambda x: self.test_contrast(x, 1.5),
            "对比度减弱0.5倍": lambda x: self.test_contrast(x, 0.5),
            "高斯模糊(5x5)": lambda x: self.test_blurring(x, 5)
        }

        results = {}
        for test_name, test_func in tests.items():
            attacked_image = test_func(watermarked_image)

            # 尝试提取水印
            try:
                extracted_watermark = extraction_func(attacked_image, original_image)

                # 计算NCC
                ncc = self.watermark_system.calculate_ncc(original_watermark, extracted_watermark)

                # 计算PSNR（如果图像尺寸匹配）
                if attacked_image.shape == original_image.shape:
                    psnr = self.watermark_system.calculate_psnr(original_image, attacked_image)
                else:
                    psnr = None

                results[test_name] = {
                    'attacked_image': attacked_image,
                    'extracted_watermark': extracted_watermark,
                    'ncc': ncc,
                    'psnr': psnr
                }
            except Exception as e:
                print(f"测试 {test_name} 失败: {str(e)}")
                results[test_name] = {
                    'attacked_image': attacked_image,
                    'extracted_watermark': None,
                    'ncc': None,
                    'psnr': None,
                    'error': str(e)
                }

        return results


    def visualize_results(self, results, original_watermark, title="鲁棒性测试结果"):
        """可视化鲁棒性测试结果"""
        num_tests = len(results)
        # 动态计算子图布局，确保有足够的列数
        num_cols = min(10, num_tests + 1)  # 最多10列，避免图形过宽
        num_rows = (num_tests + 1) // num_cols + 1  # 计算所需行数

        fig, axes = plt.subplots(num_rows, num_cols, figsize=(5 * num_cols, 5 * num_rows))
        axes = axes.flatten()  # 将二维数组展平为一维数组

        # 设置标题
        fig.suptitle(title, fontsize=16)

        # 绘制原始水印
        axes[0].imshow(original_watermark, cmap='gray')
        axes[0].set_title("原始水印")
        axes[0].axis('off')

        # 绘制攻击后的图像和提取的水印
        for i, (test_name, result) in enumerate(results.items()):
            idx = i + 1

            # 绘制攻击后的图像
            if len(result['attacked_image'].shape) == 3:
                axes[idx].imshow(cv2.cvtColor(result['attacked_image'], cv2.COLOR_BGR2RGB))
            else:
                axes[idx].imshow(result['attacked_image'], cmap='gray')

            axes[idx].set_title(f"{test_name}\nPSNR: {result['psnr']:.2f}" if result['psnr'] is not None else test_name)
            axes[idx].axis('off')

            # 绘制提取的水印
            idx_wm = idx + num_tests + 1  # 水印图像的位置
            if idx_wm < len(axes):
                if result['extracted_watermark'] is not None:
                    axes[idx_wm].imshow(result['extracted_watermark'], cmap='gray')
                    axes[idx_wm].set_title(f"NCC: {result['ncc']:.4f}")
                else:
                    axes[idx_wm].text(0.5, 0.5, '提取失败', ha='center', va='center', transform=axes[idx_wm].transAxes)
                    axes[idx_wm].set_title("提取失败")
                axes[idx_wm].axis('off')

         # 隐藏多余的子图
        for i in range(len(results) * 2 + 1, len(axes)):
            axes[i].axis('off')

        plt.tight_layout()
        plt.subplots_adjust(top=0.9)
        plt.show()

        # 返回NCC值表格
        ncc_table = {test_name: result['ncc'] for test_name, result in results.items()}
        return ncc_table
