"""
Image processing utilities for optimizing invoice images before OCR
"""
from PIL import Image, ImageEnhance, ImageFilter
import io
from typing import Tuple, Optional
from app.utils.logger import app_logger


def optimize_image_for_ocr(
    image_bytes: bytes,
    max_size: Tuple[int, int] = (2000, 2000),
    enhance_contrast: float = 1.5,
    enhance_sharpness: float = 1.3
) -> bytes:
    """
    Optimize image for better OCR results
    
    Steps:
    1. Convert to RGB if needed
    2. Resize if too large
    3. Enhance contrast
    4. Enhance sharpness
    5. Convert to grayscale (optional for better text recognition)
    
    Args:
        image_bytes: Original image as bytes
        max_size: Maximum width and height
        enhance_contrast: Contrast enhancement factor (1.0 = no change)
        enhance_sharpness: Sharpness enhancement factor (1.0 = no change)
        
    Returns:
        Optimized image as bytes
    """
    try:
        # Load image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        app_logger.info(f"Original image size: {image.size}, mode: {image.mode}")
        
        # Convert to RGB if needed (handles RGBA, P, etc.)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Resize if too large
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            app_logger.info(f"Resized image to: {image.size}")
        
        # Enhance contrast
        if enhance_contrast != 1.0:
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(enhance_contrast)
        
        # Enhance sharpness
        if enhance_sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(enhance_sharpness)
        
        # Apply slight unsharp mask for better text clarity
        image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        
        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95, optimize=True)
        optimized_bytes = output.getvalue()
        
        app_logger.info(f"Image optimized. Original: {len(image_bytes)} bytes, Optimized: {len(optimized_bytes)} bytes")
        
        return optimized_bytes
        
    except Exception as e:
        app_logger.error(f"Error optimizing image: {e}")
        # Return original if optimization fails
        return image_bytes


def convert_to_grayscale(image_bytes: bytes) -> bytes:
    """
    Convert image to grayscale for better text recognition
    
    Args:
        image_bytes: Original image as bytes
        
    Returns:
        Grayscale image as bytes
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95)
        
        return output.getvalue()
        
    except Exception as e:
        app_logger.error(f"Error converting to grayscale: {e}")
        return image_bytes


def validate_image_format(image_bytes: bytes) -> bool:
    """
    Validate that the image is in a supported format
    
    Args:
        image_bytes: Image as bytes
        
    Returns:
        True if valid format, False otherwise
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Supported formats
        supported_formats = ['JPEG', 'PNG', 'JPG']
        return image.format in supported_formats
    except Exception:
        return False


def get_image_info(image_bytes: bytes) -> Optional[dict]:
    """
    Get information about the image
    
    Args:
        image_bytes: Image as bytes
        
    Returns:
        Dictionary with image info or None if invalid
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        return {
            'format': image.format,
            'mode': image.mode,
            'size': image.size,
            'width': image.size[0],
            'height': image.size[1],
            'size_bytes': len(image_bytes)
        }
    except Exception as e:
        app_logger.error(f"Error getting image info: {e}")
        return None
