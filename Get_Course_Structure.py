# Run with Python 3
# Save course structure as seen in left menu to YAML and markdown files
import re
import json
import requests
from pathlib import Path
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Enter parameters below:
client_id = '...'
client_secret = '...'
api_host = 'https://stepik.org'

# Get a token
auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
response = requests.post(f'{api_host}/oauth2/token/',
                         data={'grant_type': 'client_credentials'},
                         auth=auth)
token = response.json().get('access_token', None)
if not token:
    print('Unable to authorize with provided credentials')
    exit(1)

def fetch_object(obj_class: str, obj_id: int) -> dict:
    """Fetch single object from Stepik API"""
    api_url = f'{api_host}/api/{obj_class}s/{obj_id}'
    response = requests.get(api_url,
                            headers={'Authorization': f'Bearer {token}'}).json()
    return response[f'{obj_class}s'][0]

def fetch_objects(obj_class: str, obj_ids: List[int]) -> List[dict]:
    """Fetch multiple objects from Stepik API"""
    objs = []
    step_size = 30
    for i in range(0, len(obj_ids), step_size):
        obj_ids_slice = obj_ids[i:i + step_size]
        ids_param = '&'.join(f'ids[]={obj_id}' for obj_id in obj_ids_slice)
        api_url = f'{api_host}/api/{obj_class}s?{ids_param}'
        response = requests.get(api_url,
                                headers={'Authorization': f'Bearer {token}'}).json()
        objs += response[f'{obj_class}s']
    return objs

def get_valid_filename(s: str) -> str:
    """Convert string to valid filename"""
    return re.sub(r'(?u)[^-\w. ]', '', str(s)).strip()

@dataclass
class Step:
    """Step class representing a single step in a lesson"""
    position: int
    step_id: int
    step_type: str
    title: str = ''
    content: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api(cls, step_data: dict, step_source: dict, position: int) -> 'Step':
        """Create Step from API data"""
        step_type = step_data['block']['name']
        # Create title based on step type and position
        if step_type == 'text':
            title = f'Шаг TEXT {position}'
        elif step_type == 'video':
            title = f'Шаг VIDEO {position}'
        elif step_type == 'choice':
            title = f'Шаг QUIZ {position}'
        elif step_type == 'sort':
            title = f'Шаг SORT {position}'
        elif step_type == 'matching':
            title = f'Шаг MATCH {position}'
        elif step_type == 'table':
            title = f'Шаг TABLE {position}'
        elif step_type == 'number':
            title = f'Шаг NUMBER {position}'
        elif step_type == 'string':
            title = f'Шаг STRING {position}'
        elif step_type == 'free-answer':
            title = f'Шаг ESSAY {position}'
        elif step_type == 'code':
            title = f'Шаг CODE {position}'
        elif step_type == 'admin':
            title = f'Шаг ADMIN {position}'
        else:
            title = f'Шаг {step_type.upper()} {position}'
        
        return cls(
            position=position,
            step_id=step_data['id'],
            step_type=step_type,
            title=title,
            content=step_source['block']
        )
    
    def to_markdown(self) -> str:
        """Convert step to markdown format"""
        md_lines = []
        
        # Add step header with type and number (like in left menu)
        md_lines.append(f'## {self.title}')
        
        # Add step content based on type
        if self.step_type == 'text':
            text = self.content.get('text', '')
            md_lines.append(text)
        elif self.step_type == 'video':
            video = self.content.get('video', {})
            md_lines.append('### Video')
            if video.get('urls'):
                for url_info in video['urls']:
                    md_lines.append(f'[{url_info["quality"]}p]({url_info["url"]})')
        elif self.step_type == 'choice':
            md_lines.append(self.content.get('text', ''))
            options = self.content.get('options', [])
            if options:
                md_lines.append('\nOptions:')
                for i, opt in enumerate(options, 1):
                    md_lines.append(f'{i}. {opt.get("text", "")}')
        elif self.step_type == 'code':
            md_lines.append('```' + self.content.get('code', 'python'))
            md_lines.append('# Write your code here')
            md_lines.append('```')
        
        return '\n'.join(md_lines)

@dataclass
class Lesson:
    """Lesson class containing steps (appears as numbered item in left menu: X.Y)"""
    section_position: int
    lesson_position: int
    lesson_id: int
    title: str
    steps: List[Step] = field(default_factory=list)
    
    @property
    def menu_number(self) -> str:
        """Get lesson number as it appears in left menu (e.g., 2.1)"""
        return f'{self.section_position}.{self.lesson_position}'
    
    @classmethod
    def from_api(cls, section_pos: int, unit_data: dict, lesson_data: dict, 
                 steps_data: List[dict], steps_source: List[dict]) -> 'Lesson':
        """Create Lesson from API data"""
        lesson = cls(
            section_position=section_pos,
            lesson_position=unit_data['position'],
            lesson_id=lesson_data['id'],
            title=lesson_data['title']
        )
        
        # Sort steps by position
        steps_data.sort(key=lambda x: x['position'])
        
        # Create Step objects
        for i, step_data in enumerate(steps_data, 1):
            step_source = next((s for s in steps_source if s['id'] == step_data['id']), None)
            if step_source:
                step = Step.from_api(step_data, step_source, i)
                lesson.steps.append(step)
        
        return lesson
    
    def to_markdown(self) -> str:
        """Convert lesson to markdown format with left menu numbering"""
        md_lines = []
        
        # Add lesson header with menu number
        md_lines.append(f'# {self.menu_number} {self.title}')
        md_lines.append(f'<!-- lesson_id: {self.lesson_id} -->')
        md_lines.append('')
        
        # Add all steps
        for step in self.steps:
            md_lines.append(step.to_markdown())
            md_lines.append('')
        
        return '\n'.join(md_lines)

@dataclass
class Section:
    """Section (module) class (appears as top-level number in left menu: 1, 2, 3...)"""
    position: int
    section_id: int
    title: str
    lessons: List[Lesson] = field(default_factory=list)
    
    @classmethod
    def from_api(cls, section_data: dict, units_data: List[dict], 
                 lessons_data: List[dict], steps_map: Dict[int, List[dict]], 
                 steps_source_map: Dict[int, List[dict]]) -> 'Section':
        """Create Section from API data"""
        section = cls(
            position=section_data['position'],
            section_id=section_data['id'],
            title=section_data['title']
        )
        
        # Filter units for this section and sort by position
        section_units = [u for u in units_data if u['section'] == section_data['id']]
        section_units.sort(key=lambda x: x['position'])
        
        # Create lessons with correct section position
        for unit in section_units:
            lesson_data = next((l for l in lessons_data if l['id'] == unit['lesson']), None)
            if lesson_data:
                steps = steps_map.get(lesson_data['id'], [])
                steps_source = steps_source_map.get(lesson_data['id'], [])
                lesson = Lesson.from_api(
                    section.position, 
                    unit, 
                    lesson_data, 
                    steps, 
                    steps_source
                )
                section.lessons.append(lesson)
        
        return section

@dataclass
class Course:
    """Course class containing the full left menu structure"""
    course_id: int
    title: str
    sections: List[Section] = field(default_factory=list)
    progress: str = '0/0'
    
    @classmethod
    def from_api(cls, course_id: int) -> 'Course':
        """Fetch course data from API and build full left menu structure"""
        # Get course
        course_data = fetch_object('course', course_id)
        
        course = cls(
            course_id=course_data['id'],
            title=course_data['title']
        )
        
        # Get all sections
        sections_data = fetch_objects('section', course_data['sections'])
        sections_data.sort(key=lambda x: x['position'])
        
        # Get all units
        all_unit_ids = []
        for section in sections_data:
            all_unit_ids.extend(section['units'])
        units_data = fetch_objects('unit', all_unit_ids)
        
        # Get all lessons
        all_lesson_ids = [unit['lesson'] for unit in units_data]
        lessons_data = fetch_objects('lesson', all_lesson_ids)
        
        # Get all steps for each lesson
        steps_map = {}
        steps_source_map = {}
        
        for lesson in lessons_data:
            if lesson['steps']:
                steps = fetch_objects('step', lesson['steps'])
                steps.sort(key=lambda x: x['position'])
                steps_map[lesson['id']] = steps
                
                step_sources = fetch_objects('step-source', lesson['steps'])
                steps_source_map[lesson['id']] = step_sources
        
        # Create sections
        for section_data in sections_data:
            section = Section.from_api(
                section_data, 
                units_data, 
                lessons_data,
                steps_map,
                steps_source_map
            )
            course.sections.append(section)
        
        # Calculate total steps for progress
        total_steps = sum(
            len(lesson.steps) 
            for section in course.sections 
            for lesson in section.lessons
        )
        course.progress = f'0/{total_steps}'
        
        return course
    
    def get_left_menu_text(self) -> str:
        """Generate text representation of left menu"""
        lines = []
        lines.append(self.title)
        lines.append(f'Прогресс по курсу:  {self.progress}')
        lines.append('')
        
        for section in self.sections:
            lines.append(f'{section.position}  {section.title}')
            lines.append('')
            
            for lesson in section.lessons:
                lines.append(f'{lesson.menu_number}  {lesson.title}')
                lines.append('')
        
        return '\n'.join(lines)
    
    def save_structure(self, output_dir: Path) -> Path:
        """Save course structure to YAML file and lessons to markdown"""
        # Create course directory
        course_dir = output_dir / f"{str(self.course_id).zfill(2)}_{get_valid_filename(self.title)}"
        course_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare TOC structure matching left menu
        toc = {
            'course': {
                'id': self.course_id,
                'title': self.title,
                'progress': self.progress,
                'sections': []
            }
        }
        
        # Save left menu text
        menu_file = course_dir / 'left_menu.txt'
        with open(menu_file, 'w', encoding='utf-8') as f:
            f.write(self.get_left_menu_text())
        
        # Save each section and lesson
        for section in self.sections:
            section_dir = course_dir / f"{str(section.position).zfill(2)}_{get_valid_filename(section.title)}"
            section_dir.mkdir(exist_ok=True)
            
            section_toc = {
                'position': section.position,
                'id': section.section_id,
                'title': section.title,
                'lessons': []
            }
            
            for lesson in section.lessons:
                # Create filename with menu number
                filename = f"{lesson.menu_number}_{get_valid_filename(lesson.title)}.md"
                lesson_file = section_dir / filename
                
                # Save lesson to markdown
                with open(lesson_file, 'w', encoding='utf-8') as f:
                    f.write(lesson.to_markdown())
                
                # Add to TOC with menu number
                lesson_toc = {
                    'menu': lesson.menu_number,
                    'position': lesson.lesson_position,
                    'id': lesson.lesson_id,
                    'title': lesson.title,
                    'file': str(lesson_file.relative_to(course_dir)),
                    'steps': []
                }
                
                for step in lesson.steps:
                    step_toc = {
                        'position': step.position,
                        'id': step.step_id,
                        'type': step.step_type,
                        'title': step.title
                    }
                    lesson_toc['steps'].append(step_toc)
                
                section_toc['lessons'].append(lesson_toc)
            
            toc['course']['sections'].append(section_toc)
        
        # Save TOC to YAML
        toc_file = course_dir / f"toc_{self.course_id}.yaml"
        with open(toc_file, 'w', encoding='utf-8') as f:
            yaml.dump(toc, f, allow_unicode=True, sort_keys=False)
        
        return toc_file

def main():
    """Main function"""
    print("Course Structure Saver")
    print("=" * 50)
    
    # Use first course in list for demonstration
    print("Fetching first course from your account...")
    
    # Get list of courses
    api_url = f'{api_host}/api/courses?is_public=false&page=1'
    response = requests.get(api_url, headers={'Authorization': f'Bearer {token}'}).json()
    
    if not response.get('courses'):
        print("No courses found. Please check your credentials.")
        return
    
    # Take first course
    first_course = response['courses'][0]
    course_id = first_course['id']
    print(f"Using course: {first_course['title']} (ID: {course_id})")
    
    try:
        # Fetch course structure
        print("\nFetching course structure...")
        course = Course.from_api(course_id)
        
        # Save to files
        output_dir = Path.cwd() / 'courses'
        toc_file = course.save_structure(output_dir)
        
        print(f"\nCourse structure saved successfully!")
        print(f"TOC file: {toc_file}")
        print(f"Course directory: {toc_file.parent}")
        
        # Print left menu preview
        print("\nLeft menu structure:")
        print("-" * 50)
        print(course.get_left_menu_text())
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
