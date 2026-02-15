import cv2
import pygame
from pathlib import Path
import os

ASSETS_DIR = Path(__file__).parent / "assets"
SMILE_CAPTURES_DIR = Path(__file__).parent / "smile_captures"
BODY_IMAGE = ASSETS_DIR / "2.png"


def get_latest_smile_capture():
    """Get the latest smile capture image"""
    if not SMILE_CAPTURES_DIR.exists():
        return None
    
    # Look for face_*.png files (from FaceCapture) or smile_capture_*.jpg (legacy)
    files = [f for f in os.listdir(SMILE_CAPTURES_DIR) if (f.startswith('face_') and f.endswith('.png')) or (f.startswith('smile_capture_') and f.endswith('.jpg'))]
    
    if not files:
        return None
    
    files_with_time = [(SMILE_CAPTURES_DIR / f, os.path.getmtime(SMILE_CAPTURES_DIR / f)) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    return files_with_time[0][0]


def create_player_sprite(width=64, height=96):
    """
    Composite player sprite from latest smile capture (head) + 2.png (body)
    Returns pygame Surface
    """
    # Load body image
    if not BODY_IMAGE.exists():
        raise FileNotFoundError(f"Body image not found at {BODY_IMAGE}")
    
    body = cv2.imread(str(BODY_IMAGE))
    if body is None:
        raise FileNotFoundError(f"Failed to load body image: {BODY_IMAGE}")
    
    # Resize body to target dimensions
    body = cv2.resize(body, (width, height))
    
    # Load latest smile capture
    smile_path = get_latest_smile_capture()
    if smile_path is None:
        print("Warning: No smile capture found. Using body only.")
        # Convert BGR to RGB for pygame
        body_rgb = cv2.cvtColor(body, cv2.COLOR_BGR2RGB)
        sprite = pygame.image.fromstring(body_rgb.tobytes(), body_rgb.shape[1::-1], "RGB")
        return sprite
    
    # Load and scale smile capture (for head, ~40% of total height)
    smile = cv2.imread(str(smile_path))
    if smile is None:
        print(f"Warning: Failed to load smile capture. Using body only.")
        body_rgb = cv2.cvtColor(body, cv2.COLOR_BGR2RGB)
        sprite = pygame.image.fromstring(body_rgb.tobytes(), body_rgb.shape[1::-1], "RGB")
        return sprite
    
    head_height = int(height * 0.4)
    head_width = int(width * 0.8)
    smile = cv2.resize(smile, (head_width, head_height))
    
    # Create composite on body
    # Place head at top-center of body
    head_x_offset = (width - head_width) // 2
    head_y_offset = 10
    
    composite = body.copy()
    # Blend head onto body
    composite[head_y_offset:head_y_offset+head_height, head_x_offset:head_x_offset+head_width] = smile
    
    # Convert BGR to RGB for pygame
    composite_rgb = cv2.cvtColor(composite, cv2.COLOR_BGR2RGB)
    sprite = pygame.image.fromstring(composite_rgb.tobytes(), composite_rgb.shape[1::-1], "RGB")
    
    return sprite


def save_player_sprite_debug(width=64, height=96):
    """
    Create and save composite sprite to assets folder for preview
    """
    if not BODY_IMAGE.exists():
        raise FileNotFoundError(f"Body image not found at {BODY_IMAGE}")
    
    body = cv2.imread(str(BODY_IMAGE))
    if body is None:
        raise FileNotFoundError(f"Failed to load body image: {BODY_IMAGE}")
    
    body = cv2.resize(body, (width, height))
    
    smile_path = get_latest_smile_capture()
    if smile_path is None:
        print("Warning: No smile capture found. Using body only.")
        body_rgb = cv2.cvtColor(body, cv2.COLOR_BGR2RGB)
        debug_path = ASSETS_DIR / "player_sprite_debug.png"
        cv2.imwrite(str(debug_path), body)
        print(f"Saved debug sprite to: {debug_path}")
        return
    
    smile = cv2.imread(str(smile_path))
    if smile is None:
        print(f"Warning: Failed to load smile capture. Using body only.")
        body_rgb = cv2.cvtColor(body, cv2.COLOR_BGR2RGB)
        debug_path = ASSETS_DIR / "player_sprite_debug.png"
        cv2.imwrite(str(debug_path), body)
        print(f"Saved debug sprite to: {debug_path}")
        return
    
    head_height = int(height * 0.4)
    head_width = int(width * 0.8)
    smile = cv2.resize(smile, (head_width, head_height))
    
    head_x_offset = (width - head_width) // 2
    head_y_offset = 10
    
    composite = body.copy()
    composite[head_y_offset:head_y_offset+head_height, head_x_offset:head_x_offset+head_width] = smile
    
    debug_path = ASSETS_DIR / "player_sprite_debug.png"
    cv2.imwrite(str(debug_path), composite)
    print(f"Saved debug sprite to: {debug_path}")
