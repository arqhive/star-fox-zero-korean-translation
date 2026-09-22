# 스타폭스 제로 (Wii U) 한글 패치

*Star Fox Zero* (Wii U, 일본판 `00050000101AFF00`) 비공식 한국어 팬 패치입니다.
대사는 일본어판 원문을 기준으로 번역했습니다.

**제작: arqhive** · **최신 버전: [v1.1](https://github.com/arqhive/star-fox-zero-korean-translation/releases/tag/v1.1)**

- 게임 안의 텍스트 전체를 한글화했습니다(대사 2,000여 개, HUD, 타이틀·일시정지 메뉴, 브리핑, 트레이닝, 엔딩).
- 타이틀 로고의 「スターフォックス ゼロ」와 엔딩 청구서 이미지도 한글로 바꿨습니다.
- 폰트는 원본과 같은 방식(파일별 사전 렌더 글리프 아틀라스)으로 새로 그려 넣습니다.
- 고유명사는 정식 한국어판 『스타폭스 64 3D』·『스타폭스』(Switch 2)의 표기를 따릅니다.

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판 게임(`00050000101AFF00`)에서 덤프한 `content/data003.cpk`. 북미·유럽판에는 적용할 수 없습니다.
- 배포 ZIP에 든 패처. 파이썬이 함께 들어 있어 따로 설치할 필요가 없습니다.

### 적용 방법

1. [배포 페이지](https://github.com/arqhive/star-fox-zero-korean-translation/releases/tag/v1.1)에서 `StarFoxZero_KO_v1.1.zip`을 받아 압축을 풉니다.
2. 원본 `data003.cpk`를 `패치하기.bat` 옆에 두고 `패치하기.bat`를 실행합니다. 30초에서 2분 정도 지나면 `out\data003.cpk`가 만들어집니다.
3. 패처가 원본과 결과 파일의 MD5를 자동으로 검사합니다. 직접 확인하려면 결과 파일의 확인값을 아래 표와 비교합니다.
4. 만들어진 파일을 아래 위치에 넣습니다. 원본 게임 폴더는 고치지 않습니다.
   - 실기(Aroma + SDCafiine): `sd:\wiiu\sdcafiine\00050000101AFF00\StarFoxZero_KR\content\data003.cpk`.
   - Cemu: 그래픽 팩 폴더에 `rules.txt`(`titleIds = 00050000101AFF00`)와 `content\data003.cpk`를 두고 팩을 켭니다.

`패치하기.bat --sd E:`처럼 SD 카드 드라이브를 주면 SDCafiine 경로까지 복사합니다.

자세한 방법은 [`README_한국어.txt`](release/README_한국어.txt)를 참고하세요.

### 파일 확인값

| 항목 | 원본 일본판 `data003.cpk` | 패치 적용 결과 (v1.1) |
|---|---|---|
| 크기 | 815,910,328 바이트 | 890,469,816 바이트 |
| CRC32 | `1DF78828` | `33F67B69` |
| MD5 | `7450ce09efac2f405f0a36fe784d44a1` | `8e5ec4d4e4abe41dbb2a16aa456bbe6c` |
| SHA-1 | `9dfa60ddbb9b0e1ebcc313eae6ca081244c312b1` | `5c6f88d641b52ebded3d3fd2a56d28eed03d4413` |

원본 파일명 예: `content/data003.cpk`

### 실행 환경

- **확인함**: Cemu, Wii U + Aroma SDCafiine.

### 알려진 문제

- 음성은 일본어 그대로입니다.
- 스테이지 간판 등 게임 세계관 속 영어 표기(`CORNERIA PRECIOUS METALS LTD.`)는 그대로 두었습니다.
- 아케이드·챌린지 등 일부 화면은 충분히 플레이하며 확인하지 못했습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.11 이상, numpy, Pillow(`pip install -r requirements.txt`).
- 일본판에서 덤프한 원본 `data003.cpk`.
- 폰트는 [`tools/fonts/`](tools/fonts/)에 들어 있습니다(Noto Sans KR, 나눔손글씨 펜).

### 빌드

```bash
pip install -r requirements.txt
python tools/patch.py <원본 data003.cpk> -o out
```

### 배포본 만들기

```bash
python tools/patch.py <원본 data003.cpk> -o out
python tools/make_release.py <원본 data003.cpk> --version v1.1
```

`make_release.py`는 원본과 빌드 결과를 비교해 바뀐 파일만 `release/patcher/payload`에 담고 ZIP을 만듭니다. 글자 아틀라스와 MCD는 통째로, 그림 텍스처는 달라진 4KB 블록만 담습니다.
`release/python`에 [python.org embeddable](https://www.python.org/downloads/windows/)을 풀어 두면 함께 담깁니다.
받는 쪽은 numpy·Pillow·폰트 없이 표준 라이브러리만으로 패치를 적용합니다.

v1.1 그래픽 개선판의 변경 내용과 기존 v1.0 완성본에서 다시 만드는 방법은 [`docs/GRAPHICS_UPDATE.md`](docs/GRAPHICS_UPDATE.md)에 있습니다.

### 번역 수정

- `translation/text/*.json`의 `ko` 항목을 고칩니다. 표기 규칙은 [`translation/glossary.md`](translation/glossary.md)(용어·말투)와 [`translation/punct_rules.md`](translation/punct_rules.md)(구두점·문체)에 있습니다.
- 텍스트 표기는 `\n` 줄바꿈, `{I숫자}` 버튼 아이콘, `{G0}`와 `{/G0}` 아이콘 묶음, `{{` `}}` 중괄호 문자입니다.
- `python tools/lint.py`로 태그 손상, 일본어 잔존, 줄 폭·줄 수 초과를 검사합니다.
- 고친 뒤 `python tools/patch.py ...`로 다시 빌드합니다.
- 플레이하며 검수하는 순서는 [`docs/REVIEW_GUIDE.md`](docs/REVIEW_GUIDE.md)에 정리했습니다.

### 폴더 구조

```
tools/               패치 빌더와 포맷 도구(CPK·DAT·MCD·GX2 텍스처), 번들 폰트
translation/text/    번역 JSON 29개(원문 ja와 번역 ko)
translation/*.md     용어집, 구두점·문체 규칙
docs/                기술 문서, 릴리즈 노트 사본(docs/releases/)
release/             배포용 패처(표준 라이브러리만 사용)와 사용자 설명서
work/                원본에서 뽑은 작업 파일(커밋하지 않음)
```

### 기술 문서

파일 포맷과 패치 방식은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드: [MIT License](LICENSE) (© 2026 arqhive).
- 한국어 번역문: CC BY-NC-SA 4.0.
- 번들 폰트(Noto Sans KR, 나눔손글씨 펜): SIL Open Font License 1.1 ([`tools/fonts/OFL.txt`](tools/fonts/OFL.txt)).
- `tools/addrlib.py`는 [aboood40091/BFRES-Tool](https://github.com/aboood40091/BFRES-Tool)의 Wii U 텍스처 주소 계산 코드입니다(GPLv3).

## 면책

비공식 팬 번역이며 Nintendo와 관련이 없습니다. 「스타폭스」 관련 상표·저작권은 Nintendo에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
