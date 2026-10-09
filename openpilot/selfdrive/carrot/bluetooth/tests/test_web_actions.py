"""The web mapping menu has its own action list; keep it and its labels in sync with the server."""
import re
from pathlib import Path

from openpilot.selfdrive.carrot.bluetooth.model import ACTIONS, REMOTE_BUTTONS

TOOLS = Path(__file__).resolve().parents[2] / 'web' / 'src' / 'features' / 'tools'


def _js_array(source, name):
  match = re.search(rf'export const {name} = \[(.*?)\];', source, re.S)
  assert match, f'{name} not found'
  return match.group(1)


def test_web_menu_offers_exactly_the_server_actions():
  source = (TOOLS / 'bluetooth_mapping.js').read_text(encoding='utf-8')
  buttons = re.findall(r'"([^"]+)"', _js_array(source, 'BUTTON_ACTIONS'))
  assert tuple(buttons) == REMOTE_BUTTONS
  remote = _js_array(source, 'REMOTE_ACTIONS')
  assert '...BUTTON_ACTIONS,' in remote and '...BUTTON_ACTIONS.map(button => `${button}Long`)' in remote
  explicit = re.findall(r'"([^"]+)"', remote)
  assert [explicit[0], *buttons, *(button + 'Long' for button in buttons), *explicit[1:]] == list(ACTIONS)


def test_every_action_has_korean_and_english_labels():
  source = (TOOLS / 'bluetooth.js').read_text(encoding='utf-8')
  ko = source[source.index('  ko: {'):source.index('  en: {')]
  en = source[source.index('  en: {'):]
  for action in ACTIONS:
    key = 'cancelCruise' if action == 'cancel' else action  # actionLabel() relabels the shared "cancel" word
    for words in (ko, en):
      assert re.search(rf'\b{key}: "', words), f'missing label for {action}'
