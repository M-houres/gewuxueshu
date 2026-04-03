# Aliyun ECS Deployment

One command for first deploy and updates:

```bash
curl -fsSL https://raw.githubusercontent.com/M-houres/gewuxueshu/main/scripts/deploy_aliyun.sh | bash
```

If repo is already cloned:

```bash
bash scripts/deploy_aliyun.sh
```

Optional variables:

```bash
INITIAL_CREDITS=2000 BRANCH=main APP_DIR=/opt/wuhongai bash scripts/deploy_aliyun.sh
```

Compatibility scripts:

```bash
bash scripts/deploy_aliyun_first.sh
bash scripts/deploy_aliyun_update.sh
```

Notes:

- Open inbound port `80` in Alibaba Cloud security group.
- If using HTTPS, also open `443`.
- Main runtime config file on server: `/opt/wuhongai/.env.prod`.
