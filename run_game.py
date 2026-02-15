"""
Face Avatar Game Launcher
Installs dependencies and starts the game
"""
import subprocess
import sys
import os

def install_dependencies():
    """Install required packages"""
    packages = ['pygame', 'pillow']
    
    print("="*60)
    print("INSTALLING DEPENDENCIES")
    print("="*60)
    
    for package in packages:
        print(f"\nInstalling {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
        print(f"[OK] {package} installed")
    
    print("\n" + "="*60)
    print("[OK] All dependencies installed successfully!")
    print("="*60 + "\n")

def main():
    """Main launcher"""
    print("\n")
    print("+" + "="*58 + "+")
    print("|" + "  FACE AVATAR GAME - Smile to Play!  ".center(58) + "|")
    print("+" + "="*58 + "+")
    print()
    
    # Check and install dependencies
    required_packages = {'pygame': 'pygame', 'PIL': 'pillow'}
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}\n")
        install_dependencies()
    else:
        print("[OK] All dependencies already installed\n")
    
    # Import and run game
    print("Starting game...\n")
    try:
        from game import main as run_game
        run_game()
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nTrying to install missing dependencies...")
        install_dependencies()
        try:
            from game import main as run_game
            run_game()
        except Exception as e2:
            print(f"Failed to start game: {e2}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"Error running game: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
