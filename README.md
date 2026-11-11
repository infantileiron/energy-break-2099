# 青屿陶窑 · 能耗工况变点

把小时电量和产量转为可复核的单位能耗工况段，区分持续均值变化与偶然尖峰。面向青屿陶窑16人工艺组，全部为模拟记录，不连接真实设备。

## 场景与工作流

原流程用 `qingyu_kiln1_202610.csv` 在Excel按日均电量对比。三个痛点是不同产量不可比、变点靠肉眼判断、停机扰动混进运行期。上游为电表与产量小时汇总；本项目替代人工归一、分段和异常复核；下游为工艺组对照换料、烧成和计量日志讨论。

六核心实体贯穿表、Python Model/Schema/Service/Controller/Route、React API/Store/页面：MeterDataset（小时观测）、OperatingWindow（时间口径）、ChangeStudy（算法参数）、ChangeRun（异步结果）、IncidentReview（工况复核）、Report（批准快照）。

## 启动

```sh
cp .env.example .env
docker compose up -d --build --wait
# 可手工重复执行，保留用户修改，不新增重复演示实体
docker compose exec -T backend python -m scripts.seed_demo
```

前端 http://localhost:18214 ，API文档 http://localhost:19214/docs ，PostgreSQL宿主17714。Nginx `/api/` 去前缀转发给Python；Vite开发代理保持相同口径。`/health` 验证数据库与Redis连接。

恰好frontend/backend/worker/db/redis五服务，均有健康检查。数据库、Redis和共享worker心跳分别使用具名卷。演示清理 `docker compose down -v --remove-orphans`；若保留数据，去掉 `-v`。

## 技术与目录

| 层 | 实现 |
|---|---|
| 前端 | React18.3.1、TypeScript5.7、Vite6、React Router6 |
| 后端 | Python3.12、FastAPI0.115.6、SQLAlchemy2、NumPy2.2.1 |
| 存储 | PostgreSQL16、Redis7.4 |
| 后台 | 独立Python worker，Redis队列，运行与结果持久化PostgreSQL |
| 网关 | Nginx1.28，SPA回落与API代理 |

- `backend/src/models,schemas,services,controllers,routes`：按六业务实体分层。
- `services/readings.py`：导入与归一；`change_points.py`：DP；`robust_scores.py`：分段残差MAD评分。
- `backend/src/config,utils,middlewares`：配置、数据库、JWT/口令摘要、队列、审计、全局错误。
- `backend/scripts/seed_demo.py`：自然键种子；`migrations/001_schema.sql`：新库基线说明，启动以元数据建表。
- `frontend/src/api,stores,types,pages,router`：实体端到端入口；`components`的EnergyTrace与SegmentTable被总览、结果、报告共用；`hooks`提供任务状态和轮询。
- 测试、截图、日志位于批次外层 `test-artifacts/gb-2205`，不放源码内。

本地开发：安装backend/requirements.txt后从backend执行 `uvicorn src.main:app --reload`，设置可用DATABASE_URL/REDIS_URL；另起 `python -m src.worker`。前端 `npm install && npm run dev`，构建 `npm run build` 同时执行TypeScript检查。

变量：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET、SEED_DEMO；DATABASE_URL/REDIS_URL由Compose内部注入。演示数据库口令和JWT密钥用于本地模拟，部署时需独立配置。`.env`不进入源码包。

## 演示账号与权限

统一密码 `KilnDemo2026!`。PBKDF2-SHA256独立salt口令摘要；JWT八小时有效。

| 账号/角色 | 页面与动作 | 服务端权限 |
|---|---|---|
| admin@energy.demo / admin | 工况复核、报告归档、审计 | 所有分析写入与批准归档 |
| analyst@energy.demo / analyst | 观测导入、窗口、研究、计算、复核提交 | 可分析，不能批准/归档 |
| viewer@energy.demo / viewer | 台账、结果、已归档CSV | 只读；写入403 |

未登录401，错角色403，未批准复核生成报告409。同一已审复核重复归档返回同一快照，不覆盖标题及结果。

共享枚举：角色/运行状态在 `backend/src/constants/enums.py` 的Role/RunStatus和 `frontend/src/constants/enums.ts` 的roles/runStatuses；计量状态MeterStatus与meterStatuses分处同两文件，前端Role类型见types/domain.ts。

## 算法、单位与失败态

CSV列 `timestamp,kwh,output_kg,status`；最多5000行。时间必须含时区，归一UTC、排序，等价时刻跨时区重复也拒绝。未知状态、负值、NaN、Infinity在导入时422拒绝。空电量/产量可入库，标为缺测；stopped、零产量、缺测分别隔离，保留原因，不把0当能耗值。

归一口径为 x_i=kWh_i/output_kg_i（kWh/kg）。按窗口两端包含取样，至少8条有效运行观测。最小段长以**有效观测数量**计，不是小时长度；停机与缺测造成的时间空隙不插值。图横轴为排序后的有效观测序号，日期只作位置标记。

DP在所有满足最小段长的分割中求解：

`Σ_segments Σ_i (x_i - segment_mean)^2 + penalty × number_of_change_points`

使用中心化前缀和计算段SSE，动态规划保存最小目标与回溯边界；默认penalty=6（单位为归一能耗的平方），min_segment=24。惩罚越大通常工况段越少。输入不足最小段长、无足够有效观测或量级不支持可靠平方运算时运行明确failed，返回可读错误。

第二算法在每个DP段内以均值残差计算中位数与MAD。分数：

`abs(residual - median_residual) / max(1.4826 × MAD, noise_floor)`

默认noise_floor=0.02 kWh/kg，threshold=3.5；分数严格大于阈值时标注尖峰。MAD=0时使用明确的计量噪声下限，保持有限分数：常量段全部0，不伪造异常；孤立偏离仍可识别。噪声下限应由真实计量分辨率设定，演示值不代表实际设备公差。两算法确定性计算，不使用随机拟合。

变点表示分段均值变化，不自动证明换料造成变化；异常分数也不是故障概率。低惩罚可能把尖峰分成独立工况；最小段长与复核日志帮助约束这种误读。

## 一天的工艺复核

1. 09:00 分析师打开 `qingyu_kiln1_202610.csv`，核查720条小时记录、单位与时区。
2. 09:03 检查4条停机、1条零产量、1条缺测，确认隔离口径。
3. 09:07 选择十月全月窗口，不跨未记录的工况时段比较。
4. 09:10 保存惩罚6、最小24条、MAD阈值3.5及噪声下限0.02。
5. 09:12 送入Redis队列，由独立worker完成DP与MAD结果持久化。
6. 09:18 对照10月11日、21日两次工况变化，查看三处尖峰时段。
7. 09:23 标注换料记录与计量核查建议，不直接认定设备故障。
8. 09:28 管理员批准并归档；viewer下载含714条有效观测和有限分数的CSV底稿。

固定种子20261112产生720条模拟小时观测。默认研究实际得到3工况段、714有效/6隔离、3尖峰，与生成的工况及尖峰位置一致。演示实体自然键幂等，手工修改说明不被种子覆盖。

## 已知差异

- Redis列表取走任务后worker崩溃不会自动重投；可建立新运行重试，未实现租约与取消。
- 新库自动建表；存量库没有版本化升级/回滚工具。列表最多200条实体，尚无服务器分页。
- 仅有限CSV导入，不接真实设备或自动校验电量/产量计量周期是否一致；由使用者复核口径。
- 控制图展示与诊断为模拟教学，不是设备安全监测。Google Fonts需联网，断网回退字体。

MIT License。真实验收和截图见批次 `test-artifacts/gb-2205/TESTING.md`。
