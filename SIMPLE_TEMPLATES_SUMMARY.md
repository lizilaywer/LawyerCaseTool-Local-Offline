# 9个简易模板创建完成

## 创建日期
2026-03-15

## 模板列表

| 序号 | 模板ID | 模板名称 | 分类 | 文件夹数 |
|------|--------|----------|------|----------|
| 1 | civil_simple_001 | 民事案件简易模板(原告) | civil | 4 |
| 2 | civil_simple_002 | 民事案件简易模板(被告) | civil2 | 4 |
| 3 | criminal_simple_001 | 刑事案件简易模板 | criminal | 4 |
| 4 | admin_simple_001 | 行政案件简易模板(原告) | administrative | 4 |
| 5 | admin_simple_002 | 行政案件简易模板(被告) | administrative | 4 |
| 6 | labor_simple_001 | 劳动仲裁简易模板(申请人) | labor_arbitration | 4 |
| 7 | labor_simple_002 | 劳动仲裁简易模板(被申请人) | labor_arbitration | 4 |
| 8 | commercial_simple_001 | 商事仲裁简易模板(申请人) | commercial_arbitration | 4 |
| 9 | commercial_simple_002 | 商事仲裁简易模板(被申请人) | commercial_arbitration | 4 |

## 文件夹结构

每个简易模板包含4个核心文件夹：
1. **委托手续** - 委托合同、授权委托书、身份证明
2. **文书材料** - 起诉状/答辩状/申请书、证据清单
3. **证据材料** - 空文件夹（用于存放证据）
4. **检索及其他材料** - 空文件夹（用于存放检索材料）

## 创建的文件

### 配置文件
- `src/config/default_templates.py` - 已添加9个简易模板定义

### 模板目录
在 `templates/` 下创建9个新目录：
- `civil_simple_plaintiff/`
- `civil_simple_defendant/`
- `criminal_simple/`
- `administrative_simple_plaintiff/`
- `administrative_simple_defendant/`
- `labor_simple_applicant/`
- `labor_simple_respondent/`
- `commercial_simple_applicant/`
- `commercial_simple_respondent/`

每个目录包含：
- `template.docx` - 空Word模板文件

### 变量定义
每个模板包含6个核心变量：
1. 委托人/当事人/申请人/被申请人名称（必填）
2. 案号/仲裁案号（可选）
3. 对方当事人名称（可选）
4. 受理法院/仲裁机构（可选）
5. 承办律师（可选）
6. 收案日期（可选）

## 与完整模板的区别

| 特性 | 完整模板 | 简易模板 |
|------|----------|----------|
| 文件夹数 | 6-9个 | 4个 |
| 预设文件数 | 15-25个 | 6-8个 |
| 适用场景 | 复杂案件 | 简单案件 |
| 灵活性 | 高 | 精简高效 |

## 总数统计

- **完整版模板**: 8个
- **简易版模板**: 9个
- **总计**: 17个默认模板

## 使用方法

重启应用后，9个新模板会自动加载到模板列表中，可以在"全部"或对应分类下查看和使用。
