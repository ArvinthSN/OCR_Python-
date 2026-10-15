import cv2
import numpy as np
from scipy.signal import convolve2d
from app.config import settings

class ImageDeblurrer:
    @staticmethod
    def unsharp_mask(image: np.ndarray, sigma: float = 1.0, strength: float = 1.5) -> np.ndarray:
        """
        Applies conservative unsharp masking for mild blur without amplifying noise.
        """
        blurred = cv2.GaussianBlur(image, (0, 0), sigma)
        sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    @staticmethod
    def wiener_deconvolution(image: np.ndarray, kernel_size: int = 5, nsr: float = 0.05) -> np.ndarray:
        """
        Regularized Wiener deconvolution for defocus blur using estimated Gaussian PSF.
        """
        is_color = len(image.shape) == 3
        channels = [image[:, :, i] for i in range(3)] if is_color else [image]
        deblurred_channels = []

        # Create Gaussian PSF kernel
        kernel = cv2.getGaussianKernel(kernel_size, kernel_size / 3.0)
        psf = kernel @ kernel.T
        psf /= psf.sum()

        h, w = channels[0].shape
        # Pad PSF to image size
        psf_padded = np.zeros((h, w), dtype=np.float32)
        kh, kw = psf.shape
        psf_padded[:kh, :kw] = psf

        # Optical transfer function
        otf = np.fft.fft2(psf_padded)
        otf_conj = np.conj(otf)
        # Wiener filter: H* / (|H|^2 + nsr)
        wiener_filter = otf_conj / (np.abs(otf) ** 2 + nsr)

        for ch in channels:
            img_fft = np.fft.fft2(ch.astype(np.float32))
            restored_fft = img_fft * wiener_filter
            restored = np.fft.ifft2(restored_fft)
            restored = np.real(restored)
            restored = np.roll(restored, -kh // 2, axis=0)
            restored = np.roll(restored, -kw // 2, axis=1)
            deblurred_channels.append(np.clip(restored, 0, 255).astype(np.uint8))

        if is_color:
            return cv2.merge(deblurred_channels)
        return deblurred_channels[0]

    @staticmethod
    def motion_deblur(image: np.ndarray, length: int = 7, angle: float = 0.0, nsr: float = 0.05) -> np.ndarray:
        """
        Deconvolves linear motion blur kernel along the estimated dominant gradient direction.
        """
        is_color = len(image.shape) == 3
        channels = [image[:, :, i] for i in range(3)] if is_color else [image]
        deblurred_channels = []

        # Construct linear motion blur kernel
        kernel = np.zeros((length, length), dtype=np.float32)
        center = (length - 1) / 2.0
        # Line rotation
        rot_mat = cv2.getRotationMatrix2D((center, center), angle, 1.0)
        kernel[int(center), :] = 1.0
        kernel = cv2.warpAffine(kernel, rot_mat, (length, length))
        kernel /= max(1e-5, kernel.sum())

        h, w = channels[0].shape
        kernel_padded = np.zeros((h, w), dtype=np.float32)
        kh, kw = kernel.shape
        kernel_padded[:kh, :kw] = kernel

        otf = np.fft.fft2(kernel_padded)
        wiener_filter = np.conj(otf) / (np.abs(otf)**2 + nsr)

        for ch in channels:
            img_fft = np.fft.fft2(ch.astype(np.float32))
            restored = np.real(np.fft.ifft2(img_fft * wiener_filter))
            restored = np.roll(restored, -kh // 2, axis=0)
            restored = np.roll(restored, -kw // 2, axis=1)
            deblurred_channels.append(np.clip(restored, 0, 255).astype(np.uint8))

        if is_color:
            return cv2.merge(deblurred_channels)
        return deblurred_channels[0]

    @staticmethod
    def adaptive_rescale_text(image: np.ndarray, median_text_height: float) -> np.ndarray:
        """
        Adaptively rescales image so that estimated text height approaches the optimal ~32px
        target for recognizers, bounded by maximum image dimension.
        """
        if median_text_height <= 0 or median_text_height >= settings.OPTIMAL_TEXT_HEIGHT_PIXELS:
            return image

        target_height = float(settings.OPTIMAL_TEXT_HEIGHT_PIXELS)
        scale = min(3.0, target_height / median_text_height)

        h, w = image.shape[:2]
        new_w = int(w * scale)
        new_h = int(h * scale)

        # Enforce max dimension budget
        if max(new_w, new_h) > settings.MAX_IMAGE_DIMENSION:
            scale = settings.MAX_IMAGE_DIMENSION / float(max(w, h))
            new_w = int(w * scale)
            new_h = int(h * scale)

        if scale <= 1.05:
            return image

        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
