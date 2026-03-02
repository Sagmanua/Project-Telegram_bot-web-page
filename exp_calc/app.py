import math

def calculate_xp(skill_number, current_percentage):
    """
    Calculates the total XP required to reach a certain percentage 
    of a specific skill number.
    """
    if skill_number < 1:
        return 0

    
    base_xp_first_skill = 210064
    
    xp_previous_skills = base_xp_first_skill * (2**(skill_number - 1) - 1)
    

    xp_current_skill = base_xp_first_skill * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1)
    
    return round(xp_previous_skills + xp_current_skill)

skill_num = int(input("Enter skill number (e.g., 1, 2, 3): "))
percentage = float(input("Enter target percentage (0-100): "))

total_needed = calculate_xp(skill_num, percentage)

print(f"\nTo reach {percentage}% of skill #{skill_num}:")
print(f"You need a total of {total_needed:,} XP on that crew member.")