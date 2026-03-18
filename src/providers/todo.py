"""TODO list providers for fetching tasks from various sources.

Supports multiple TODO sources including Gist, Notion, Google Sheets,
and local configuration. Falls back to config if external sources fail.
"""

import logging

import httpx

from ..config import Config

logger = logging.getLogger(__name__)


async def get_todo_lists() -> tuple[list[str], list[str], list[str]]:
    """
    获取 TODO 列表（根据配置的数据源）

    Returns:
        (goals, must, optional) 三个列表
    """
    source = Config.todo.source.lower()

    try:
        match source:
            case "gist":
                return await get_todo_from_gist()
            case "notion":
                return await get_todo_from_notion()
            case "sheets":
                return await get_todo_from_sheets()
            case _:
                return get_todo_from_config()
    except Exception as e:
        logger.error(f"Failed to fetch TODO from {source}: {e}, using config")
        return get_todo_from_config()


def get_todo_from_config() -> tuple[list[str], list[str], list[str]]:
    """从配置文件获取 TODO 列表（默认/回退方案）"""
    return (
        Config.todo.list_goals,
        Config.todo.list_must,
        Config.todo.list_optional,
    )


async def get_todo_from_gist() -> tuple[list[str], list[str], list[str]]:
    """
    从 GitHub Gist 获取 TODO 列表

    Gist 格式:
    ```markdown
    ## Goals
    - Item 1
    - Item 2

    ## Must
    - Item 1

    ## Optional
    - Item 1
    ```
    """
    if not Config.todo.gist_id or not Config.github.token:
        logger.warning("Gist ID or GitHub token not configured")
        return get_todo_from_config()

    url = f"https://api.github.com/gists/{Config.todo.gist_id}"
    headers = {"Authorization": f"token {Config.github.token}"}

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        limits=httpx.Limits(max_connections=2, max_keepalive_connections=0),
    ) as client:
        try:
            res = await client.get(url, headers=headers, timeout=10)
            res.raise_for_status()

            logger.info(f"✅ Successfully fetched gist {Config.todo.gist_id}")

            data = res.json()
            # 查找 todo.md 或第一个 .md 文件
            files = data.get("files", {})
            logger.info(f"📁 Files in gist: {list(files.keys())}")
            content = None

            if "todo.md" in files:
                content = files["todo.md"]["content"]
                logger.info(f"📄 Found todo.md, content length: {len(content)} chars")
            else:
                # 使用第一个 markdown 文件
                for filename, file_data in files.items():
                    if filename.endswith(".md"):
                        content = file_data["content"]
                        logger.info(f"📄 Using {filename}, content length: {len(content)} chars")
                        break

            if content:
                result = parse_markdown_todo(content)
                logger.info(
                    f"✅ Parsed TODO from gist: {len(result[0])} goals, {len(result[1])} must, {len(result[2])} optional"
                )
                return result
            else:
                logger.warning("⚠️ No markdown file found in gist, falling back to config")
                return get_todo_from_config()

        except Exception as e:
            logger.error(f"❌ Failed to fetch gist: {e}")
            raise


async def get_todo_from_notion() -> tuple[list[str], list[str], list[str]]:
    """
    从 Notion Database 获取 TODO 列表

    Database 结构:
    - Name (title): TODO 项目名称
    - Category (select): Goals / Must / Optional
    - Status (select): Active / Done (只获取 Active)
    """
    if not Config.todo.notion_token or not Config.todo.notion_database_id:
        logger.warning("Notion token or database ID not configured")
        return get_todo_from_config()

    try:
        from notion_client import Client
    except ImportError:
        logger.error("notion-client not installed. Run: pip install notion-client")
        return get_todo_from_config()

    notion = Client(auth=Config.todo.notion_token)

    try:
        # 查询数据库，只获取 Active 状态的项目
        response = notion.databases.query(
            database_id=Config.todo.notion_database_id,
            filter={"property": "Status", "select": {"equals": "Active"}},
        )

        goals, must, optional = [], [], []

        for page in response.get("results", []):
            # 获取标题
            title_prop = page["properties"].get("Name", {})
            if title_prop.get("title"):
                name = title_prop["title"][0]["plain_text"]
            else:
                continue

            # 获取分类
            category_prop = page["properties"].get("Category", {})
            if category_prop.get("select"):
                category = category_prop["select"]["name"]
            else:
                category = "Optional"  # 默认分类

            # 分配到对应列表
            match category:
                case "Goals":
                    goals.append(name)
                case "Must":
                    must.append(name)
                case "Optional":
                    optional.append(name)

        logger.info(
            f"Fetched from Notion: {len(goals)} goals, {len(must)} must, {len(optional)} optional"
        )
        return goals, must, optional

    except Exception as e:
        logger.error(f"Failed to fetch from Notion: {e}")
        raise


async def get_todo_from_sheets() -> tuple[list[str], list[str], list[str]]:
    """
    从 Google Sheets 获取 TODO 列表

    表格结构:
    | Goals | Must | Optional |
    |-------|------|----------|
    | Item1 | Item1| Item1    |
    | Item2 | Item2| Item2    |
    """
    if not Config.todo.google_sheets_id:
        logger.warning("Google Sheets ID not configured")
        return get_todo_from_config()

    try:
        import gspread
    except ImportError:
        logger.error("gspread not installed. Run: pip install gspread")
        return get_todo_from_config()

    try:
        # 使用 service account 认证
        gc = gspread.service_account(filename=Config.todo.google_credentials_file)
        sheet = gc.open_by_key(Config.todo.google_sheets_id).sheet1

        # 读取三列数据（跳过标题行）
        all_values = sheet.get_all_values()

        if len(all_values) < 2:
            logger.warning("Sheet is empty or has no data rows")
            return get_todo_from_config()

        # 跳过第一行（标题）
        data_rows = all_values[1:]

        goals = [row[0] for row in data_rows if len(row) > 0 and row[0].strip()]
        must = [row[1] for row in data_rows if len(row) > 1 and row[1].strip()]
        optional = [row[2] for row in data_rows if len(row) > 2 and row[2].strip()]

        logger.info(
            f"Fetched from Sheets: {len(goals)} goals, {len(must)} must, {len(optional)} optional"
        )
        return goals, must, optional

    except Exception as e:
        logger.error(f"Failed to fetch from Google Sheets: {e}")
        raise


def parse_markdown_todo(content: str) -> tuple[list[str], list[str], list[str]]:
    """
    解析 Markdown 格式的 TODO 列表

    支持格式:
    1. 简单列表:
       ## Goals
       - Item 1
       - Item 2

    2. GitHub 任务列表:
       ## Must
       - [ ] Item 1
       - [x] Item 2

    3. 混合格式:
       ## Optional
       * Item 1
       - [ ] Item 2
    """
    logger.debug(f"Parsing markdown content (first 200 chars): {content[:200]}")

    goals, must, optional = [], [], []
    current_section = None

    for line in content.split("\n"):
        line = line.strip()
        line_lower = line.lower()

        # 检测章节标题（不区分大小写，支持常见拼写变体）
        # 使用 'in' 而不是 'startswith' 来更灵活地匹配
        if (line_lower.startswith("##") or line_lower.startswith("#")) and "goal" in line_lower:
            current_section = "goals"
            logger.debug(f"Found Goals section: {line}")
        elif (line_lower.startswith("##") or line_lower.startswith("#")) and "must" in line_lower:
            current_section = "must"
            logger.debug(f"Found Must section: {line}")
        elif (line_lower.startswith("##") or line_lower.startswith("#")) and "opt" in line_lower:
            # 匹配 "optional", "optinal", "option" 等变体
            current_section = "optional"
            logger.debug(f"Found Optional section: {line}")
        # 检测列表项（支持简单列表和任务列表）
        elif line.startswith("- ") or line.startswith("* "):
            # 移除列表标记
            item = line[2:].strip()

            # 检查是否是任务列表格式并标记完成状态
            is_completed = False
            if item.startswith("[ ]"):
                item = item[3:].strip()
            elif item.startswith("[x]") or item.startswith("[X]"):
                item = item[3:].strip()
                is_completed = True

            if not item:
                continue

            # 如果已完成，添加特殊标记前缀
            if is_completed:
                item = "✓" + item

            match current_section:
                case "goals":
                    goals.append(item)
                    logger.debug(f"  Added to goals: {item}")
                case "must":
                    must.append(item)
                    logger.debug(f"  Added to must: {item}")
                case "optional":
                    optional.append(item)
                    logger.debug(f"  Added to optional: {item}")

    logger.debug(f"Parsed result: {len(goals)} goals, {len(must)} must, {len(optional)} optional")
    return goals, must, optional
