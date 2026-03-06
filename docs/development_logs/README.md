# 개발일지 저장소

Stage 종료 시 개발일지를 아래 구조로 저장합니다.

```
docs/development_logs/
  frontend/
    stage-f1-upload-top3/
      DEVLOG.md
  backend/
    stage-b1-core-mock/
      DEVLOG.md
  mlops/
    stage-m1-data-build/
      DEVLOG.md
  pm-devops/
    stage-p1-baseline/
      DEVLOG.md
```

## 생성 방법

```bash
bash docs/develop_rule/scripts/init_stage_devlog.sh \
  --part frontend \
  --stage f1-upload-top3 \
  --owner "홍길동"
```

생성 후 `docs/develop_rule/templates/DEVLOG_TEMPLATE.md` 기준으로 내용을 채웁니다.
