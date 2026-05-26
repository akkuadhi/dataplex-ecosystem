
import subprocess
import json

def upgrade_all():
    print("Fetching outdated packages...")
    result = subprocess.run(["pip", "list", "--outdated", "--format=json"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error fetching outdated packages.")
        return

    outdated = json.loads(result.stdout)
    packages = [pkg["name"] for pkg in outdated]

    if not packages:
        print("All packages are up to date.")
        return

    print(f"Upgrading {len(packages)} packages: {', '.join(packages)}")
    
    # Upgrade one by one to avoid issues with large command lines or conflicting dependencies
    for pkg in packages:
        print(f"\n--- Upgrading {pkg} ---")
        subprocess.run(["pip", "install", "--upgrade", pkg])

if __name__ == "__main__":
    upgrade_all()
