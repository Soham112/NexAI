"""
Input validation utilities
"""


def get_user_input():
    """
    Prompt user for job search parameters with validation
    
    Returns:
        Tuple of (job_title, location, strict_location)
    """
    print("\n" + "=" * 60)
    print("JOB MARKET AGENT")
    print("=" * 60)
    
    job_title = input("\nEnter job title (e.g., Data Scientist, analyst): ").strip()
    while not job_title:
        print("❌ Job title cannot be empty!")
        job_title = input("Enter job title: ").strip()
    
    location = input("Enter location (e.g., Dallas, New York) or press Enter for ALL: ").strip()
    
    # Ask about location strictness
    if location:
        print(f"\n📍 Location Filter Options:")
        print(f"  1. Flexible (includes '{location}', nearby areas, and remote jobs)")
        print(f"  2. Strict (only exact '{location}' matches)")
        
        choice = input("\nChoose option (1 or 2) [default: 1]: ").strip()
        strict_location = (choice == "2")
        
        if strict_location:
            print(f"   ✓ Using STRICT location filter: '{location}' only")
        else:
            print(f"   ✓ Using FLEXIBLE location filter: '{location}' + nearby + remote")
    else:
        strict_location = False
        print("   ✓ No location filter - searching ALL locations")
    
    return job_title, location, strict_location
