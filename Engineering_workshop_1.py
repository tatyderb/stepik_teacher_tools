# Run with Python 3
# Save course structure (sections and lessons) to YAML file in current folder
import re
import requests
from pathlib import Path
import yaml
from dataclasses import dataclass, field
from typing import List, Dict

client_id = 'OsLhovOYWZr6yo1ktQyV7SDQae911bLfjB50TyP5'
client_secret = '0vP90obw9agj89F8whEXgKvzhPsPTEq9YefBPGZlXI2GdRi6a5ZXP1R4LNzGiDd4fWP3hSmok51CO8RCMHL0W2t53xfjlUDpkqJxpvp7OlLb4q3rwm6XZKuAEGSpGaDx'
api_host = 'https://stepik.org'

# Get token
auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
response = requests.post(f'{api_host}/oauth2/token/',
                         data={'grant_type': 'client_credentials'},
                         auth=auth)
token = response.json().get('access_token')
if not token:
    print('Unable to authorize')
    exit(1)


def fetch_object(obj_class: str, obj_id: int) -> dict:
    url = f'{api_host}/api/{obj_class}s/{obj_id}'
    r = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    return r.json()[f'{obj_class}s'][0]


def fetch_objects(obj_class: str, obj_ids: List[int]) -> List[dict]:
    objs = []
    for i in range(0, len(obj_ids), 30):
        ids_param = '&'.join(f'ids[]={id}' for id in obj_ids[i:i+30])
        url = f'{api_host}/api/{obj_class}s?{ids_param}'
        r = requests.get(url, headers={'Authorization': f'Bearer {token}'})
        objs += r.json().get(f'{obj_class}s', [])
    return objs


def get_valid_filename(s: str) -> str:
    return re.sub(r'(?u)[^-\w. ]', '', str(s)).strip()


@dataclass
class Lesson:
    section_position: int
    lesson_position: int
    lesson_id: int
    title: str

    @property
    def menu_number(self) -> str:
        return f'{self.section_position}.{self.lesson_position}'

    @classmethod
    def from_api(cls, section_pos: int, unit_data: dict, lesson_data: dict) -> 'Lesson':
        return cls(
            section_position=section_pos,
            lesson_position=unit_data['position'],
            lesson_id=lesson_data['id'],
            title=lesson_data['title']
        )


@dataclass
class Section:
    position: int
    section_id: int
    title: str
    lessons: List[Lesson] = field(default_factory=list)

    @classmethod
    def from_api(cls, section_data: dict, units_data: List[dict],
                 lessons_map: Dict[int, dict]) -> 'Section':
        section = cls(
            position=section_data['position'],
            section_id=section_data['id'],
            title=section_data['title']
        )
        section_units = [u for u in units_data if u['section'] == section_data['id']]
        section_units.sort(key=lambda x: x['position'])
        for unit in section_units:
            lesson_data = lessons_map.get(unit['lesson'])
            if lesson_data:
                lesson = Lesson.from_api(section.position, unit, lesson_data)
                section.lessons.append(lesson)
        return section


@dataclass
class Course:
    course_id: int
    title: str
    sections: List[Section] = field(default_factory=list)

    @classmethod
    def from_api(cls, course_id: int) -> 'Course':
        course_data = fetch_object('course', course_id)
        course = cls(course_id=course_data['id'], title=course_data['title'])
        print(f"Курс: {course_data['title']}")

        sections_data = fetch_objects('section', course_data['sections'])
        sections_data.sort(key=lambda x: x['position'])
        print(f"Секций: {len(sections_data)}")

        all_unit_ids = []
        for s in sections_data:
            all_unit_ids.extend(s['units'])
        units_data = fetch_objects('unit', all_unit_ids)
        print(f"Юнитов: {len(units_data)}")

        all_lesson_ids = [u['lesson'] for u in units_data]
        lessons_data = fetch_objects('lesson', all_lesson_ids)
        print(f"Уроков: {len(lessons_data)}")

        lessons_map = {l['id']: l for l in lessons_data}

        for sdata in sections_data:
            section = Section.from_api(sdata, units_data, lessons_map)
            course.sections.append(section)
        return course

    def save_yaml(self, output_path: Path) -> None:
        """Save only structure (sections and lessons) to YAML file"""
        toc = {}
        for section in self.sections:
            section_key = section.position
            toc[section_key] = {
                'name': section.title,
                'lessons': {}
            }
            for lesson in section.lessons:
                lesson_key = lesson.menu_number
                # file field is empty because we don't create .md files
                toc[section_key]['lessons'][lesson_key] = {
                    'id': lesson.lesson_id,
                    'name': lesson.title,
                    'file': ""   # or omit this key if you prefer
                }
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump({'toc': toc}, f, allow_unicode=True, sort_keys=False)


def main():
    course_id = 253149
    try:
        course = Course.from_api(course_id)
        yaml_file = Path.cwd() / f"toc_{course_id}.yaml"
        course.save_yaml(yaml_file)
        print(f"\nYAML сохранён: {yaml_file}")
        total_lessons = sum(len(s.lessons) for s in course.sections)
        print(f"Всего: {len(course.sections)} модулей, {total_lessons} уроков")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()