const copy = {
  en: {
    chooseLanguage: 'Choose your language', welcome: 'Welcome to ZyPulse', languageIntro: 'Choose a language to continue. You can change it later in your profile.', continue: 'Continue',
    safety: 'ZyPulse is a self-care support prototype, not a medical device. Consult your doctor for medical advice.',
    today: 'Today', coach: 'Coach', log: 'Log', meals: 'Meals', trends: 'Trends', connect: 'Connect', history: 'History', profile: 'Profile',
    record: 'Record', explore: 'Explore', more: 'More', account: 'Account', notifications: 'Notifications',
    notesForDoctor: 'Notes for My Doctor', healthSummaryShort: 'Health Summary',
    exploreEvents: 'Healthy365 Events', exploreFacilities: 'Sports Facilities',
    shortcutEvents: 'Explore Healthy365 Events', shortcutFacilities: 'Find Nearby Sports Facilities',
    sharingTitle: 'What is shared, and with whom',
    sharingBody: 'ZyPulse is a self-care prototype. Your entries are stored in the local demo database used by this prototype. Nothing is sent to Healthy 365, HPB, Sport Singapore or any other third party, and the Healthy 365 event handoff is simulated only. There are no data-sharing settings to configure, and nothing here is saved or enforced as a sharing preference.',
    close: 'Close',
    saveForDoctor: 'Save question for my doctor', savedForDoctor: 'Question saved to Notes for My Doctor.', saveForDoctorFailed: 'Could not save that question. Please try again.',
    whyRedirected: 'Why was this redirected?',
    safetyBlockedReason: 'Questions about changing your medication, or about diagnosis and cause, are redirected. ZyPulse cannot answer them safely — please ask your doctor.',
    safetyFallbackReason: 'The AI answer is unavailable, so this reply uses information calculated directly from your own records.',
    profileTitle: 'Profile', displayName: 'Preferred / display name', location: 'General location', email: 'Contact email (optional)', phone: 'Contact phone (optional)',
    preferredLanguage: 'Preferred language', languageHelp: 'This choice updates ZyPulse throughout the app.', goals: 'My self-care goals', barriers: 'What can make this harder?', activities: 'Preferred activities', availability: 'Times that usually work for you',
    accessibility: 'Accessibility / settings', largerText: 'Larger text', on: 'On', off: 'Off', saveProfile: 'Save Profile', saving: 'Saving...', profileSaved: 'Profile saved.',
    quickLinks: 'Quick links', reminders: 'Notifications & reminders', healthSummary: 'Health Summary & Notes for Doctor', help: 'Help', signOut: 'Sign out', signedOut: 'Signed out (prototype)', returnProfile: 'Return to Profile',
    signOutNote: 'Prototype only - no account is actually closed.', profileSafety: 'This is a self-care prototype. No account data leaves your device in this demo.',
  },
  zh: {
    chooseLanguage: '选择语言', welcome: '欢迎使用 ZyPulse', languageIntro: '请选择语言以继续。您之后可在个人资料中更改。', continue: '继续',
    safety: 'ZyPulse 是一个自我照护支持原型，并非医疗设备。如需医疗建议，请咨询医生。',
    today: '今日', coach: '健康助手', log: '记录', meals: '膳食', trends: '趋势', connect: '社区', history: '历史', profile: '个人资料',
    record: '记录', explore: '探索', more: '更多', account: '账户', notifications: '通知',
    notesForDoctor: '给医生的备注', healthSummaryShort: '健康摘要',
    exploreEvents: 'Healthy365 活动', exploreFacilities: '运动场地',
    shortcutEvents: '浏览 Healthy365 活动', shortcutFacilities: '查找附近运动场地',
    sharingTitle: '共享了什么，与谁共享',
    sharingBody: 'ZyPulse 是一个自我照护原型。您的记录保存在本原型使用的本地演示数据库中。不会向 Healthy 365、HPB、Sport Singapore 或任何第三方发送数据，Healthy 365 活动转接仅为模拟。此原型没有可配置的数据共享设置，此处也不会保存或执行任何共享偏好。',
    close: '关闭',
    saveForDoctor: '保存此问题给医生', savedForDoctor: '问题已保存到「给医生的备注」。', saveForDoctorFailed: '无法保存该问题，请重试。',
    whyRedirected: '为什么被转接？',
    safetyBlockedReason: '关于调整用药、诊断或病因的问题会被转接。ZyPulse 无法安全地回答这些问题——请咨询您的医生。',
    safetyFallbackReason: 'AI 回答暂不可用，因此此回复使用直接根据您自己的记录计算得出的信息。',
    profileTitle: '个人资料', displayName: '首选称呼 / 显示名称', location: '大致位置', email: '联系电邮（可选）', phone: '联系电话（可选）',
    preferredLanguage: '首选语言', languageHelp: '此选择会更新整个 ZyPulse 应用的语言。', goals: '我的自我照护目标', barriers: '哪些事情会让这更困难？', activities: '首选活动', availability: '通常方便的时间',
    accessibility: '无障碍功能 / 设置', largerText: '较大文字', on: '开启', off: '关闭', saveProfile: '保存个人资料', saving: '保存中...', profileSaved: '个人资料已保存。',
    quickLinks: '快捷链接', reminders: '通知与提醒', healthSummary: '健康摘要与给医生的备注', help: '帮助', signOut: '登出', signedOut: '已登出（原型）', returnProfile: '返回个人资料',
    signOutNote: '仅为原型，账户不会真的被关闭。', profileSafety: '这是一个自我照护原型。此演示中不会有账户数据离开您的设备。',
  },
}

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'zh', label: '中文' },
]

export function translate(language, key) {
  return copy[language]?.[key] || copy.en[key] || key
}

export function useTranslation(language) {
  return (key) => translate(language, key)
}

// Page copy uses this helper while it is being progressively moved to named keys.
// Keeping the English source as the key prevents a missing translation from rendering an internal key.
const pageCopy = {
  zh: {
    'Record Activity': '记录运动',
    'Click to record activity': '点击记录运动',
    'Preparing your daily briefing...': '正在准备您的每日简报…', 'Your daily briefing': '您的每日简报', 'Good day, Mr Tan': '您好，陈先生', 'Your verified self-care snapshot, in one place.': '在这里查看您的自我照护记录概览。',
    "Today's health record check": '今日健康记录检查', attention: '关注', 'One small thing for today': '今天的一件小事', 'Make your briefing more personal': '让您的简报更贴合您', 'Complete profile': '完善个人资料', 'AI briefing': 'AI 简报', 'Based on your records': '根据您的记录', 'Continue with ZyPulse': '继续使用 ZyPulse', 'Log a reading': '记录读数', 'Add a meal': '添加膳食', 'View trends': '查看趋势', 'Ask Coach': '询问健康助手', 'Your record at a glance': '您的记录一览', 'Fasting glucose · 7 days': '空腹血糖 · 7 天', 'Medication · 30 days': '用药 · 30 天', 'Activity · 30 days': '活动 · 30 天', 'active days': '活跃天数', 'See full trends →': '查看完整趋势 →', 'Why this next step': '为什么建议这一步', 'What this cannot tell us:': '这无法说明：',
    'Record Your Self-Care': '记录您的自我照护', Glucose: '血糖', Medication: '用药', Activity: '活动', 'Reading (mmol/L)': '读数 (mmol/L)', When: '时间', 'Fasting (before breakfast)': '空腹（早餐前）', Evening: '晚上', Date: '日期', 'Notes (optional)': '备注（可选）', 'Any observations...': '任何观察…', 'Save Reading': '保存读数', 'Dose Time': '服药时间', Morning: '早上', Status: '状态', Taken: '已服用', Missed: '漏服', Skipped: '跳过', 'Save Status': '保存状态', 'Activity Type': '活动类型', Walking: '步行', Exercise: '锻炼', Stretching: '伸展', Cycling: '骑行', Swimming: '游泳', 'Duration (minutes)': '时长（分钟）', 'Location (optional)': '地点（可选）', 'Save Activity': '保存活动',
    "Hello Mr Tan! I'm ZyPulse, your self-care companion. I can help you understand your glucose trends, track your medication, and support your daily self-care routine. How can I help you today?": '您好，陈先生！我是 ZyPulse，您的自我照护伙伴。我可以帮助您了解血糖趋势、追踪用药并支持您的日常自我照护。今天有什么可以帮您？', 'ZyPulse is thinking...': 'ZyPulse 正在思考…', 'Ask about your trends, log a reading, or get self-care tips...': '询问趋势、记录读数或获取自我照护建议…',
    'Quick Meal Log': '快速膳食记录', 'Estimates are illustrative - not clinically precise': '估算仅供参考，并非临床精确结果', Meal: '膳食', breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐', 'Recent / favourites': '最近 / 收藏', 'Search food / drink': '搜索食物 / 饮料', 'e.g. chicken rice, teh tarik, water': '例如：鸡饭、拉茶、白水', 'sugary drink': '含糖饮料', remove: '移除', carbs: '碳水化合物', sugar: '糖', 'Meal total:': '膳食总计：', 'Scan photo (simulated AI)': '扫描照片（模拟 AI）', 'Note (optional)': '备注（可选）', 'Include this note in visit summary for my doctor': '在给医生的就诊摘要中包含此备注', 'Saving...': '保存中…', 'Update Meal': '更新膳食', 'Save Meal': '保存膳食', 'Cancel edit': '取消编辑', 'Logged Meals': '已记录的膳食', 'No meals logged yet.': '尚未记录膳食。', edit: '编辑', delete: '删除', Custom: '自定义', 'in visit summary': '已加入就诊摘要', meal: '膳食', 'Add at least one food or drink.': '请至少添加一种食物或饮料。', 'Meal saved.': '膳食已保存。', 'Meal updated.': '膳食已更新。', 'Meal deleted.': '膳食已删除。', 'Delete this meal entry?': '删除这条膳食记录？',
    'Editing meal': '正在编辑膳食', 'Save to update.': '保存以更新。', 'SIMULATED recognition - no real vision model is connected. Review and confirm before saving.': '模拟识别——未连接真实视觉模型。请在保存前检查并确认。', Estimated: '估算：', 'sugary drink detected': '检测到含糖饮料', 'Add to meal & review': '添加到膳食并检查', Discard: '丢弃', 'Photo analysis failed: ': '照片分析失败：', 'Simulated photo result added - review portions/values, then save.': '已添加模拟照片结果——请检查份量和数值后保存。',
    'Check in': '请留意', Building: '建立中', Steady: '稳定', 'A few records need your attention': '有几项记录需要您的关注', 'More records will make this clearer': '更多记录会让情况更清晰', 'Your recent record looks consistent': '您最近的记录看起来一致', 'This signal is based on what you logged, not a medical assessment.': '此提示基于您的记录，并非医疗评估。', 'Add your next routine record to strengthen your self-care picture.': '添加下一条日常记录，让您的自我照护概况更完整。', 'Keep logging to maintain a clear picture for yourself and your care team.': '继续记录，让您和照护团队都能清楚了解情况。', 'Add your next meal': '添加下一餐', 'Log a meal': '记录膳食', 'A quick meal entry can make your self-care record more complete.': '快速记录膳食可让您的自我照护记录更完整。', 'There are no recent meal records available, while other parts of your routine have some data.': '目前没有近期膳食记录，但您的日常其他部分已有一些数据。', 'A meal record helps build context, but it cannot show that a meal caused any glucose change.': '膳食记录可提供背景信息，但无法证明某餐造成了任何血糖变化。', 'Log an evening glucose reading': '记录晚间血糖读数', 'If it is part of your usual routine, add your next evening reading.': '如果这是您平时的习惯，请添加下一次晚间读数。', 'With limited readings, ZyPulse cannot identify a reliable trend or explain why a value changed.': '读数有限时，ZyPulse 无法识别可靠趋势或解释数值变化的原因。', 'Record your next medication status': '记录下一次用药状态', 'Log medication': '记录用药', 'A simple status check keeps your record ready for your next care conversation.': '简单的状态确认可让记录为下一次照护沟通做好准备。', 'This record cannot explain why a dose was missed or whether any health outcome was caused by it.': '这项记录无法解释漏服原因，也无法判断是否造成任何健康结果。', 'Keep your routine visible': '持续记录您的日常', 'Add a record': '添加记录', 'Add your next planned self-care record when it is convenient for you.': '方便时添加下一条计划的自我照护记录。', 'These records describe what was logged; they do not diagnose a condition or establish cause and effect.': '这些记录仅描述已记录的内容，不能诊断疾病或确定因果关系。',
    'missed dose': '漏服次数', 'Glucose Trends (7 days)': '血糖趋势（7 天）', 'Fasting average': '空腹平均值', 'Fasting range': '空腹范围', 'Fasting trend': '空腹趋势', Readings: '读数次数', 'Evening average': '晚间平均值', 'Evening range': '晚间范围', 'Evening trend': '晚间趋势', 'Medication Adherence (30 days)': '用药依从性（30 天）', 'Adherence rate': '依从率', 'Doses taken': '已服用剂次', 'Missed doses': '漏服剂次', 'Activity Summary (30 days)': '活动摘要（30 天）', 'Active days': '活跃天数', 'Total duration': '总时长', 'Average per session': '每次平均时长', 'Refresh Trends': '刷新趋势', 'Loading your trends...': '正在加载趋势…', Stable: '稳定', Increasing: '上升', Decreasing: '下降', 'Insufficient data': '数据不足', 'Below target': '低于目标',
    All: '全部', 'My History': '我的历史记录', 'Loading your history...': '正在加载历史记录…', 'No entries yet.': '暂无记录。', Note: '备注', 'Included in visit summary': '已加入就诊摘要', 'In visit summary': '已加入就诊摘要', Fasting: '空腹',
    'Nearby Sports Facilities': '附近运动场地', 'Explore sports facilities and the activities they support across Singapore.': '探索新加坡各地的运动场地及可进行的运动。', 'Filter by type': '按类型筛选', 'All types': '全部类型', Badminton: '羽毛球', Tennis: '网球', Gymnasium: '体育馆', Fitness: '健身', Search: '搜索', 'Loading activities...': '正在加载场地…', 'No activities found. Try a different filter.': '未找到场地。请尝试其他筛选条件。',     'Source: Sport Singapore via data.gov.sg. Facility availability is not shown.': '数据来源：Sport Singapore（经 data.gov.sg）。未显示场地实时可用情况。',

    // Uploaded photo retention (original image kept with the confirmed record)
    'Your uploaded photo (original)': '您上传的照片（原图）',
    'This photo was not analysed. Demo mode has no real vision AI, so nothing was read from your image.': '此照片未被分析。演示模式没有真实视觉 AI，因此未从图片中读取任何内容。',
    'Fill in the details below yourself. Your photo is saved with the entry only after you confirm.': '请自行填写以下内容。只有在您确认后，照片才会随记录一起保存。',
    'Unsupported file type. Upload a PNG, JPEG or WebP image.': '不支持的文件类型。请上传 PNG、JPEG 或 WebP 图片。',
    'Image is too large (max 8 MB).': '图片过大（最大 8 MB）。',
    'The selected file is empty.': '所选文件为空。',
    'Not a recognised demo photo. Please enter details manually below.': '不是可识别的演示照片。请在下方手动填写信息。',
    'Food or drink name': '食物或饮料名称',
    'Add another item': '再添加一项',
    'Please name every food or drink you entered.': '请为每一项食物或饮料填写名称。',
    'Entered by you - photo was not analysed': '由您填写——照片未被分析',
    Remove: '移除',
    'View original photo': '查看原始照片',

    // Healthy 365 demo integration (synthetic catalogue, no real booking)
    'Healthy 365 Activities': 'Healthy 365 活动', DEMO: '演示', 'DEMO / SYNTHETIC': '演示 / 合成数据',
    'Synthetic demo catalogue - not real Healthy 365 activities and not bookable.': '合成演示目录——并非真实的 Healthy 365 活动，也不可报名。',
    'Synthetic Healthy 365-style activities for demonstration. Ranking is deterministic and based only on your stored preferences.': '用于演示的合成 Healthy 365 风格活动。排序为确定性算法，仅基于您已保存的偏好。',
    'Recommended for You': '为您推荐', 'Nearest First': '由近到远', 'Loading demo activities...': '正在加载演示活动…', 'No demo activities available.': '暂无演示活动。',
    'View details': '查看详情', 'Add to Activity Log': '加入活动记录', Planned: '计划中', Completed: '已完成',
    'Activity type': '活动类型', 'General location': '大致位置', 'Venue area': '场地范围', 'Experience level': '经验要求', 'Not specified': '未标明',
    'Demo registration status': '演示报名状态', 'Event ID': '活动编号', 'Date / time': '日期 / 时间', Duration: '时长', min: '分钟', 'Duration not specified': '时长未标明',
    'You can edit the details before saving.': '保存前您可以修改这些内容。', 'Back to list': '返回列表', 'Continue to Healthy 365 (Demo)': '继续前往 Healthy 365（演示）',
    'A demo registration for this event is already recorded locally.': '该活动的演示报名已在本机记录。', 'Already in your Activity Log': '已在您的活动记录中',
    'Pre-filled from Healthy 365 demo event': '已根据 Healthy 365 演示活动预填', 'edit anything before saving.': '保存前可修改任何内容。',
    'Planned activities are kept separate and are not counted as completed exercise.': '计划中的活动会单独保存，不会计入已完成的运动。',
    'Planned - not counted as completed exercise': '计划中——不计入已完成的运动',
    'Average heart rate (bpm, optional)': '平均心率（次/分钟，可选）', 'Leave empty if not measured': '未测量请留空',
    'Only enter a value you measured yourself. ZyPulse does not estimate heart rate and does not judge intensity or fitness from it.': '请只填写您自己测量的数值。ZyPulse 不会估算心率，也不会据此判断运动强度或体能状况。',
    'This demo event is already in your Activity Log.': '该演示活动已在您的活动记录中。',
    'Enter a whole number between 20 and 250 bpm, or leave the field empty.': '请输入 20 到 250 之间的整数，或留空。',
    'SIMULATED EXTERNAL APP — NOT THE REAL HEALTHY 365': '模拟外部应用——并非真实的 Healthy 365',
    'Healthy 365 — simulated demo screen': 'Healthy 365 —— 模拟演示界面',
    'No Singpass, NRIC or health information is requested. Nothing is shared externally.': '不会要求 Singpass、身份证号或健康信息。不会对外共享任何数据。',
    'Register (Demo)': '报名（演示）', 'Recording demo...': '正在记录演示…',
    'Demo registration recorded locally — no actual registration was made.': '演示报名已在本机记录——并未真正完成报名。',
    'Already recorded as a demo registration': '已记录为演示报名', 'Demo confirmation': '演示确认号',
    'This is a local demo record only. It is not attendance and is not sent to Healthy 365.': '这仅是本机演示记录，不代表出席，也不会发送给 Healthy 365。',
    'Return to ZyPulse': '返回 ZyPulse', 'Avg heart rate': '平均心率', 'From demo event': '来自演示活动',
    'Group exercise': '团体运动', Strength: '力量训练',
    // Fresh Vitality: five primary destinations + Explore tabs + More list
    'Healthy365 Events': 'Healthy365 活动', 'Sports Facilities': '运动场地',
    'Explore Healthy365 Events': '浏览 Healthy365 活动', 'Find Nearby Sports Facilities': '查找附近运动场地',
    Meals: '膳食', More: '更多', Account: '账户', Explore: '探索',
    'Save question for my doctor': '保存此问题给医生', 'Why was this redirected?': '为什么被转接？',
    'Question saved to Notes for My Doctor.': '问题已保存到「给医生的备注」。',
    'Could not save that question. Please try again.': '无法保存该问题，请重试。',
    Edit: '编辑', Delete: '删除', 'Confirm delete': '确认删除', Cancel: '取消', 'Save changes': '保存修改',
  },
}

export function translateText(language, text) {
  return pageCopy[language]?.[text] || text
}
