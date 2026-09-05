# Style 09 送图脚本与生成图对比审阅

## 结论

技术判断：`SUPPORT WITH CONDITIONS`。

Style 09 需要调整，但只改 `references/visual-system.md` 的文字不足以稳定修复本次问题。当前参考图 `assets/palette-samples/palette-09.png` 明确呈现左侧竖向导航、横向分层、等分栏位、图标占位与大面积照片，这些视觉先验与风格正文中的禁用项相冲突。建议同步更换 Style 09 参考图，或停止把该图作为每页必传参考。

## 对比发现

### 1. 版式形成了风格正文明确禁止的“卡片墙”

风格正文要求单一主结构、非对称、非等权，并明确禁止等宽卡片、等行等列和图标阵列。生成图实际采用三条横向分层：顶部四个等权服务对象，中部两个大卡片加一个横卡片，底部四个系统卡片与四个实施方式图标。页面因此更像信息系统总览看板，主判断只占中央圆形区域，无法真正统领全页。

### 2. 参考图在视觉上抵消了文字禁令

Style 09 参考图自身包含三段左侧深蓝竖栏、横向分区、等分内容槽、连续小图标和办公场景大图。生成图几乎逐项继承了这些结构特征。模型对图像参考的模仿强度高于对英文否定句的服从强度，因此“文本写着避免、参考图展示该结构”的合同不稳定。

### 3. “多个嵌入场景”被执行成一项一图

送图脚本要求优先使用多个小中型场景，并列举电网设施、调度中心、控制室、风光基地、储能设备和电厂等例子。生成图据此为四类服务对象、两个建设方向及底层能力大量配图。场景从语义锚点退化为栏目配图，照片数量过多，页面呈现拼贴感，且“行业中枢与价值释放引擎”的核心关系没有得到相应强化。

### 4. 图标规则未生效

风格正文规定典型页面最多使用一至两个图标，生成图实际使用了十余个图标。原因之一是参考图已展示多个图标槽位；原因之二是送图脚本同时要求呈现三重方向、四类对象、四类系统和四种实施方式，模型用图标作为压缩手段。当前规则只有文字禁令，没有要求在信息过载时优先合并、降级或省略装饰性视觉。

### 5. 出现了源稿未提供的解释性细节

生成图增加了“生产、营销、调度、设备管理等”“数据湖、数据中台、数据库等”“机理模型、AI 模型、算法库等”“平台集中提供标准化服务”“数据不出域，源端完成处理”“专属部署，保障隔离安全”“可信执行环境，保障可控可审计”等表述。它们具有行业合理性，但没有来自本页源稿，属于未经授权的事实扩写。现有文字审计仅检查错字和伪中文，`valid: true` 不能证明内容忠实。

### 6. 信息层级过多，可读字号被压缩

页面同时呈现中心定位、三重建设方向、四类服务对象、四类既有平台、四种实施方式和知识产权边界，形成至少五级阅读层。底部说明和图标注释字号明显偏小，屏幕展示时难以快速自读。送图脚本虽然要求强层级和少组件，但又要求完整承载全部正文，缺少“超出单页容量时优先保留哪些语义”的明确决策规则。

### 7. 放射关系表达不完整

源稿把中心定位、三重方向和四类服务对象描述为由内向外的放射结构。生成图只有顶部对象与中心之间的两条汇聚线，三重方向与中心、三重方向与四类对象之间没有形成完整、可追踪的关系。视觉上更接近“顶部服务对象—中部建设模块—底部支撑条件”的分层架构，改变了原稿强调的共同支撑和逐层拓展关系。

## 根因排序

1. **首要根因：参考图与文字合同冲突。** 参考图直接示范了左栏、分层、等分栏和图标阵列。
2. **次要根因：Style 09 同时奖励多场景与少组件。** “多个小中型场景”在高密度页面上会自然演化成多卡片拼贴。
3. **页面级根因：源稿容量过高。** 完整文字与四组结构都要求上屏，模型只能压缩字号并增加模块。
4. **审计缺口：只做错字/伪中文检查。** 未检查新增事实、组件数量、禁用版式和最小字号。

## 风格文件建议改法

建议把 Style 09 从“场景优先的通用领导汇报风格”收敛为“单载体、关系优先的领导汇报风格”。以下内容可直接替换当前对应段落。

```text
Create one composition around a single semantic carrier. The carrier must own the page geometry and the reading path. Supporting content may attach to, orbit, branch from, or sit beneath this carrier, but must not become a collection of independent panels.

Use at most three primary content regions in a standard page. Repeated peers must share one continuous field, band, orbit, network, or grouped structure. Do not place each peer in its own bordered card.

Choose one dominant visual medium per page: relationship diagram, one contextual business scene, object illustration, or data visualization. Use a second medium only when it proves a different source-backed claim. Do not assign one photo or one icon to every item.

For relationship-led pages, prioritize the relationship diagram over decorative scenes. Show both ends of every claimed relationship and the connecting action. When the source declares a center, surrounding layers, shared support, or radial expansion, preserve those relations in one continuous geometry.

Use no more than two photographs and no more than two semantic icons on a standard page. A photograph must prove or contextualize a specific claim. An icon must not act as a substitute for a content category.

Never invent examples, implementation details, technology names, operational claims, or explanatory captions. Every visible factual phrase must be a faithful rewrite of supplied source text. If the source does not provide a detail, leave it unstated.

When all supplied copy cannot remain readable at presentation size, preserve the core judgment, named business objects, relationships, responsibilities, conditions and boundaries first. Merge repeated wording and omit decorative labels or images. Do not solve overload by shrinking body text or multiplying modules.

Avoid left-side section rails, dashboard bands, equal-width cards, repeated bordered containers, icon inventories, photo-per-item layouts, and template-like three-row stacks, even when they appear in a reference image. Reference images control palette, material, whitespace and photographic tone only; they do not authorize copying their layout.
```

## 参考图处理建议

优先方案是重做 `palette-09.png`：只保留纯白、深蓝、浅灰、细分隔线、克制照片质感和一个明确主焦点；移除左侧三段竖栏、四等分槽位和连续图标占位。若暂时不能重做参考图，应取消 `required_for_every_page`，或在生产调用中不传 Style 09 参考图。仅靠在风格正文后追加更多否定句，预计仍会出现类似版式。

## 针对本页的理想执行

本页应采用一个连续的同心放射载体：中心为“行业中枢与价值释放引擎”，中环承载三重建设方向，外环以四个扇区表达服务对象；底部用一条低权重基座表达既有系统协同、控制关系不变和四种实施方式。照片最多保留一张作为电力行业语境，不为每一类对象分别配图。所有可见文字只取自源稿。

