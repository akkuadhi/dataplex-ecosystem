
import os
import sys
# Add parent to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from Shared_Resources.networking import setup_environment_logic

print("Running setup_environment_logic()...")
success, mode, status = setup_environment_logic()
print(f"Success: {success}")
print(f"Mode: {mode}")
print(f"Status: {status}")

if not success:
    print("\nEnvironment Variables:")
    for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        print(f"{var}: {os.environ.get(var)}")
