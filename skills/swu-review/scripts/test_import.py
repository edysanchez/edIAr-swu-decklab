import sys
sys.path.insert(0, '.')
print("sys.path:", sys.path[:3])
print("Looking for domain.services...")
try:
    from domain.services.aspect_penalty_service import AspectPenaltyService
    print("Import successful!")
except ImportError as e:
    print(f"Import error: {e}")
    # List what's in domain
    import os
    domain_dir = '/home/edy/repos/edIAr-swu-decklab/skills/swu-review/scripts/domain'
    print(f"Files in domain dir: {os.listdir(domain_dir)}")
