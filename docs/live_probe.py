"""Live click-through evidence. Run explicitly; creates a labelled demo quiz."""
from pathlib import Path
from datetime import datetime
import json
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
MODE = 'mobile' if '--mobile' in sys.argv else 'desktop'
OUT = ROOT / 'images' / 'live-check' / MODE
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://minilms-nhom7.onrender.com/'
results = []

def shot(page, name):
    page.screenshot(path=str(OUT / (name + '.png')), full_page=True)
    results.append({'step': name, 'url': page.url})
    (OUT / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')

def login(page, role):
    page.goto(BASE)
    page.locator('#email').fill('ngan.lecturer@example.edu' if role == 'lecturer' else 'duc.student@example.edu')
    page.locator('#password').fill('MiniLMS2026!')
    page.get_by_role('button', name='Sign in', exact=True).click()
    page.wait_for_load_state('networkidle')

def confirm(page, label):
    page.get_by_role('button', name=label, exact=True).click()
    dialog = page.locator('dialog')
    if dialog.count():
        dialog.get_by_role('button').last.click()
    page.wait_for_load_state('networkidle')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    context = browser.new_context(viewport={'width': 390, 'height': 844} if MODE == 'mobile' else {'width': 1365, 'height': 900}, is_mobile=MODE == 'mobile', has_touch=MODE == 'mobile')
    page = context.new_page()
    page.set_default_timeout(20000)
    login(page, 'lecturer')
    shot(page, 'US01-lecturer')
    page.get_by_role('link', name='+ Create Quiz').first.click()
    title = 'LIVE CHECK ' + datetime.now().strftime('%Y%m%d-%H%M%S')
    page.locator('[name=title]').fill(title)
    confirm(page, 'Create Quiz')
    page.wait_for_load_state('networkidle')
    assert page.locator('.badge-draft').is_visible()
    shot(page, 'US02-created')
    page.reload()
    assert title in page.inner_text('body')
    shot(page, 'US02-after-F5')
    shot(page, 'rule-empty-quiz')
    page.get_by_text('Add Questions', exact=True).click()
    page.locator('#question-content').fill('Live check: 2 + 2 = ?')
    for i, value in enumerate(['4', '3', '5', '6']):
        page.locator('#choice-' + str(i)).fill(value)
    page.locator('[name=correct_index]').first.check()
    confirm(page, 'Add Question')
    page.wait_for_load_state('networkidle')
    assert '1 question' in page.inner_text('.manage-quiz-overview')
    shot(page, 'US03-added')
    page.get_by_text('Questions List', exact=True).click()
    page.locator('.manage-question-item details summary').first.click()
    page.locator('[id^=edit-question-content]').fill('Live check edited: 2 + 2 = ?')
    confirm(page, 'Save changes')
    page.get_by_text('Questions List', exact=True).click()
    assert 'Live check edited: 2 + 2 = ?' in page.inner_text('.manage-question-list')
    shot(page, 'm3-edit-question-after')
    page.locator('#max-attempts').fill('2')
    confirm(page, 'Save Schedule')
    page.reload()
    assert page.locator('#max-attempts').input_value() == '2'
    shot(page, 'm3-attempt-limit-after')
    confirm(page, 'Publish Quiz')
    assert page.locator('.badge-published').is_visible()
    shot(page, 'US04-published')
    mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    student = mobile.new_page()
    login(student, 'student')
    shot(student, 'US01-student-mobile')
    row = student.locator('tr').filter(has_text=title)
    row.get_by_role('button').first.click()
    student.wait_for_load_state('networkidle')
    assert student.locator('#timer').is_visible()
    timer_box = student.locator('#timer').bounding_box()
    assert 0 <= timer_box['x'] and timer_box['x'] + timer_box['width'] <= 390
    assert 0 <= timer_box['y'] and timer_box['y'] + timer_box['height'] <= 844
    student.locator('[name=choice_id]').first.check()
    assert student.locator('[name=choice_id]').first.is_checked()
    shot(student, 'US06-mobile-answer')
    student.get_by_role('button', name='Review & submit').click()
    confirm(student, 'Submit quiz')
    assert student.get_by_role('heading', name='Quiz submitted', exact=True).is_visible()
    shot(student, 'US08-mobile-submitted')
    # Keep the dashboard stale to exercise closing between listing and starting.
    student.get_by_role('link', name='Back to dashboard', exact=False).click()
    student.wait_for_load_state('networkidle')
    confirm(page, 'Close Quiz')
    student.locator('tr').filter(has_text=title).get_by_role('button').first.click()
    student.wait_for_load_state('networkidle')
    assert "This quiz is closed" in student.inner_text('body')
    shot(student, 'rule-closed-quiz')
    if MODE == 'desktop':
        locked = browser.new_context().new_page()
        locked.goto(BASE)
        for failure in range(5):
            locked.locator('#email').fill('minh.student@example.edu')
            locked.locator('#password').fill('live-check-intentionally-wrong')
            locked.get_by_role('button', name='Sign in', exact=True).click()
            locked.wait_for_load_state('networkidle')
        assert 'Too many failed attempts. Try again in 15 minutes.' in locked.inner_text('body')
        shot(locked, 'rule-fifth-wrong-password')
    browser.close()
