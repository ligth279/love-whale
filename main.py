from pathlib import Path

import pygame

ASSETS_DIR = Path(__file__).parent / "assets"
BACKGROUND_IMAGE = ASSETS_DIR / "1.png"


def main() -> None:
    if not BACKGROUND_IMAGE.is_file():
        raise FileNotFoundError(f"Missing background image at {BACKGROUND_IMAGE}")

    pygame.init()
    loaded_surface = pygame.image.load(str(BACKGROUND_IMAGE))
    screen = pygame.display.set_mode(loaded_surface.get_rect().size)
    background = loaded_surface.convert()
    pygame.display.set_caption("Love Whale")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.blit(background, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
