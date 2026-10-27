# 청렴 신고 조회 — Netlify 배포 프로젝트

## 상태
실제 Netlify 배포는 수행하지 않았으며 공개 URL은 없습니다. 계정 연결된 배포 기능이 없어 배포 가능한 프로젝트를 제공합니다. 기능과 RSS의 원격 실행 성공까지 검증한 것은 아닙니다.

## 구성
- public/index.html: 신고 카드, 유형/상태 필터, 검색, ‘결과 N건’, 12건 페이지 이동
- public/data/cases.json: 원본 사건 CSV 500행. 모든 원본 열 유지, 결측은 null
- public/data/education.json: 원본 교육 CSV 120행. 모든 원본 열 유지, 결측은 null
- netlify/functions/rss.mjs: 행안부 공식 보도자료 RSS 고정 URL을 서버에서 호출해 JSON 반환
- netlify.toml: 정적 경로 및 /api/rss 서버리스 경로
- package.json: XML 파서 의존성. 별도 빌드 명령 불필요

## Netlify 배포
1. 공개 승인 및 개인정보/재식별 위험 검토를 먼저 완료합니다. 사건ID, 날짜, 지역 등의 조합도 검토 대상입니다. HTML에 표시하지 않는 열도 JSON에 남습니다.
2. ZIP을 풀고 이 폴더의 파일을 GitHub 저장소 최상위에 업로드합니다. public, netlify 폴더와 package.json, netlify.toml이 같은 최상위에 있어야 합니다.
3. Netlify에서 Add new project → Import an existing project → 해당 Git 저장소를 연결합니다.
4. Base directory는 비움, Build command는 비움, Publish directory는 public. netlify.toml 설정을 사용합니다.
5. Deploy를 실행합니다. Netlify가 의존성을 설치하고 서버리스 함수를 빌드합니다. 완료 후 표시되는 실제 URL로 확인합니다.
6. /api/rss가 HTTP 200으로 JSON을 반환하는지 확인합니다. 페이지에 제목·날짜·링크가 있는 최신 보도자료 10건이 나타나는지 확인합니다. 필터 초기값에서는 최소 5건 이상이어야 합니다.

**단순 정적 폴더 드래그앤드롭은 사용하지 마세요.** 이 프로젝트는 RSS 프록시 함수 빌드가 필요합니다. public 폴더만 올리면 RSS가 작동하지 않습니다. Netlify의 현재 계정별 무료 사용 한도와 함수 지원 조건을 배포 시 확인하세요.

## RSS 정책
공식 RSS 안내 https://www.mois.go.kr/frt/sub/a08/rss/screen.do 에서 확인한 보도자료 피드:
https://www.mois.go.kr/gpms/view/jsp/rss/rss.jsp?ctxCd=1012

브라우저는 동일 출처 /api/rss만 호출하므로 원문 CORS에 의존하지 않습니다. 피드는 서버리스에서 15초 제한으로 조회하고 성공 응답은 최대 10분 캐시합니다. 외부 입력 URL을 받지 않아 임의 프록시로 사용할 수 없습니다. 제목은 textContent로 출력하고 링크는 mois.go.kr 도메인만 허용합니다.

전체 최신 항목 10건이 기본입니다. 일반 보도자료를 청렴 정책이라고 오인하지 않도록 구분했습니다. 청렴·윤리 관련 필터는 제목·설명 키워드를 사용하며 해당 항목이 없으면 사실대로 안내합니다. 전체 보도자료의 과거 검색 기능은 아닙니다. 수신 실패나 유효 항목 5건 미만은 오류로 안내하며 임의 뉴스/날짜/링크로 채우지 않습니다. 정적 RSS 사본은 제공하지 않으며 서버리스 조회에 의존합니다.

## 검수
- 사건 JSON 500행, 교육 JSON 120행, 원본과 결측 수 대조
- title에 청렴/신고 포함, 카드에 신고일자/신고유형/지역/처리상태 표시
- 신고유형/처리상태 복합 필터 및 ‘결과 N건’ 표시 코드 확인
- JavaScript 문법 검사
- 실브라우저 작동 및 배포 후 실제 RSS 파싱/함수 실행은 미검증

## 갱신
원본 CSV를 pandas read_csv 후 to_json(orient='records', force_ascii=False)로 변환해 해당 JSON을 교체하고 Git에 커밋하면 Netlify가 재배포합니다. RSS는 데이터 파일 재배포와 별개로 접속할 때 조회합니다. 비공개 정보는 원본 JSON에서 제거한 뒤 배포하세요.
