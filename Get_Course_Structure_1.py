# Run with Python 3
# Save course structure as seen in left menu to YAML and markdown files
import re
import json
import requests
from pathlib import Path
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# ВСТАВЬ СВОИ ДАННЫЕ ЗДЕСЬ
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
    print('Проверь client_id и client_secret')
    exit(1)


def fetch_object(obj_class: str, obj_id: int) -> dict:
    """Fetch single object from Stepik API"""
    api_url = f'{api_host}/api/{obj_class}s/{obj_id}'
    response = requests.get(api_url,
                            headers={'Authorization': f'Bearer {token}'})
    data = response.json()
    # Stepik API всегда возвращает объекты в списке даже для одного объекта
    return data[f'{obj_class}s'][0]


def fetch_objects(obj_class: str, obj_ids: List[int]) -> List[dict]:
    """Fetch multiple objects from Stepik API"""
    objs = []
    step_size = 30
    for i in range(0, len(obj_ids), step_size):
        obj_ids_slice = obj_ids[i:i + step_size]
        ids_param = '&'.join(f'ids[]={obj_id}' for obj_id in obj_ids_slice)
        api_url = f'{api_host}/api/{obj_class}s?{ids_param}'
        response = requests.get(api_url,
                                headers={'Authorization': f'Bearer {token}'})
        data = response.json()
        objs += data.get(f'{obj_class}s', [])
    return objs


def fetch_step_source(step_id: int) -> dict:
    """Fetch step source for a specific step"""
    api_url = f'{api_host}/api/step-sources/{step_id}'
    response = requests.get(api_url,
                            headers={'Authorization': f'Bearer {token}'})
    data = response.json()
    return data['step-sources'][0]


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
    text: str = ''

    @classmethod
    def from_api(cls, step_data: dict, position: int) -> 'Step':
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

        # Get text content if available
        text = step_data['block'].get('text', '')

        return cls(
            position=position,
            step_id=step_data['id'],
            step_type=step_type,
            title=title,
            text=text
        )

    def to_markdown(self) -> str:
        """Convert step to markdown format"""
        md_lines = []

        # Add step header with type and number
        md_lines.append(f'## {self.title}')
        md_lines.append(f'<!-- step_id: {self.step_id} -->')

        # Add step content
        if self.text:
            md_lines.append(self.text)
        else:
            md_lines.append('*Нет текстового содержания*')

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
    def from_api(cls, section_pos: int, unit_data: dict, lesson_data: dict) -> 'Lesson':
        """Create Lesson from API data"""
        lesson = cls(
            section_position=section_pos,
            lesson_position=unit_data['position'],
            lesson_id=lesson_data['id'],
            title=lesson_data['title']
        )

        # Get steps for this lesson
        if lesson_data.get('steps'):
            steps_data = fetch_objects('step', lesson_data['steps'])
            steps_data.sort(key=lambda x: x['position'])

            # Create Step objects
            for i, step_data in enumerate(steps_data, 1):
                step = Step.from_api(step_data, i)
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
            md_lines.append('---')
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
                 lessons_map: Dict[int, dict]) -> 'Section':
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
            lesson_data = lessons_map.get(unit['lesson'])
            if lesson_data:
                lesson = Lesson.from_api(
                    section.position,
                    unit,
                    lesson_data
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

        print(f"  Загружено: курс")

        # Get all sections
        sections_data = fetch_objects('section', course_data['sections'])
        sections_data.sort(key=lambda x: x['position'])
        print(f"  Загружено: {len(sections_data)} секций")

        # Get all units
        all_unit_ids = []
        for section in sections_data:
            all_unit_ids.extend(section['units'])
        units_data = fetch_objects('unit', all_unit_ids)
        print(f"  Загружено: {len(units_data)} юнитов")

        # Get all lessons
        all_lesson_ids = [unit['lesson'] for unit in units_data]
        lessons_data = fetch_objects('lesson', all_lesson_ids)
        print(f"  Загружено: {len(lessons_data)} уроков")

        # Create lessons map for quick access
        lessons_map = {lesson['id']: lesson for lesson in lessons_data}

        # Create sections
        for section_data in sections_data:
            print(f"  Обработка секции {section_data['position']}: {section_data['title'][:30]}...")
            section = Section.from_api(
                section_data,
                units_data,
                lessons_map
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
                lines.append(f'  {lesson.menu_number}  {lesson.title}')
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

    # ID курса, который нужно спарсить
    course_id = 253149  # ID нужного курса

    try:
        # Проверяем доступность курса
        print(f"Проверка курса с ID: {course_id}...")
        course_info = fetch_object('course', course_id)
        print(f"Курс найден: {course_info['title']}")
        print(f"Количество секций: {len(course_info['sections'])}")

        # Загружаем полную структуру
        print("\nЗагрузка полной структуры курса...")
        course = Course.from_api(course_id)

        # Сохраняем в файлы
        output_dir = Path.cwd() / 'courses'
        toc_file = course.save_structure(output_dir)

        print(f"\nСтруктура курса успешно сохранена!")
        print(f"YAML файл: {toc_file}")
        print(f"Папка курса: {toc_file.parent}")

        # Статистика
        total_lessons = sum(len(section.lessons) for section in course.sections)
        total_steps = sum(len(lesson.steps) for section in course.sections for lesson in section.lessons)
        print(f"Итого: {len(course.sections)} модулей, {total_lessons} уроков, {total_steps} шагов")

        # Превью левого меню
        print("\nСтруктура левого меню:")
        print("-" * 50)
        print(course.get_left_menu_text())

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
        print("\nВозможные причины:")
        print("1. Неверный client_id или client_secret")
        print("2. Курс 253149 не существует или недоступен")
        print("3. Проблемы с подключением к Stepik API")


if __name__ == "__main__":
    main()
