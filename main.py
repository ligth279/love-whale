from pathlib import Path
import pygame
import random
from player_sprite import create_player_sprite
from face_capture import FaceCapture

ASSETS_DIR = Path(__file__).parent / "assets"
BACKGROUND_IMAGE = ASSETS_DIR / "1.png"
FLOOR_IMAGE = ASSETS_DIR / "3.png"
HEART_IMAGE = ASSETS_DIR / "heart.svg"
MINUS_IMAGE = ASSETS_DIR / "5.jpeg"

# Game constants
GRAVITY = 0.6
PLAYER_SPEED = 5
JUMP_POWER = 15
FLOOR_TILE_SIZE = 64
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
LEVEL_WIDTH = 2000  # Reduced from 5000 to make level beatable in 90 seconds
LEVEL_HEIGHT = 720
HEARTS_TO_WIN = 20
LIVES = 3

# Camera follows player - player positioned left-of-center
CAMERA_OFFSET_X = SCREEN_WIDTH // 4

MINUS_POINTER_PENALTY = 4
MINUS_POINTERS_COUNT = 5
TIME_LIMIT = 90  # seconds (extended to allow reaching the end)
MINUS_SPAWN_THRESHOLD = 8  # Minus pointers appear after collecting 8 hearts

# Dialogue
DIALOGUE = [
    ("Narrator", "Once upon a time, a lonely whale floated through the vast ocean..."),
    ("Whale", "So many empty days... so much loneliness..."),
    ("Narrator", "But one day, something magical happened."),
    ("Whale", "Wait... what is this feeling? Is it... love?"),
    ("Narrator", "A journey of hearts begins. Collect 20 hearts to win this level!"),
    ("Whale", "Let's go! I must find my way!"),
]


class Heart(pygame.sprite.Sprite):
    """Collectible heart sprite"""
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 32, 32)
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        # Draw a simple red heart shape
        self.draw_heart()
        self.collected = False
    
    def draw_heart(self):
        """Draw a simple heart shape"""
        pygame.draw.circle(self.image, (255, 0, 0), (8, 10), 7)
        pygame.draw.circle(self.image, (255, 0, 0), (24, 10), 7)
        pygame.draw.polygon(self.image, (255, 0, 0), [(2, 14), (30, 14), (16, 32)])
    
    def draw(self, screen, camera_x):
        """Draw heart with camera offset"""
        screen_x = self.rect.x - camera_x
        if 0 <= screen_x <= SCREEN_WIDTH:
            screen.blit(self.image, (screen_x, self.rect.y))


class MinusPointer(pygame.sprite.Sprite):
    """Obstacle that deducts hearts"""
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 32, 32)
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        self.collected = False
        self.active = False  # Only active after 8 hearts collected
        
        # Try to load the actual one.jpeg image
        if MINUS_IMAGE.exists():
            try:
                loaded_img = pygame.image.load(str(MINUS_IMAGE))
                self.image = pygame.transform.scale(loaded_img, (32, 32))
                print(f"[OK] Loaded minus image from {MINUS_IMAGE}")
            except Exception as e:
                print(f"[FAIL] Failed to load {MINUS_IMAGE}: {e}, using fallback")
                self.draw_minus()
        else:
            print(f"[FAIL] Minus image not found at {MINUS_IMAGE}, using fallback")
            self.draw_minus()
    
    def draw_minus(self):
        """Draw a visible minus symbol as fallback"""
        # Fill background with orange
        pygame.draw.circle(self.image, (255, 150, 0), (16, 16), 16)
        # Draw minus line
        pygame.draw.rect(self.image, (0, 0, 0), (8, 14, 16, 4))
        # Border
        pygame.draw.circle(self.image, (255, 100, 0), (16, 16), 16, 2)
    
    def draw(self, screen, camera_x):
        """Draw minus pointer with camera offset - displays the 5.jpeg image"""
        screen_x = self.rect.x - camera_x
        if -32 <= screen_x <= SCREEN_WIDTH:
            # Draw the image
            if self.active:
                # Bright when active
                screen.blit(self.image, (screen_x, self.rect.y))
            else:
                # Dim when inactive - reduce brightness
                dim_image = self.image.copy()
                dim_image.set_alpha(128)  # 50% opacity when inactive
                screen.blit(dim_image, (screen_x, self.rect.y))


class DialogueScene:
    def __init__(self, screen, background, dialogue_list):
        self.screen = screen
        self.background = background
        self.dialogue_list = dialogue_list
        self.current_index = 0
        self.font_speaker = pygame.font.Font(None, 36)
        self.font_text = pygame.font.Font(None, 28)
        self.done = False
    
    def handle_input(self, keys):
        if keys[pygame.K_SPACE] or keys[pygame.K_RETURN]:
            self.current_index += 1
            if self.current_index >= len(self.dialogue_list):
                self.done = True
    
    def draw(self):
        self.screen.blit(self.background, (0, 0))
        
        if self.current_index < len(self.dialogue_list):
            speaker, text = self.dialogue_list[self.current_index]
            
            # Draw semi-transparent dialogue box
            box_height = 150
            box_y = self.screen.get_height() - box_height - 20
            pygame.draw.rect(self.screen, (20, 20, 40), (20, box_y, self.screen.get_width() - 40, box_height))
            pygame.draw.rect(self.screen, (100, 150, 255), (20, box_y, self.screen.get_width() - 40, box_height), 3)
            
            # Draw speaker name
            speaker_text = self.font_speaker.render(f"{speaker}:", True, (255, 200, 100))
            self.screen.blit(speaker_text, (40, box_y + 20))
            
            # Draw dialogue text (word wrap)
            words = text.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                line_text = " ".join(current_line)
                if self.font_text.size(line_text)[0] > self.screen.get_width() - 100:
                    if len(current_line) > 1:
                        current_line.pop()
                        lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        lines.append(line_text)
                        current_line = []
            if current_line:
                lines.append(" ".join(current_line))
            
            for i, line in enumerate(lines[:3]):  # Max 3 lines
                dialogue_render = self.font_text.render(line, True, (255, 255, 255))
                self.screen.blit(dialogue_render, (40, box_y + 60 + i * 25))
            
            # Draw "Press SPACE to continue"
            continue_text = self.font_text.render("Press SPACE to continue...", True, (150, 255, 150))
            self.screen.blit(continue_text, (self.screen.get_width() - 320, box_y + box_height - 35))
        
        pygame.display.flip()
    
    def run(self, clock):
        while not self.done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
            
            keys = pygame.key.get_pressed()
            self.handle_input(keys)
            self.draw()
            clock.tick(60)
        
        return True


def show_dialogue(screen, background, clock):
    """Run the dialogue scene"""
    dialogue_scene = DialogueScene(screen, background, DIALOGUE)
    return dialogue_scene.run(clock)


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_player_sprite(width=64, height=96)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.lives = LIVES
        self.hearts_collected = 0
        self.start_time = pygame.time.get_ticks()
        self.minus_activated = False  # Track if we've already notified about activation
    
    def handle_input(self, keys):
        # A/D for left/right movement
        self.vel_x = 0
        if keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
        if keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
        
        # Space to jump
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -JUMP_POWER
            self.on_ground = False
    
    def update(self, floors, hearts, minus_pointers):
        # Apply gravity
        self.vel_y += GRAVITY
        
        # Move horizontally with level bounds
        self.rect.x += self.vel_x
        self.rect.x = max(0, min(self.rect.x, LEVEL_WIDTH - self.rect.width))
        
        # Move vertically
        self.rect.y += self.vel_y
        
        # Collision detection with floors
        self.on_ground = False
        for floor in floors:
            if self.rect.colliderect(floor.rect):
                # Landing on floor from above
                if self.vel_y > 0:
                    self.rect.bottom = floor.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                # Hit head on floor from below
                elif self.vel_y < 0:
                    self.rect.top = floor.rect.bottom
                    self.vel_y = 0
        
        # Heart collection
        for heart in hearts:
            if not heart.collected and self.rect.colliderect(heart.rect):
                heart.collected = True
                self.hearts_collected += 1
        
        # Minus pointer collection (deduct hearts)
        for minus in minus_pointers:
            if minus.active and not minus.collected and self.rect.colliderect(minus.rect):
                minus.collected = True
                self.hearts_collected -= MINUS_POINTER_PENALTY
                print(f"[-] Hit a minus pointer! Hearts now: {self.hearts_collected}")
        
        # Death on falling off screen
        if self.rect.top > SCREEN_HEIGHT:
            self.lives -= 1
            if self.lives <= 0:
                return False
            # Respawn at start
            self.rect.x = 100
            self.rect.y = 300
            self.vel_y = 0
        
        return True
    
    def draw(self, screen, camera_x):
        screen_x = self.rect.x - camera_x
        screen.blit(self.image, (screen_x, self.rect.y))
    
    def get_camera_x(self):
        """Calculate camera X position based on player position"""
        target_camera_x = self.rect.x - CAMERA_OFFSET_X
        return max(0, min(target_camera_x, LEVEL_WIDTH - SCREEN_WIDTH))


class Floor(pygame.sprite.Sprite):
    def __init__(self, x, y, width=64, height=64):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill((100, 200, 100))  # Placeholder green
        self.rect = self.image.get_rect(topleft=(x, y))
    
    def draw(self, screen, camera_x):
        screen_x = self.rect.x - camera_x
        if -self.rect.width <= screen_x <= SCREEN_WIDTH:
            screen.blit(self.image, (screen_x, self.rect.y))


def load_floor_image():
    """Load floor tile image"""
    if FLOOR_IMAGE.exists():
        return pygame.image.load(str(FLOOR_IMAGE))
    return None


def create_level():
    """Create procedurally generated level with 5000px width"""
    floors = []
    hearts = []
    minus_pointers = []
    floor_img = load_floor_image()
    
    # Ground floor with HOLES (not spanning entire level)
    # Create small gaps player can jump over (1-2 tiles = 64-128px)
    x = 0
    hole_positions = set()
    while x < LEVEL_WIDTH:
        # Random hole size (1-2 tiles only, so player CAN jump over)
        hole_size = random.randint(1, 2) * FLOOR_TILE_SIZE
        # Random distance before next hole (700-1000px)
        distance = random.randint(700, 1000)
        x += distance
        hole_positions.add((x, hole_size))
    
    for x in range(0, LEVEL_WIDTH, FLOOR_TILE_SIZE):
        # Skip this tile if it's in a hole
        skip = False
        for hole_x, hole_size in hole_positions:
            if abs(x - hole_x) < hole_size // 2 + FLOOR_TILE_SIZE:  # Only skip tiles within the hole
                skip = True
                break
        
        if not skip:
            floor = Floor(x, LEVEL_HEIGHT - FLOOR_TILE_SIZE)
            if floor_img:
                floor.image = pygame.transform.scale(floor_img, (FLOOR_TILE_SIZE, FLOOR_TILE_SIZE))
            floors.append(floor)
    
    # Generate floating platforms procedurally
    platform_x = 300
    heart_count = 0
    all_platforms = []  # Store platform positions for minus pointer placement
    
    while platform_x < LEVEL_WIDTH - 400:
        # Random platform height (250-450 pixels from top)
        platform_y = random.randint(250, 450)
        
        # Platform width (1-3 tiles)
        platform_width = random.randint(1, 3)
        
        for i in range(platform_width):
            floor = Floor(platform_x + i * FLOOR_TILE_SIZE, platform_y)
            if floor_img:
                floor.image = pygame.transform.scale(floor_img, (FLOOR_TILE_SIZE, FLOOR_TILE_SIZE))
            floors.append(floor)
        
        all_platforms.append((platform_x, platform_y, platform_width))
        
        # Place 1 heart on this platform
        if heart_count < HEARTS_TO_WIN:
            heart_x = platform_x + FLOOR_TILE_SIZE * platform_width // 2
            heart_y = platform_y - 50
            hearts.append(Heart(heart_x, heart_y))
            heart_count += 1
        
        # Gap between platforms (150-250 pixels)
        gap = random.randint(150, 250)
        platform_x += platform_width * FLOOR_TILE_SIZE + gap
    
    # Place hearts on ground floor (every 300px, scattered around)
    for x in range(500, LEVEL_WIDTH - 500, 300):
        if heart_count < HEARTS_TO_WIN:
            ground_y = LEVEL_HEIGHT - FLOOR_TILE_SIZE - 50
            # Add some randomness to x position
            heart_x = x + random.randint(-50, 50)
            hearts.append(Heart(heart_x, ground_y))
            heart_count += 1
    
    # Fill remaining hearts if needed
    if heart_count < HEARTS_TO_WIN:
        for x in range(300, LEVEL_WIDTH - 300, 150):
            if heart_count < HEARTS_TO_WIN:
                ground_y = LEVEL_HEIGHT - FLOOR_TILE_SIZE - 50
                hearts.append(Heart(x, ground_y))
                heart_count += 1
    
    print(f"[OK] Total hearts placed: {len(hearts)} (target: {HEARTS_TO_WIN})")
    print(f"  ~ {len([h for h in hearts if h.rect.y < 250])} on floating platforms")
    print(f"  ~ {len([h for h in hearts if h.rect.y >= LEVEL_HEIGHT - FLOOR_TILE_SIZE - 50])} on ground floor")
    
    # Place 5 minus pointers with distribution: 40% on floating (with space), 20% on ground, 40% random
    minus_count = 0
    max_retries = 5  # Try up to 5 times to find a valid spot
    
    for placement_type in range(MINUS_POINTERS_COUNT):
        if minus_count >= MINUS_POINTERS_COUNT:
            break
        
        placed = False
        retries = 0
        
        while not placed and retries < max_retries:
            placement_roll = random.random()
            
            if placement_roll < 0.4 and all_platforms:
                # 40% - On floating platforms (with random platform selection)
                platform_choice = all_platforms[random.randint(0, len(all_platforms) - 1)]
                px, py, pw = platform_choice
                minus_x = px + (pw - 1) * FLOOR_TILE_SIZE - 30
                minus_y = py - 50
                
                # Check if it overlaps with hearts
                overlap = False
                for heart in hearts:
                    if abs(minus_x - heart.rect.x) < 50 and abs(minus_y - heart.rect.y) < 50:
                        overlap = True
                        break
                
                if not overlap:
                    minus_pointers.append(MinusPointer(minus_x, minus_y))
                    print(f"[OK] Minus pointer {minus_count + 1} at ({minus_x}, {minus_y}) [FLOATING]")
                    minus_count += 1
                    placed = True
            
            elif placement_roll < 0.6:
                # 20% - On ground floor
                ground_x = random.randint(500, LEVEL_WIDTH - 500)
                ground_y = LEVEL_HEIGHT - FLOOR_TILE_SIZE - 50
                
                overlap = False
                for heart in hearts:
                    if abs(ground_x - heart.rect.x) < 50 and abs(ground_y - heart.rect.y) < 50:
                        overlap = True
                        break
                
                if not overlap:
                    minus_pointers.append(MinusPointer(ground_x, ground_y))
                    print(f"[OK] Minus pointer {minus_count + 1} at ({ground_x}, {ground_y}) [GROUND FLOOR]")
                    minus_count += 1
                    placed = True
            
            else:
                # 40% - Random positioning
                random_x = random.randint(500, LEVEL_WIDTH - 500)
                random_y = random.randint(100, 400)
                
                overlap = False
                for heart in hearts:
                    if abs(random_x - heart.rect.x) < 50 and abs(random_y - heart.rect.y) < 50:
                        overlap = True
                        break
                
                if not overlap:
                    minus_pointers.append(MinusPointer(random_x, random_y))
                    print(f"[OK] Minus pointer {minus_count + 1} at ({random_x}, {random_y}) [RANDOM]")
                    minus_count += 1
                    placed = True
            
            retries += 1
    
    print(f"Total minus pointers created: {len(minus_pointers)}")
    return floors, hearts, minus_pointers


def show_win_screen(screen, background, clock, hearts_count):
    """Display beautiful win screen with proposal message to girl"""
    font_big = pygame.font.Font(None, 80)
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 28)
    
    messages = [
        "You collected all 20 hearts! 💕",
        "",
        "The love whale has found their purpose...",
        "",
        "Now comes the greatest adventure of all:",
        "",
        "Will you propose to the girl you love?",
        "",
        "With 20 hearts full of courage,",
        "Ask her: 'Will you be my love whale?'",
    ]
    
    # Show win screen with fade effect
    alpha_step = 5
    alpha = 0
    
    win_running = True
    start_time = pygame.time.get_ticks()
    
    while win_running and alpha < 255:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    alpha = 255
        
        # Draw background
        screen.blit(background, (0, 0))
        
        # Create semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(alpha)
        overlay.fill((10, 30, 60))
        screen.blit(overlay, (0, 0))
        
        # Draw win text elements with fade
        text_alpha = int(alpha * 0.8)
        
        # Title
        title_surface = font_big.render("🎉 YOU WIN! 🎉", True, (255, 215, 0))
        title_surface.set_alpha(text_alpha)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)
        
        # Hearts collected
        hearts_text = font_large.render(f"{hearts_count} ❤️ Hearts Collected", True, (255, 100, 150))
        hearts_text.set_alpha(text_alpha)
        hearts_rect = hearts_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(hearts_text, hearts_rect)
        
        # Messages
        y_offset = 280
        for message in messages:
            if message:
                color = (255, 200, 100) if "propose" in message.lower() or "love whale" in message.lower() else (200, 220, 255)
                msg_surface = font_small.render(message, True, color)
                msg_surface.set_alpha(text_alpha)
                msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(msg_surface, msg_rect)
            y_offset += 45
        
        # Press SPACE to continue
        if pygame.time.get_ticks() - start_time > 2000:
            space_text = font_small.render("Press SPACE to continue...", True, (100, 255, 100))
            space_text.set_alpha(int(text_alpha * 0.7))
            space_rect = space_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
            screen.blit(space_text, space_rect)
        
        pygame.display.flip()
        clock.tick(60)
        alpha += alpha_step
    
    # Hold the win screen for a bit
    hold_time = 0
    while win_running and hold_time < 3000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                hold_time = 3000
        
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((10, 30, 60))
        screen.blit(overlay, (0, 0))
        
        title_surface = font_big.render("🎉 YOU WIN! 🎉", True, (255, 215, 0))
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)
        
        hearts_text = font_large.render(f"{hearts_count} ❤️ Hearts Collected", True, (255, 100, 150))
        hearts_rect = hearts_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(hearts_text, hearts_rect)
        
        y_offset = 280
        for message in messages:
            if message:
                color = (255, 200, 100) if "propose" in message.lower() or "love whale" in message.lower() else (200, 220, 255)
                msg_surface = font_small.render(message, True, color)
                msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(msg_surface, msg_rect)
            y_offset += 45
        
        space_text = font_small.render("Press SPACE to continue...", True, (100, 255, 100))
        space_rect = space_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        screen.blit(space_text, space_rect)
        
        pygame.display.flip()
        clock.tick(60)
        hold_time += clock.get_time()
    
    return True


def show_lonely_win_screen(screen, background, clock, hearts_count):
    """Display beautiful win screen with proposal message to guy (lonely ending)"""
    font_big = pygame.font.Font(None, 80)
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 28)
    
    messages = [
        "You reached the end with only sorrow... 💔",
        "",
        "The love whale became so lonely",
        f"that it found purpose in solitude ({hearts_count} hearts)",
        "",
        "But perhaps there's still hope:",
        "",
        "Will you propose to the boy you love?",
        "",
        "With courage born from loneliness,",
        "Ask him: 'Will you heal my whale heart?'",
    ]
    
    # Show win screen with fade effect
    alpha_step = 5
    alpha = 0
    
    win_running = True
    start_time = pygame.time.get_ticks()
    
    while win_running and alpha < 255:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    alpha = 255
        
        # Draw background
        screen.blit(background, (0, 0))
        
        # Create semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(alpha)
        overlay.fill((40, 10, 30))  # Darker red tint for lonely ending
        screen.blit(overlay, (0, 0))
        
        # Draw win text elements with fade
        text_alpha = int(alpha * 0.8)
        
        # Title
        title_surface = font_big.render("💔 LONELY VICTORY 💔", True, (200, 100, 150))
        title_surface.set_alpha(text_alpha)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)
        
        # Hearts collected
        hearts_text = font_large.render(f"{hearts_count} 💔 Hearts Lost", True, (255, 150, 150))
        hearts_text.set_alpha(text_alpha)
        hearts_rect = hearts_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(hearts_text, hearts_rect)
        
        # Messages
        y_offset = 280
        for message in messages:
            if message:
                color = (255, 180, 150) if "propose" in message.lower() or "heal" in message.lower() else (200, 180, 220)
                msg_surface = font_small.render(message, True, color)
                msg_surface.set_alpha(text_alpha)
                msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(msg_surface, msg_rect)
            y_offset += 40
        
        # Press SPACE to continue
        if pygame.time.get_ticks() - start_time > 2000:
            space_text = font_small.render("Press SPACE to continue...", True, (150, 200, 255))
            space_text.set_alpha(int(text_alpha * 0.7))
            space_rect = space_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
            screen.blit(space_text, space_rect)
        
        pygame.display.flip()
        clock.tick(60)
        alpha += alpha_step
    
    # Hold the win screen for a bit
    hold_time = 0
    while win_running and hold_time < 3000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                hold_time = 3000
        
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((40, 10, 30))
        screen.blit(overlay, (0, 0))
        
        title_surface = font_big.render("💔 LONELY VICTORY 💔", True, (200, 100, 150))
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)
        
        hearts_text = font_large.render(f"{hearts_count} 💔 Hearts Lost", True, (255, 150, 150))
        hearts_rect = hearts_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(hearts_text, hearts_rect)
        
        y_offset = 280
        for message in messages:
            if message:
                color = (255, 180, 150) if "propose" in message.lower() or "heal" in message.lower() else (200, 180, 220)
                msg_surface = font_small.render(message, True, color)
                msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(msg_surface, msg_rect)
            y_offset += 40
        
        space_text = font_small.render("Press SPACE to continue...", True, (150, 200, 255))
        space_rect = space_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        screen.blit(space_text, space_rect)
        
        pygame.display.flip()
        clock.tick(60)
        hold_time += clock.get_time()
    
    return True


def show_bachelor_screen(screen, background, clock, hearts_count):
    """Display bachelor ending screen"""
    font_big = pygame.font.Font(None, 80)
    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 28)
    
    messages = [
        f"You finished with {hearts_count} hearts...",
        "",
        "Not enough love, but not enough sadness either.",
        "",
        "The whale looks at the horizon,",
        "then back at the mirror...",
        "",
        "CONGRATULATIONS!",
        "",
        "You are destined to be a BACHELOR FOREVER! 🎩",
        "",
        "A free whale, forever floating alone.",
    ]
    
    # Show screen with fade effect
    alpha_step = 5
    alpha = 0
    
    running = True
    start_time = pygame.time.get_ticks()
    
    while running and alpha < 255:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    alpha = 255
        
        # Draw background
        screen.blit(background, (0, 0))
        
        # Create semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(alpha)
        overlay.fill((30, 30, 30))  # Dark neutral gray
        screen.blit(overlay, (0, 0))
        
        # Draw text elements with fade
        text_alpha = int(alpha * 0.8)
        
        # Title
        title_surface = font_big.render("🎩 BACHELOR FOR LIFE 🎩", True, (200, 200, 100))
        title_surface.set_alpha(text_alpha)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)
        
        # Hearts status
        hearts_text = font_large.render(f"{hearts_count} ❓ Hearts Remaining", True, (150, 150, 200))
        hearts_text.set_alpha(text_alpha)
        hearts_rect = hearts_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(hearts_text, hearts_rect)
        
        # Messages
        y_offset = 280
        for message in messages:
            if message:
                if "CONGRATULATIONS" in message or "BACHELOR" in message:
                    color = (255, 200, 100)
                elif "destined" in message:
                    color = (255, 150, 0)
                else:
                    color = (180, 180, 220)
                msg_surface = font_small.render(message, True, color)
                msg_surface.set_alpha(text_alpha)
                msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(msg_surface, msg_rect)
            y_offset += 40
        
        # Press SPACE to continue
        if pygame.time.get_ticks() - start_time > 2000:
            space_text = font_small.render("Press SPACE to continue...", True, (100, 200, 100))
            space_text.set_alpha(int(text_alpha * 0.7))
            space_rect = space_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
            screen.blit(space_text, space_rect)
        
        pygame.display.flip()
        clock.tick(60)
        alpha += alpha_step
    
    # Hold the screen for a bit
    hold_time = 0
    while running and hold_time < 3000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                hold_time = 3000
        
        screen.blit(background, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((30, 30, 30))
        screen.blit(overlay, (0, 0))
        
        title_surface = font_big.render("🎩 BACHELOR FOR LIFE 🎩", True, (200, 200, 100))
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title_surface, title_rect)
        
        hearts_text = font_large.render(f"{hearts_count} ❓ Hearts Remaining", True, (150, 150, 200))
        hearts_rect = hearts_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        screen.blit(hearts_text, hearts_rect)
        
        y_offset = 280
        for message in messages:
            if message:
                if "CONGRATULATIONS" in message or "BACHELOR" in message:
                    color = (255, 200, 100)
                elif "destined" in message:
                    color = (255, 150, 0)
                else:
                    color = (180, 180, 220)
                msg_surface = font_small.render(message, True, color)
                msg_rect = msg_surface.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
                screen.blit(msg_surface, msg_rect)
            y_offset += 40
        
        space_text = font_small.render("Press SPACE to continue...", True, (100, 200, 100))
        space_rect = space_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
        screen.blit(space_text, space_rect)
        
        pygame.display.flip()
        clock.tick(60)
        hold_time += clock.get_time()
    
    return True


def draw_ui(screen, player):
    """Draw UI elements (hearts collected, lives remaining, timer)"""
    font = pygame.font.Font(None, 32)
    
    # Hearts collected (can be negative)
    hearts_color = (255, 100, 100)
    if player.hearts_collected < 0:
        hearts_color = (255, 200, 0)  # Yellow/orange for negative
    
    hearts_text = font.render(f"Hearts: {player.hearts_collected}/{HEARTS_TO_WIN}", True, hearts_color)
    screen.blit(hearts_text, (20, 20))
    
    # Lives remaining
    lives_text = font.render(f"Lives: {player.lives}", True, (255, 255, 255))
    screen.blit(lives_text, (20, 60))
    
    # Timer
    elapsed_ms = pygame.time.get_ticks() - player.start_time
    elapsed_seconds = elapsed_ms / 1000.0
    time_remaining = max(0, TIME_LIMIT - elapsed_seconds)
    
    timer_color = (100, 255, 100)  # Green
    if time_remaining < 10:
        timer_color = (255, 100, 100)  # Red if < 10 seconds
    
    timer_text = font.render(f"Time: {time_remaining:.1f}s", True, timer_color)
    screen.blit(timer_text, (20, 100))
    
    # Warning when minus pointers are active
    if player.hearts_collected >= MINUS_SPAWN_THRESHOLD:
        warning_font = pygame.font.Font(None, 28)
        warning_text = warning_font.render("[!] MINUS POINTERS ACTIVE! AVOID THEM!", True, (255, 100, 100))
        screen.blit(warning_text, (SCREEN_WIDTH - 400, 20))


def main() -> None:
    if not BACKGROUND_IMAGE.is_file():
        raise FileNotFoundError(f"Missing background image at {BACKGROUND_IMAGE}")

    pygame.init()
    loaded_surface = pygame.image.load(str(BACKGROUND_IMAGE))
    # Scale background to fill screen
    background = pygame.transform.scale(loaded_surface, (SCREEN_WIDTH, SCREEN_HEIGHT))
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Love Whale - Level 1")
    clock = pygame.time.Clock()

    # Capture player's face for custom sprite
    print("\n" + "="*50)
    print("CAPTURING YOUR SMILE...")
    print("="*50)
    capturer = FaceCapture()
    face_path = capturer.capture_face_with_smile(timeout=60)
    capturer.release()
    if face_path:
        print(f"\n[OK] Face captured: {face_path}\n")
    else:
        print("\nNo face captured - using default character\n")

    # Show dialogue first
    dialogue_complete = show_dialogue(screen, background, clock)
    if not dialogue_complete:
        pygame.quit()
        return

    # Create player and level
    player = Player(100, 300)
    floors, hearts, minus_pointers = create_level()

    running = True
    game_won = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        
        alive = player.update(floors, hearts, minus_pointers)
        if not alive:
            print(f"Game Over! Final hearts: {player.hearts_collected}/{HEARTS_TO_WIN}")
            running = False
        
        # Check win condition FIRST (before time/lives checks)
        if player.rect.x > LEVEL_WIDTH - 200:
            if player.hearts_collected >= HEARTS_TO_WIN:
                print(f"You won! Collected all {HEARTS_TO_WIN} hearts!")
                # Show beautiful win screen - propose to girl
                show_win_screen(screen, background, clock, player.hearts_collected)
                game_won = True
                running = False
            elif player.hearts_collected <= -1:
                print(f"Lonely victory! You reached the end with {player.hearts_collected} hearts...")
                # Show lonely win screen with proposal to guy
                show_lonely_win_screen(screen, background, clock, player.hearts_collected)
                game_won = True
                running = False
            elif 0 < player.hearts_collected < HEARTS_TO_WIN:
                print(f"Bachelor ending! You finished with {player.hearts_collected} hearts...")
                # Show bachelor forever screen
                show_bachelor_screen(screen, background, clock, player.hearts_collected)
                game_won = True
                running = False
        
        # Only check time/lives if game hasn't been won yet
        if not running:
            continue
        
        # Check time limit
        elapsed_ms = pygame.time.get_ticks() - player.start_time
        elapsed_seconds = elapsed_ms / 1000.0
        if elapsed_seconds >= TIME_LIMIT:
            print(f"Time's up! Final hearts: {player.hearts_collected}/{HEARTS_TO_WIN}")
            running = False
        
        # Check if minus pointers should activate
        if player.hearts_collected >= MINUS_SPAWN_THRESHOLD and not player.minus_activated:
            # Activate all minus pointers so they can be collected
            for minus in minus_pointers:
                minus.active = True
            print(f"[!] WARNING! Minus pointers have appeared! Avoid them!")
            player.minus_activated = True
        
        # Get camera position
        camera_x = player.get_camera_x()
        
        # Draw everything
        # Tile background across level
        for i in range(0, LEVEL_WIDTH, SCREEN_WIDTH):
            screen.blit(background, (i - camera_x, 0))
        
        # Draw floors
        for floor in floors:
            floor.draw(screen, camera_x)
        
        # Draw hearts
        for heart in hearts:
            if not heart.collected:
                heart.draw(screen, camera_x)
        
        # Draw minus pointers
        for minus in minus_pointers:
            if not minus.collected:
                minus.draw(screen, camera_x)
        
        # Draw player
        player.draw(screen, camera_x)
        
        # Draw UI
        draw_ui(screen, player)
        
        pygame.display.flip()
        clock.tick(60)

    # Show ending screen if player died without reaching the end
    if not game_won:
        if player.hearts_collected >= HEARTS_TO_WIN:
            show_win_screen(screen, background, clock, player.hearts_collected)
        elif player.hearts_collected <= -1:
            show_lonely_win_screen(screen, background, clock, player.hearts_collected)
        elif player.hearts_collected > 0:
            show_bachelor_screen(screen, background, clock, player.hearts_collected)
        else:
            # Game Over screen for 0 or negative hearts
            print(f"Game Over! You finished with {player.hearts_collected} hearts.")

    pygame.quit()


if __name__ == "__main__":
    main()
