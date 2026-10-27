#!/usr/bin/env python3
"""청렴 CSV 통계 및 정적 페이지 생성. Python 3.10+, pandas."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd

CASE_COLS = ['사건ID','신고일자','신고유형','지역','신고자유형','처리상태','처리기간_일','위반금액_만원','조치결과']
EDU_COLS = ['기관코드','기관명','기관유형','교육이수율','연간교육시간','교육참여자수','청렴우수기관']

def read_csv(path, cols, nums, key):
    for enc in ['utf-8-sig','cp949']:
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f'인코딩 확인 필요: {path}')
    missing = set(cols) - set(df.columns)
    if missing:
        raise ValueError(f'{path}: 필수 열 누락 {sorted(missing)}')
    df = df[cols].copy()
    for col in set(cols)-set(nums):
        df[col] = df[col].astype('string').str.strip().replace('', pd.NA)
    if df[key].isna().any() or df[key].duplicated().any():
        raise ValueError(f'{key}: 누락 또는 중복 식별자')
    for col in nums:
        original = df[col]
        converted = pd.to_numeric(original.astype('string').str.replace(',','',regex=False), errors='coerce')
        if (original.notna() & converted.isna()).any():
            raise ValueError(f'{col}: 숫자 변환 불가 값')
        if ((converted < 0) | (converted.abs() == float('inf'))).any():
            raise ValueError(f'{col}: 음수/무한대 값')
        df[col] = converted.astype(float)
    return df

def records(df):
    return json.loads(df.to_json(orient='records',force_ascii=False))

def mean(s):
    return None if not s.notna().any() else float(s.mean())

def run(cases, education, out, template):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    c = read_csv(cases, CASE_COLS, ['처리기간_일','위반금액_만원'], '사건ID')
    e = read_csv(education, EDU_COLS, ['교육이수율','연간교육시간','교육참여자수'], '기관코드')
    dates = pd.to_datetime(c['신고일자'], format='%Y-%m-%d', errors='coerce')
    if dates.isna().any(): raise ValueError('신고일자: 누락 또는 잘못된 날짜')
    c['신고일자'] = dates.dt.strftime('%Y-%m-%d')
    if (e['교육이수율'] > 100).any(): raise ValueError('교육이수율: 100 초과')
    if not e['청렴우수기관'].isin(['Y','N']).all(): raise ValueError('청렴우수기관은 Y/N 필요')
    summary = {
        '신고사건수':len(c), '신고기간_시작':str(c['신고일자'].min()), '신고기간_종료':str(c['신고일자'].max()),
        '처리완료수':int(c['처리상태'].eq('처리완료').sum()),
        '처리완료비율_pct':float(c['처리상태'].eq('처리완료').mean()*100) if len(c) else None,
        '처리기간_평균_일_전체상태':mean(c['처리기간_일']),
        '처리기간_평균_일_처리완료만':mean(c.loc[c['처리상태'].eq('처리완료'),'처리기간_일']),
        '위반금액_합계_만원':float(c['위반금액_만원'].sum(min_count=1)) if c['위반금액_만원'].notna().any() else None,
        '교육기관수':len(e), '교육이수율_기관단순평균_pct':mean(e['교육이수율']),
        '교육참여자수_기관합계_명':float(e['교육참여자수'].sum(min_count=1)),
        '연간교육시간_기관평균':mean(e['연간교육시간']), '청렴우수기관수':int(e['청렴우수기관'].eq('Y').sum()),
        '결측수':{'사건':{k:int(v) for k,v in c.isna().sum().items()},'교육':{k:int(v) for k,v in e.isna().sum().items()}},
        '산식안내':'평균·합계는 해당 열 결측 제외. 결측을 0으로 대체하지 않음. 이수율은 기관 단순평균이며 전체 인원 이수율 아님. 참여자 합계는 중복인원 제거 불가. 위반금액은 원자료 기재값이며 확정 인정액을 뜻하지 않음.'
    }
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for col in ['신고유형','지역','처리상태','신고자유형','조치결과']:
        g = c.groupby(col,dropna=False).agg(사건수=('사건ID','size'),처리기간_유효수=('처리기간_일','count'),처리기간_평균_일=('처리기간_일','mean'),위반금액_유효수=('위반금액_만원','count'),위반금액_합계_만원=('위반금액_만원',lambda s:s.sum(min_count=1))).reset_index()
        assert int(g['사건수'].sum()) == len(c)
        g.to_csv(out/f'사건_{col}별.csv',index=False,encoding='utf-8-sig')
    monthly = c.assign(신고월=c['신고일자'].str[:7]).groupby('신고월').size().rename('사건수').reset_index()
    assert int(monthly['사건수'].sum()) == len(c)
    monthly.to_csv(out/'사건_월별.csv',index=False,encoding='utf-8-sig')
    e.groupby('기관유형',dropna=False).agg(기관수=('기관코드','size'),이수율_유효기관수=('교육이수율','count'),이수율_기관단순평균=('교육이수율','mean'),참여자수_기관합계=('교육참여자수','sum'),연간교육시간_평균=('연간교육시간','mean')).reset_index().to_csv(out/'교육_기관유형별.csv',index=False,encoding='utf-8-sig')
    quality = pd.concat([c.isna().sum().rename('결측수').reset_index().assign(자료='사건'),e.isna().sum().rename('결측수').reset_index().assign(자료='교육')],ignore_index=True).rename(columns={'index':'열'})
    quality.to_csv(out/'데이터품질.csv',index=False,encoding='utf-8-sig')
    if template:
        payload = json.dumps({'cases':records(c),'education':records(e)},ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
        html = Path(template).read_text(encoding='utf-8').replace('__PAYLOAD__',payload).replace('2026-10-26', datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d'))
        (out/'index.html').write_text(html,encoding='utf-8')
    return summary

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',required=True);p.add_argument('--education',required=True)
    p.add_argument('--out',default='dist');p.add_argument('--template',default=None)
    a=p.parse_args()
    try:
        result=run(a.cases,a.education,a.out,a.template)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:
        p.exit(1,f'오류: {exc}\n')
