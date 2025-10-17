"""
Extract skills from job descriptions
"""
from typing import List


class SkillExtractor:
    """Extract technical skills from job descriptions"""
    
    COMMON_SKILLS = [
        "Python", "R", "SQL", "Java", "JavaScript", "TypeScript", "C++", "Scala", "Go",
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Keras",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "LLM",
        "Data Analysis", "Statistics", "A/B Testing", "ETL", "Big Data", "Spark",
        "Tableau", "Power BI", "Looker", "Git", "REST API", "FastAPI", "Flask", "Django"
    ]
    
    @classmethod
    def extract(cls, description: str) -> List[str]:
        """
        Extract skills from job description
        
        Args:
            description: Job description text
            
        Returns:
            List of found skills
        """
        found_skills = []
        description_lower = description.lower()
        
        for skill in cls.COMMON_SKILLS:
            if skill.lower() in description_lower:
                found_skills.append(skill)
        
        return list(set(found_skills))
