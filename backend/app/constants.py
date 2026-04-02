from app.models import TaskType


TASK_RATES: dict[TaskType, int] = {
    TaskType.AIGC_DETECT: 1,
    TaskType.DEDUP: 3,
    TaskType.REWRITE: 2,
}

DEFAULT_BILLING_PACKAGES = [
    {
        "name": "入门包",
        "price": 9.9,
        "credits": 10000,
        "description": "适合单篇检测与初稿优化，低门槛启动。",
        "badge": "新手推荐",
        "enabled": True,
    },
    {
        "name": "标准包",
        "price": 39.0,
        "credits": 50000,
        "description": "适合毕业季高频使用，兼顾成本和处理量。",
        "badge": "运营主推",
        "enabled": True,
    },
    {
        "name": "专业包",
        "price": 128.0,
        "credits": 200000,
        "description": "适合团队批量处理，单位成本更优。",
        "badge": "高性价比",
        "enabled": True,
    },
    {
        "name": "大额包",
        "price": 388.0,
        "credits": 1000000,
        "description": "适合长期运营或机构使用，大额度稳定供给。",
        "badge": "长期使用",
        "enabled": True,
    },
]


PACKAGE_CONFIG = {
    item["name"]: {"price": float(item["price"]), "credits": int(item["credits"])}
    for item in DEFAULT_BILLING_PACKAGES
}


ALLOWED_EXTENSIONS = {".docx", ".pdf", ".txt"}
MAX_FILE_SIZE_MB = 20
