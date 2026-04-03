# Aliyun ECS Deployment (Simple)

First deploy and later updates use the same command:

```bash
curl -fsSL https://raw.githubusercontent.com/M-houres/gewuxueshu/main/scripts/deploy_aliyun.sh | sudo bash
```

If code is already on server:

```bash
sudo bash /opt/gewuxueshu/scripts/deploy_aliyun.sh
```

Notes:

- This script targets Ubuntu/Debian.
- Default deploy directory: `/opt/gewuxueshu`.
- Open inbound port `80` in Alibaba Cloud security group.
