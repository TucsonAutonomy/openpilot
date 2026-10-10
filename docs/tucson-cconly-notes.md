# 투싼 CC 온리 작업 메모

TucsonAutonomy/openpilot 포크에서 2017 투싼 디젤(CC 온리)용으로 작업한 내용을 정리한 메모입니다.
새 세션을 시작하거나 아주아톰의 새 버전을 이식할 때 이 파일을 먼저 읽어 주세요.

## 1. 차량과 장치

- 차량: 2017 현대 투싼 디젤. SCC와 레이더가 없는 CC 온리 차량입니다(순정 크루즈만 있음).
  오토홀드와 EPB가 있고, SMDPS가 개조되어 있으며, LFA 버튼은 없습니다.
- 장치: comma 3X, AGNOS `19.8-carrot-bt1`
- 기기 주소: 집 와이파이 `192.168.1.40`, 테더링 중에는 `192.168.43.1`. SSH 사용자는 `comma`입니다.
- 필수 설정: 캐롯 웹 → 설정 → 현대·기아 → **HYUNDAI: CC ONLY CAR = 1** (`HyundaiCcOnly`)
- LTE 유심: KT, APN `lte.ktfwing.com`
- 블루투스 리모컨: 샤오미 XMRM-002(시험용). 왼쪽(`key:105`)은 왼쪽 차로변경, 오른쪽(`key:106`)은 오른쪽 차로변경으로 지정했습니다.
  크루즈 취소/재개, 현재 속도로 크루즈 시작도 다른 버튼에 지정해 씁니다(9절).

## 2. 작업 규칙 (사용자 요청)

- **"수정해 / 구현해 / 진행해 / 실행해"라고 할 때만** 코드를 수정합니다. 질문이나 "검토만 해"라고 하면 검토만 합니다.
- 새 커밋을 만들면 **커밋 번호를 항상** 알려 드립니다.
- 푸시하기 전에 **어느 저장소, 어느 브랜치로 올리는지** 먼저 알리고, **"푸시해"라고 할 때만** 푸시합니다.
- 한국어 존댓말로 답하고, 영어 표현은 되도록 쓰지 않습니다.
- SSH 명령은 **한 블록에 한 줄씩** 드립니다(복사해서 붙여 넣기 쉽게).
- 새로 추가하는 토글의 기본값은 **꺼짐**입니다. 사용자가 바꾼 설정값은 건드리지 않습니다.
- 기능 동작을 설명할 때는 기억에 기대지 말고 **먼저 코드를 확인**한 뒤 답합니다.
- `claude/sweet-gates-Hc9md-carrot` 브랜치는 아직 지우지 않습니다.
- `c3-wip` 브랜치는 **지우지 않습니다.** 클라우드 세션을 시작할 때 필요합니다(아래 7절 참고).

## 3. 브랜치

| 브랜치 | 위치 | 설명 |
|---|---|---|
| `carrot-cconly2-remote` | 최신 | **현재 사용 중.** `carrot-cconly2` 위에 리모컨 크루즈 기능(9절)을 더한 시험용 브랜치 |
| `carrot-cconly2` | `6b3ef2cd` | 아주아톰 `carrot-wip`(`209b3c0c`) 위에 기능을 이식한 브랜치. 리모컨 크루즈 기능 전 상태 |
| `carrot-cconly` | `d74c5456` | 예전 carrot-wip 기준으로 만든 브랜치. 차에서 확인 완료, 되돌릴 때 사용 |
| `carrot-wip` | `209b3c0c` | 아주아톰 원본을 Sync fork로 받아 둔 것 |
| `c3-wip` | `de7bd742` | 클라우드 세션 시작용 이름표. 지우지 말 것 |
| `claude/sweet-gates-Hc9md-carrot`, `rollback-0909` | - | 예전 작업 보관용 |

## 4. 이식 목록 (`carrot-wip` 위에 얹은 커밋)

새 버전으로 이식할 때 아래 커밋을 **순서대로** 다시 적용합니다.

| 커밋 | 내용 |
|---|---|
| `76c1be63` | CC 온리(조향만) 지원. `HyundaiCcOnly` → `CC_ONLY_CAR` 플래그, 판다 안전 코드에서 SCC12(0x421) 수신 검사 제외(`CC_ONLY = 1024`) |
| `4ffb0722` | CC 온리 오토홀드와 순정 크루즈 표시등 알림(소리, `cruiseLampOn`) |
| `bd5f9bc4` | ATC(좌·우회전, 진출, 차로변경) 음성 안내 |
| `1cf2160e` | 깜빡이 도중 ATC 종류가 바뀌면 다시 안내 |
| `92351d25` | CC 온리 내연기관 차의 타이어 공기압(TPMS) 읽기 |
| `2c0f0c61` | ATC 안내 소리를 한 번만 재생 |
| `b7a664db` | CRUISE 버튼만으로 조향 켜기·끄기. RES+/SET−로는 조향을 켜지 않음 |
| `cf05ff30` | 깜빡이 막대 점멸, ATC가 요청한 방향 표시 |
| `2bb66b8d` | 설치 프로그램(installer) 내장 파일 이름 오류 수정 |
| `abd4d0a0` | 타이어 공기압 글자 크게 |
| `de7bd742` | 초록 테두리를 조향이 "켜졌을 때" 기준으로 표시 |
| `e6421d7b` | 블루투스 리모컨: 가속 페달을 밟고 있어도 차로변경 버튼 허용 |
| `2ae7b518` | 블루투스 리모컨: 브레이크를 밟고 있어도 차로변경 버튼 허용 |
| `f9c5e2ad` | 등록 안 된 기기에서도 APN 메뉴 표시, 테더링 인터넷 넘겨주기와 `iptables-legacy` NAT 자동 설정 |
| `a01ae3f5` | 모뎀: 설정한 APN을 2번 통로로 연결(재부팅 후 KT LTE 연결 실패 해결) |

리모컨 크루즈 기능(`carrot-cconly2-remote` 브랜치). 위 커밋 다음에 순서대로 적용합니다.

| 커밋 | 내용 |
|---|---|
| `98136ea5` | 리모컨 "크루즈 취소"를 CC 온리에서 CLU11 CANCEL로 보냄. 판다는 순정 크루즈 램프(EMS16 `CRUISE_LAMP_S`)가 켜져 있을 때만 CANCEL 허용 |
| `8867a8ea` | 시험 코드만 수정: 크루즈 버튼 시험 도우미에 CC 온리 값 추가(`b7a664db` 뒤로 실패하던 시험) |
| `223a944c` | 리모컨 동작 "크루즈 취소/재개 (CC 온리)" 추가 |
| `6c8d9593` | 웹 매핑 메뉴에 취소/재개가 보이지 않던 문제 수정 |
| `c9ab3164` | 리모컨 동작 "현재 속도로 크루즈 시작 (CC 온리)" 추가 |
| `fd3644c9` | 가속 페달을 밟고 있어도 두 CC 온리 크루즈 버튼 허용 |
| `5dffe3ba` | SET을 최대 1초까지 누름(차가 SET에 0.1~0.6초 걸림), SET 뒤 3초 동안 결과 기록 |
| `9a14c975` | 쓸기(터치) 동작으로 들어오는 버튼도 페달을 밟는 동안 손을 뗄 때까지 살려 둠 |

이식할 때 주의할 점:

- 겹치기 쉬운 파일: `cruise.py`(크루즈 버튼), `car.capnp`(항목 번호), `log.capnp`(이벤트 번호).
  carrot-cconly2를 만들 때 아주아톰이 `radarInput @93`를 추가해서 `cruiseLampOn`을 `@94`로 옮겼습니다.
- 리모컨 기능에서 겹치기 쉬운 파일: 현대 `carcontroller.py`, `safety_hyundai.h`, `bluetooth/model.py`, `bluetooth/daemon.py`,
  웹 `bluetooth_mapping.js`·`bluetooth.js`. 웹 파일을 고치면 `openpilot/selfdrive/carrot/web`에서 `node build.mjs`로 다시 묶고,
  생성 파일(`js/generated/tools.js`, `generated/asset-manifest.json`)도 함께 커밋합니다.
  서버의 동작 목록(`model.py`의 `ACTIONS`)과 웹 메뉴 목록(`REMOTE_ACTIONS`)이 같아야 합니다(`test_web_actions.py`가 확인).
- 겹치는 부분을 손으로 정리한 뒤, 파이썬 컴파일과 판다 안전 코드 빌드를 확인합니다.
- 차에서는 조향(1순위)부터 다시 확인합니다.

## 5. 주요 동작

- **CRUISE 버튼(메인)**: 조향 켜기·끄기. 켜지면 화면에 **초록 테두리**가 생깁니다.
- **SET**: 순정 크루즈가 작동하면 화면에 **초록 점**이 생기고 소리가 납니다(`cruiseLampOn`).
  CRUISE만 켠 상태에서는 초록 테두리만 있고 초록 점은 없습니다.
- **CANCEL**: 순정 크루즈만 해제합니다. 조향은 유지합니다.
- **블루투스 리모컨 차로변경 조건**: 조향 작동 중(초록 테두리), 차로변경 가능 속도 이상, 기어 D.
  SET(초록 점)은 필요 없습니다. 가속·브레이크 페달을 밟고 있어도 차로변경 버튼은 받아들입니다.
- **페달을 밟는 동안 리모컨**: 차로변경은 두 페달 모두 허용합니다. 가속 페달만 밟을 때는 CC 온리 크루즈 버튼
  (취소/재개, 현재 속도로 시작)도 허용합니다. 짧게·두 번 누르기(터치·쓸기 동작 포함)만 해당하고,
  길게 누르기와 그 밖의 버튼은 막힙니다.
- 시동이 꺼져 있으면 리모컨 입력은 의도적으로 버려집니다. 집에서 버튼이 안 찍히는 것은 정상입니다.
- 빨간 **전원 버튼**이 있는 리모컨은 그 버튼을 누르지 않습니다(기기가 꺼질 수 있음).

## 6. 설치와 되돌리기

같은 브랜치의 작은 수정(파이썬만 바뀜):

- 캐롯 웹 → 도구 → **git pull** → **Reboot**, 또는 기기 화면 → 설정 → 소프트웨어 → **설치**
- 또는 SSH:

```
cd /data/openpilot && git pull && sudo reboot
```

다른 브랜치로 옮길 때(빌드 필요). 아래 명령을 한 줄씩 실행합니다:

```
tmux kill-session -t comma
```
```
cd /data/openpilot && git config --replace-all remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
```
```
git fetch origin carrot-cconly2 && git checkout -B carrot-cconly2 origin/carrot-cconly2
```
```
sudo reboot
```

- 재부팅하면 시작 스크립트가 AGNOS 업데이트, 부품(wheel) 설치, 빌드를 차례로 자동으로 합니다.
  손으로 `scons`를 먼저 돌리면 부품이 없어 `catch2` 등 오류가 납니다.
- 특정 커밋으로 되돌리기(SSH):

```
cd /data/openpilot && git reset --hard <커밋번호> && sudo reboot
```

- 리모컨 시험 브랜치로 옮길 때는 위 명령의 `carrot-cconly2`를 `carrot-cconly2-remote`로 바꿉니다.
- 리모컨 기능 이전 코드로 되돌리기 전에, 새 동작(크루즈 취소/재개, 현재 속도로 크루즈 시작)에 지정한 버튼을 먼저 "없음"으로 바꿉니다.
  예전 코드는 모르는 동작이 하나라도 있으면 리모컨 매핑 전체를 받아들이지 않습니다.
- 캐롯 웹의 빨간 글씨 버튼(git reset, reset repo, Reset Calib, delete all …, Rebuild All)은 되돌리기 어려운 동작입니다.
- 완전히 새로 설치해야 하면 flash.comma.ai로 다시 굽고, 설치 주소에 `TucsonAutonomy/carrot-cconly2`를 넣습니다.

## 7. 클라우드 세션 참고

- 이 작업은 Claude Code 클라우드 세션에서 했습니다. 세션은 **`c3-wip` 브랜치로 시작**하도록 기록되어 있습니다.
  이 브랜치가 없으면 세션이 "브랜치를 찾을 수 없음"으로 시작되지 않습니다. 그래서 `c3-wip`을 지우면 안 됩니다.
- "세션을 시작하지 못했습니다"가 뜨면 세션을 **보관했다가 보관 해제**하면 다시 시작된 적이 있습니다.
- 대화가 길어지면 앞부분이 요약(압축)되어 세부 내용이 줄어듭니다. 중요한 내용은 이 파일에 남깁니다.

## 8. LTE와 테더링 문제 해결

- 테더링 이름: `weedle-` + 동글 ID 앞 4글자, 기본 비밀번호 `swagswagcomma`, 기기 주소 `192.168.43.1`
- 인터넷이 없어도 맥을 테더링에 연결하면 SSH 접속이 됩니다(주소 `192.168.43.1`).
- 이 버전은 LTE를 `wwan0`이 아니라 **`ppp0`**으로 연결합니다(`modem.py`). `nmcli`에는 나오지 않습니다.

확인 명령:

```
grep -E '"state"|"connected"|"ip_address"' /dev/shm/modem
```
```
tmux capture-pane -pt comma -S -5000 | grep "modem:" | tail -15
```
```
ping -c 3 -I ppp0 8.8.8.8
```
```
cat /proc/sys/net/ipv4/ip_forward
```
```
sudo iptables-legacy -t nat -S POSTROUTING
```
```
sudo journalctl -t pppd -n 40 --no-pager
```

지금까지 찾은 원인과 해결:

| 증상 | 원인 | 해결 |
|---|---|---|
| APN 메뉴가 없음, 테더링 인터넷 안 됨 | 기기가 comma connect에 등록되지 않아(`PrimeType -1`) 셀룰러 메뉴와 인터넷 넘겨주기가 꺼짐 | `f9c5e2ad` |
| 테더링은 연결되는데 인터넷만 안 됨 | 커널 4.9가 nftables NAT를 지원하지 않음 | `f9c5e2ad`(`iptables-legacy`로 NAT 자동 추가) |
| 재부팅 후 `PPP fail 1/3…` 반복 | LTE 기본 통로와 PPP가 같은 APN을 쓰면 KT가 인증 직후 끊음 | `a01ae3f5`(설정 APN은 2번 통로로 연결) |

- APN이 비어 있으면 KT 데이터가 연결되지 않습니다. `lte.ktfwing.com`을 넣어야 합니다.
- 업데이트 직후 첫 부팅은 모뎀에 예전 APN이 남아 한 번 실패할 수 있습니다. 두 번째 부팅부터 확인합니다.

## 9. 블루투스 리모컨

- 캐롯은 `/dev/input/event*`(블루투스 HID 입력 장치)만 읽습니다. 마우스 버튼(272~274)은 받지 않습니다.
- 확인된 결과:
  - 샤오미 XMRM-002: 됨. 웹 화면 짝짓기가 `AuthenticationFailed`로 실패하면 SSH로 `agent NoInputNoOutput`을 쓰고 "yes"를 자동으로 답하게 해서 짝지었습니다.
  - 애플 Siri 리모컨(1세대): 연결은 되지만 애플 전용 신호라 버튼이 오지 않습니다. 사용 불가.
  - 로지텍 페블 마우스: 버튼 번호가 캐롯이 받지 않는 범위라 사용 불가.
  - 데논 RC-1202: 적외선 리모컨이라 사용 불가.
- 버튼 하나짜리 셀카 셔터 리모컨(AB Shutter3 계열) 두 개를 핸들 양쪽에 붙여 왼쪽·오른쪽 차로변경에 쓰는 것이 목표입니다.
  매핑은 리모컨(주소)마다 따로 저장되어 두 개를 동시에 쓸 수 있습니다.
- 짝짓기 확인:

```
grep -A6 "Bus=0005" /proc/bus/input/devices
```

### 리모컨 크루즈 버튼 (CC 온리, `carrot-cconly2-remote`)

| 매핑 메뉴 이름 | 동작 |
|---|---|
| 크루즈 취소 | 초록 점이 있을 때 CANCEL. 개발자가 만든 기능을 CC 온리에서도 동작하게 함 |
| 크루즈 취소/재개 (CC 온리) | 초록 점이 있으면 CANCEL, 없으면 RES(직전 설정 속도로 재개) |
| 현재 속도로 크루즈 시작 (CC 온리) | 초록 점이 없을 때 SET(현재 속도로 시작). 초록 점이 있으면 아무 동작도 하지 않음(설정 속도를 바꾸지 않음) |

- 조건: 초록 테두리(CRUISE 메인) 켜짐, 기어 D, 핸들 버튼을 누르는 중이 아닐 것.
- 크루즈가 꺼진 뒤, 그리고 브레이크·오토홀드·주차 브레이크를 푼 뒤 2초 동안은 재개와 시작이 막힙니다.
- 브레이크를 밟으면 보내던 버튼도 바로 멈춥니다.
- 오픈파일럿이 핸들 버튼처럼 CLU11 신호를 보냅니다. CANCEL·RES는 0.3초, SET은 최대 1초 동안 보내고, 초록 점이 바뀌면 바로 멈춥니다.
  실측 반응 시간: CANCEL·RES 약 0.1초, SET 0.1~0.6초(0.3초를 넘을 때가 많음).
- 판다 허용 조건: CANCEL은 순정 크루즈 램프가 켜져 있을 때, RES는 항상, SET은 제어 허용일 때입니다.
  CC 온리에서는 오픈파일럿이 보내는 SCC12(`ACCMode=1`, CRUISE 메인 켜짐)가 제어 허용을 계속 켜 줍니다.
- CC 온리에서는 "크루즈 +/−", "패들 감속"을 리모컨에 지정하지 않습니다. RES 신호가 나가 순정 크루즈가 재개될 수 있습니다.
- "현재 속도로 크루즈 시작"에 지정한 버튼은 쓸기 동작(`swipe:y+`)으로 들어옵니다. 쓸기 동작은 처음에 톡 누름(tap)으로
  시작해서 움직인 뒤 쓸기로 바뀝니다. 이 때문에 페달을 밟는 동안 취소되던 문제를 `9a14c975`에서 고쳤습니다.

가속 페달을 밟으면 "현재 속도로 크루즈 시작"이 안 되던 문제는 원인이 두 가지였습니다.

1. 쓸기 동작이 페달을 밟는 동안 tap 단계에서 취소되어 신호가 차까지 가지 못함 → `9a14c975`
2. 차가 SET을 받아들이는 데 0.3초보다 오래 걸릴 때가 많음 → `5dffe3ba`

판다는 원인이 아니었습니다. P단에서 가속 페달을 밟아도 EMS16 체크섬이 정상이었고 제어 허용도 유지되었습니다.

확인 명령(한 줄씩 실행). 차량 제어 기록:

```
tmux capture-pane -pt comma -S -20000 | grep "cc_only" | tail -20
```

리모컨 입력 기록(최근 10개):

```
python3 -c "import json;d=json.load(open('/dev/shm/carrot-bluetooth/status.json'));[print(e['button'],e['action'],e['reason']) for e in d.get('recent_events',[])[-10:]]"
```

판다 상태(두 줄을 차례로 실행):

```
cd /data/openpilot
```
```
python3 -c "from openpilot.cereal import messaging as m;sm=m.SubMaster(['pandaStates']);sm.update(1000);p=sm['pandaStates'];print('allowed',int(p[0].controlsAllowed),'txBlocked',p[0].safetyTxBlocked) if len(p) else print('no pandaStates')"
```

기록 읽는 법:

| 기록 | 뜻 |
|---|---|
| `remote ...: sending CLU11 ...` | 버튼 신호를 보내기 시작함 |
| `factory cruise on/off after N frames of ...` | N×0.01초 만에 초록 점이 바뀜(성공) |
| `... window ended with factory cruise still ...` | 끝까지 보냈지만 초록 점이 바뀌지 않음 |
| `remote ... blocked: cruise off for only ...` | 2초 대기 중이라 보내지 않음 |
| `remote set ignored: factory cruise already engaged` | 이미 크루즈 작동 중이라 SET을 보내지 않음 |
| `factory cruise on / still off ... after the SET press ended` | SET을 다 보낸 뒤 3초 동안 지켜본 결과 |
| `remote press aborted by brake` | 브레이크로 보내던 버튼을 멈춤 |

- 리모컨 입력 기록의 끝이 `sent`면 통과, `inactive`면 막힌 것입니다. 페달 때문에 취소된 누름은 기록에 남지 않습니다.
- `txBlocked`는 판다가 막은 신호 수입니다. 취소할 때 램프가 꺼지는 순간 남은 CANCEL 몇 개가 막힐 수 있는데, 정상입니다.

## 10. 보류한 작업

- 부팅 시 테더링 자동 켜기: 이미 있는 `HotspotOnBoot` 설정(캐롯 웹 "부팅시 핫스팟켜기")을 실제로 동작하게 연결.
  계획은 `wifi_manager.py` 초기화 때 값이 1이면 테더링을 켜고, 저장된 `PrimeType`으로 인터넷 넘겨주기를 판단하는 것입니다.
- 셔터 리모컨 두 개 짝짓기와 매핑
- 리모컨 크루즈 취소가 가끔 안 되는 현상: 아직 재현 못 함. 다시 생기면 바로 차량 제어 기록을 확인합니다.
  의심되는 원인은 리모컨 신호가 계기판 신호와 섞이고 메시지 번호가 계기판 번호와 이어지지 않는 것입니다.
  필요하면 번호를 계기판 다음 번호로 맞춰 보내는 방법(개발자의 `create_clu11_button` 방식)을 시험합니다.
- 시험 브랜치 `carrot-cconly2-remote`를 `carrot-cconly2`에 합치기
- (선택) CC 온리에서 리모컨 "크루즈 +/−", "패들 감속"이 아무 동작도 하지 않게 막기
- (선택) CC 온리 판단(`HyundaiCcOnly`)에 현대·기아 차종인지 확인 추가
- 우회전 보조(turn assist) 이식: 우회전 ATC가 잘 안 되는 문제 해결용
- 저속 조향 제한(`MAX_CURVATURE`) 완화
- ATC 안내 시점 조정, 좌·우 방향 음성 파일(녹음 파일 필요)
