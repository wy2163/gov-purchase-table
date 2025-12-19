import pandas as pd
from datetime import datetime
from pathlib import Path
import json

# ========== 核心配置（gov-purchase-table项目） ==========
CONFIG = {
    # 采购公告CSV配置（不含公告ID）
    "purchase_notice": {
        "csv_path": r"D:\pytonTest\爬取相关网络信息\采购公告.csv",
        "headers": ["标题", "采购级别", "采购品类", "发布时间", "详情链接"],  # 无公告ID
        "unique_key": "标题",  # 用于判断重复的字段
        "filter_cols": ["采购级别", "采购品类"],  # 支持按品类/级别筛选
        "time_col": "发布时间"  # 时间排序列
    },
    # 采购意向公告CSV配置（不含公告ID）
    "purchase_intention": {
        "csv_path": r"D:\pytonTest\爬取相关网络信息\采购意向公告.csv",
        "headers": ["意向标题", "级别", "采购单位", "意向发布时间", "详情链接"],  # 无公告ID
        "unique_key": "意向标题",  # 用于判断重复的字段
        "filter_cols": ["级别", "采购单位"],  # 支持按级别筛选
        "time_col": "意向发布时间"  # 时间排序列
    },
    # HTML生成路径（项目名称改为gov-purchase-table）
    "html_output_path": r"D:\pytonTest\爬取相关网络信息\gov-purchase-table.html",
    # 历史数据存储路径（用于判断新增内容）
    "history_data_path": r"D:\pytonTest\爬取相关网络信息\history_data.json"
}


# ========== 数据处理工具函数 ==========
def load_history_data():
    """加载历史数据用于判断重复内容"""
    try:
        if Path(CONFIG["history_data_path"]).exists():
            with open(CONFIG["history_data_path"], "r", encoding="utf-8") as f:
                return json.load(f)
        return {"purchase_notice": [], "purchase_intention": []}
    except Exception as e:
        print(f"加载历史数据失败：{str(e)}")
        return {"purchase_notice": [], "purchase_intention": []}


def save_history_data(notice_titles, intention_titles):
    """保存当前数据到历史记录"""
    try:
        history_data = {
            "purchase_notice": notice_titles,
            "purchase_intention": intention_titles,
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(CONFIG["history_data_path"], "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        print("历史数据已更新")
    except Exception as e:
        print(f"保存历史数据失败：{str(e)}")


def filter_duplicates(df, unique_key, history_list):
    """过滤重复内容，并标记新增内容"""
    # 标记新增内容
    df['is_new'] = df[unique_key].apply(lambda x: x not in history_list)
    # 返回去重后的DataFrame
    df = df.drop_duplicates(subset=[unique_key], keep='first')
    # 新增数据置顶
    df = df.sort_values(by='is_new', ascending=False, ignore_index=True)
    return df


def parse_time_column(df, time_col):
    """解析时间列，统一格式并处理异常值"""
    if time_col not in df.columns:
        return df

    def parse_time(time_str):
        if pd.isna(time_str) or time_str in ["无数据", "未知", ""]:
            return pd.NaT
        # 尝试多种时间格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y年%m月%d日',
            '%m-%d-%Y',
            '%d/%m/%Y'
        ]
        for fmt in formats:
            try:
                return pd.to_datetime(time_str, format=fmt)
            except:
                continue
        # 自动解析
        try:
            return pd.to_datetime(time_str, errors='ignore')
        except:
            return pd.NaT

    df[f'{time_col}_parsed'] = df[time_col].apply(parse_time)
    return df


# ========== 生成HTML在线表格核心函数 ==========
def generate_online_html_table():
    """生成包含完整筛选和排序功能的政府采购在线表格"""
    print("开始生成gov-purchase-table.html...")
    print(f"读取采购公告CSV：{CONFIG['purchase_notice']['csv_path']}")
    print(f"读取采购意向公告CSV：{CONFIG['purchase_intention']['csv_path']}")

    # 1. 加载历史数据
    history_data = load_history_data()

    # 2. 安全读取CSV文件
    def read_csv_safe(csv_path, headers):
        try:
            if not Path(csv_path).exists():
                print(f"⚠️ 未找到CSV文件：{csv_path}")
                return pd.DataFrame(columns=headers)

            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            # 强制保留指定列
            df = df.reindex(columns=headers, fill_value="无数据")
            # 补全缺失值
            df = df.fillna({"采购品类": "未分类"}, inplace=False)
            return df.fillna("无数据")

        except Exception as e:
            print(f"❌ 读取CSV失败 {csv_path}：{str(e)}")
            return pd.DataFrame(columns=headers)

    # 读取两份CSV
    df_notice = read_csv_safe(
        CONFIG["purchase_notice"]["csv_path"],
        CONFIG["purchase_notice"]["headers"]
    )
    df_intention = read_csv_safe(
        CONFIG["purchase_intention"]["csv_path"],
        CONFIG["purchase_intention"]["headers"]
    )

    # 解析时间列（用于排序）
    df_notice = parse_time_column(df_notice, CONFIG["purchase_notice"]["time_col"])
    df_intention = parse_time_column(df_intention, CONFIG["purchase_intention"]["time_col"])

    # 3. 过滤重复内容并标记新增
    notice_key = CONFIG["purchase_notice"]["unique_key"]
    intention_key = CONFIG["purchase_intention"]["unique_key"]

    df_notice = filter_duplicates(
        df_notice,
        notice_key,
        history_data.get("purchase_notice", [])
    )
    df_intention = filter_duplicates(
        df_intention,
        intention_key,
        history_data.get("purchase_intention", [])
    )

    # 提取当前所有标题用于更新历史记录
    current_notice_titles = df_notice[notice_key].tolist()
    current_intention_titles = df_intention[intention_key].tolist()

    # 4. HTML样式
    html_style = """
    <style>
        body {font-family: "Microsoft YaHei", Arial, sans-serif; margin: 20px; background-color: #f5f5f5;}
        .container {max-width: 1400px; margin: 0 auto;}

        /* 筛选区域样式 */
        .filter-container {background: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px;}
        .filter-group {display: inline-block; margin-right: 20px; margin-bottom: 10px;}
        .filter-label {font-size: 14px; color: #34495e; margin-right: 8px; font-weight: 500;}
        .filter-select {padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; min-width: 150px;}
        .filter-btn {padding: 6px 15px; border: none; border-radius: 4px; font-size: 14px; cursor: pointer; margin-right: 10px;}
        .filter-reset {background-color: #3498db; color: white;}
        .filter-reset:hover {background-color: #2980b9;}
        .filter-new {background-color: #e74c3c; color: white;}
        .filter-new:hover {background-color: #c0392b;}
        .filter-all {background-color: #2ecc71; color: white;}
        .filter-all:hover {background-color: #27ae60;}
        .sort-btn {background-color: #9b59b6; color: white;}
        .sort-btn:hover {background-color: #8e44ad;}
        .sort-btn.active {opacity: 0.8; border: 2px solid #8e44ad;}

        /* 表格容器样式 */
        .table-container {margin: 30px 0; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);}
        h1 {color: #2c3e50; text-align: center; margin-bottom: 30px; font-size: 24px;}
        h2 {color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; font-size: 18px; margin-top: 20px; margin-bottom: 15px;}

        /* 表格样式 */
        table {width: 100%; border-collapse: collapse; margin: 10px 0;}
        th, td {padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; font-size: 14px;}
        th {background-color: #3498db; color: white; font-weight: normal; position: relative;}
        tr:hover {background-color: #f8f9fa;}
        tr.new-row {background-color: #e8f4fd; font-weight: 500;}
        .time-sort-indicator {color: #9b59b6; font-weight: bold; margin-left: 8px; font-size: 12px;}

        /* 链接样式 */
        .link {color: #3498db; text-decoration: none;}
        .link:hover {text-decoration: underline;}

        /* 新增标记样式 */
        .new-label {color: #e74c3c; font-weight: bold; font-size: 12px; margin-left: 8px;}

        /* 元数据样式 */
        .metadata {text-align: center; color: #7f8c8d; margin-top: 20px; font-size: 12px;}

        /* 响应式样式 */
        @media (max-width: 768px) {
            .filter-group {display: block; margin-right: 0;}
            table {font-size: 12px;}
            th, td {padding: 8px 10px;}
            .filter-select {min-width: 100%;}
            .filter-btn {margin-bottom: 10px; width: 100%;}
        }
    </style>
    """

    # 5. 生成筛选控件HTML
    def generate_filter_controls(df, table_id, filter_cols, time_col):
        if df.empty:
            return "<p style='color:#7f8c8d;'>暂无筛选条件</p>"

        filter_html = []
        filter_html.append(f"<div class='filter-container' id='filter-{table_id}'>")

        # 为每个筛选列生成下拉框
        if filter_cols:
            for col in filter_cols:
                if col not in df.columns:
                    continue

                unique_vals = sorted(df[col].drop_duplicates().tolist())
                if "无数据" in unique_vals:
                    unique_vals.remove("无数据")
                    unique_vals.insert(0, "无数据")
                if "未分类" in unique_vals:
                    unique_vals.remove("未分类")
                    unique_vals.insert(1, "未分类")

                filter_html.append(f"<div class='filter-group'>")
                filter_html.append(f"<label class='filter-label'>{col}：</label>")
                filter_html.append(
                    f"<select class='filter-select' id='filter-{table_id}-{col}' onchange='filterTable(\"{table_id}\")'>")
                filter_html.append(f"<option value='all'>全部</option>")
                for val in unique_vals:
                    filter_html.append(f"<option value='{val}'>{val}</option>")
                filter_html.append(f"</select>")
                filter_html.append(f"</div>")

        # 添加筛选按钮
        filter_html.append(f"<div class='filter-group'>")
        filter_html.append(
            f"<button class='filter-btn filter-new' onclick='filterOnlyNew(\"{table_id}\")'>仅看新增</button>")
        filter_html.append(
            f"<button class='filter-btn filter-all' onclick='filterShowAll(\"{table_id}\")'>显示全部</button>")
        filter_html.append(
            f"<button class='filter-btn filter-reset' onclick='resetFilter(\"{table_id}\")'>重置筛选</button>")
        filter_html.append(f"</div>")

        # 时间排序按钮组
        filter_html.append(f"<div class='filter-group'>")
        filter_html.append(f"<label class='filter-label'>{time_col}：</label>")
        filter_html.append(
            f"<button class='filter-btn sort-btn' id='sort-{table_id}-newest' onclick='sortByTime(\"{table_id}\", \"newest\")'>按最新排序</button>")
        filter_html.append(
            f"<button class='filter-btn sort-btn' id='sort-{table_id}-oldest' onclick='sortByTime(\"{table_id}\", \"oldest\")'>按最早排序</button>")
        filter_html.append(
            f"<button class='filter-btn sort-btn' id='sort-{table_id}-reset' onclick='sortByTime(\"{table_id}\", \"reset\")'>恢复原排序</button>")
        filter_html.append(f"</div>")

        filter_html.append(f"</div>")
        return "\n".join(filter_html)

    # 6. 生成带功能的表格HTML
    def df_to_html_with_features(df, table_id, link_col="详情链接", unique_key="标题", filter_cols=[], time_col=""):
        df_html = df.copy()

        # 处理链接列
        if link_col in df_html.columns:
            df_html[link_col] = df_html[link_col].apply(
                lambda x: f'<a href="{x}" target="_blank" class="link">{x}</a>'
                if x not in ["无有效ID", "无数据", "未知"] and x.startswith("http")
                else x
            )

        # 处理标题列（添加新增标记）
        if unique_key in df_html.columns and 'is_new' in df_html.columns:
            df_html[unique_key] = df_html.apply(
                lambda row: f"{row[unique_key]}<span class='new-label'>[新增]</span>"
                if row['is_new'] else row[unique_key],
                axis=1
            )

        # 生成表格HTML
        rows = []
        # 添加表头
        headers = []
        sort_indicator = f' <span class="time-sort-indicator" id="sort-indicator-{table_id}"></span>'
        for col in df_html.columns:
            if col not in ['is_new', f'{time_col}_parsed']:
                if col == time_col:
                    headers.append(f"<th>{col}{sort_indicator}</th>")
                else:
                    headers.append(f"<th>{col}</th>")
        rows.append(f"<thead><tr>{''.join(headers)}</tr></thead>")

        # 添加表体
        rows.append("<tbody id='tbody-" + table_id + "'>")
        for idx, row in df_html.iterrows():
            row_class = "new-row" if row.get('is_new', False) else ""

            # 构建行的data属性
            data_attrs = []
            for col in filter_cols:
                if col in df_html.columns:
                    data_attrs.append(f'data-{col.lower().replace(" ", "-")}="{row[col]}"')
            data_attrs.append(f'data-is-new="{str(row.get("is_new", False)).lower()}"')

            # 添加时间戳属性（用于排序）
            if f'{time_col}_parsed' in df_html.columns:
                time_val = row[f'{time_col}_parsed']
                timestamp = pd.Timestamp(time_val).timestamp() if pd.notna(time_val) else 0
                data_attrs.append(f'data-timestamp="{timestamp}"')
                data_attrs.append(f'data-time-orig="{row[time_col]}"')

            # 构建单元格
            cells = []
            for col in df_html.columns:
                if col not in ['is_new', f'{time_col}_parsed']:
                    cells.append(f"<td>{row[col]}</td>")

            rows.append(
                f"<tr class='{row_class}' {' '.join(data_attrs)} id='{table_id}-row-{idx}'>{''.join(cells)}</tr>")
        rows.append("</tbody>")

        # 拼接表格HTML
        table_html = f"<table id='{table_id}-table'>{''.join(rows)}</table>"

        # 组合筛选控件和表格
        filter_html = generate_filter_controls(df, table_id, filter_cols, time_col)
        full_html = f"""
        <div id='{table_id}-wrapper'>
            {filter_html}
            {table_html if not df.empty else '<p style="color:#7f8c8d; text-align:center;">暂无数据</p>'}
        </div>
        """
        return full_html

    # 生成表格HTML
    notice_html = df_to_html_with_features(
        df_notice,
        table_id="notice",
        link_col="详情链接",
        unique_key=notice_key,
        filter_cols=CONFIG["purchase_notice"]["filter_cols"],
        time_col=CONFIG["purchase_notice"]["time_col"]
    )
    intention_html = df_to_html_with_features(
        df_intention,
        table_id="intention",
        link_col="详情链接",
        unique_key=intention_key,
        filter_cols=CONFIG["purchase_intention"]["filter_cols"],
        time_col=CONFIG["purchase_intention"]["time_col"]
    )

    # 7. 完整的筛选和排序JavaScript代码
    js_script = """
    <script>
        // 全局筛选状态
        const filterState = {
            'notice': {onlyNew: false, sortType: 'original'},
            'intention': {onlyNew: false, sortType: 'original'}
        };

        // 保存原始行顺序
        const originalRowOrder = {
            'notice': [],
            'intention': []
        };

        // 页面加载完成后初始化
        window.onload = function() {
            saveOriginalRowOrder('notice');
            saveOriginalRowOrder('intention');
            resetFilter('notice');
            resetFilter('intention');
        };

        // 保存原始行顺序
        function saveOriginalRowOrder(tableId) {
            const tbody = document.getElementById(`tbody-${tableId}`);
            if (!tbody) return;

            const rows = tbody.querySelectorAll('tr');
            originalRowOrder[tableId] = Array.from(rows).map(row => row.outerHTML);
        }

        // 基础筛选表格函数
        function baseFilterTable(tableId) {
            const filterCols = {
                'notice': ['采购级别', '采购品类'],
                'intention': ['级别', '采购单位']
            }[tableId];

            // 收集筛选值
            const filterValues = {};
            filterCols.forEach(col => {
                const select = document.getElementById(`filter-${tableId}-${col}`);
                if (select) {
                    filterValues[col] = select.value;
                }
            });

            // 获取所有行
            const tbody = document.getElementById(`tbody-${tableId}`);
            const rows = tbody.querySelectorAll('tr');

            // 应用筛选
            rows.forEach(row => {
                let shouldShow = true;

                // 检查筛选条件
                filterCols.forEach(col => {
                    if (filterValues[col] !== 'all') {
                        const dataAttr = `data-${col.toLowerCase().replace(' ', '-')}`;
                        if (row.getAttribute(dataAttr) !== filterValues[col]) {
                            shouldShow = false;
                        }
                    }
                });

                // 检查是否仅看新增
                if (filterState[tableId].onlyNew && row.getAttribute('data-is-new') !== 'true') {
                    shouldShow = false;
                }

                // 显示或隐藏行
                row.style.display = shouldShow ? '' : 'none';
            });
        }

        // 筛选表格（对外接口）
        function filterTable(tableId) {
            baseFilterTable(tableId);
        }

        // 仅查看新增内容
        function filterOnlyNew(tableId) {
            filterState[tableId].onlyNew = true;
            baseFilterTable(tableId);
        }

        // 显示全部内容
        function filterShowAll(tableId) {
            filterState[tableId].onlyNew = false;
            baseFilterTable(tableId);
        }

        // 重置筛选条件
        function resetFilter(tableId) {
            // 重置下拉选择框
            const filterCols = {
                'notice': ['采购级别', '采购品类'],
                'intention': ['级别', '采购单位']
            }[tableId];

            filterCols.forEach(col => {
                const select = document.getElementById(`filter-${tableId}-${col}`);
                if (select) {
                    select.value = 'all';
                }
            });

            // 重置状态
            filterState[tableId].onlyNew = false;

            // 重置排序
            sortByTime(tableId, 'reset');

            // 应用筛选
            baseFilterTable(tableId);
        }

        // 按时间排序
        function sortByTime(tableId, sortType) {
            const tbody = document.getElementById(`tbody-${tableId}`);
            if (!tbody) return;

            // 更新排序状态
            filterState[tableId].sortType = sortType;

            // 重置排序按钮样式
            document.querySelectorAll(`[id^="sort-${tableId}-"]`).forEach(btn => {
                btn.classList.remove('active');
            });
            if (sortType !== 'reset') {
                document.getElementById(`sort-${tableId}-${sortType}`).classList.add('active');
            } else {
                document.getElementById(`sort-${tableId}-reset`).classList.add('active');
            }

            // 更新排序指示器
            const indicator = document.getElementById(`sort-indicator-${tableId}`);
            if (indicator) {
                if (sortType === 'newest') {
                    indicator.textContent = '↓';
                } else if (sortType === 'oldest') {
                    indicator.textContent = '↑';
                } else {
                    indicator.textContent = '';
                }
            }

            // 获取所有可见行
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const visibleRows = rows.filter(row => row.style.display !== 'none');

            // 恢复原始排序
            if (sortType === 'reset') {
                tbody.innerHTML = originalRowOrder[tableId].join('');
                return;
            }

            // 按时间戳排序
            visibleRows.sort((a, b) => {
                const timestampA = parseFloat(a.getAttribute('data-timestamp')) || 0;
                const timestampB = parseFloat(b.getAttribute('data-timestamp')) || 0;

                // 最新在前或最早在前
                return sortType === 'newest' ? timestampB - timestampA : timestampA - timestampB;
            });

            // 重新添加排序后的行
            visibleRows.forEach(row => {
                tbody.appendChild(row);
            });
        }
    </script>
    """

    # 8. 组合完整HTML
    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>政府采购信息表格 - gov-purchase-table</title>
        {html_style}
    </head>
    <body>
        <div class="container">
            <h1>政府采购信息汇总表</h1>

            <div class="table-container">
                <h2>一、采购公告</h2>
                {notice_html}
            </div>

            <div class="table-container">
                <h2>二、采购意向公告</h2>
                {intention_html}
            </div>

            <div class="metadata">
                <p>最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>项目名称：gov-purchase-table</p>
            </div>
        </div>
        {js_script}
    </body>
    </html>
    """

    # 9. 保存HTML文件
    try:
        with open(CONFIG["html_output_path"], "w", encoding="utf-8") as f:
            f.write(full_html)
        print(f"✅ HTML表格已生成：{CONFIG['html_output_path']}")

        # 更新历史数据
        save_history_data(current_notice_titles, current_intention_titles)

    except Exception as e:
        print(f"❌ 保存HTML失败：{str(e)}")


# 执行生成
if __name__ == "__main__":
    generate_online_html_table()