const copy = {
  en: {
    chooseLanguage: 'Choose your language', welcome: 'Welcome to ZyPulse', languageIntro: 'Choose a language to continue. You can change it later in your profile.', continue: 'Continue',
    safety: 'ZyPulse is a self-care support prototype, not a medical device. Consult your doctor for medical advice.',
    today: 'Today', coach: 'Coach', log: 'Log', meals: 'Meals', trends: 'Trends', connect: 'Connect', history: 'History', profile: 'Profile',
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
    'Preparing your daily briefing...': '正在准备您的每日简报…', 'YOUR DAILY BRIEFING': '您的每日简报', 'Good day, Mr Tan': '您好，陈先生', 'Your verified self-care snapshot, in one place.': '在这里查看您的自我照护记录概览。',
    "TODAY'S HEALTH RISK CHECK": '今日健康记录检查', attention: '关注', 'ONE SMALL THING FOR TODAY': '今天的一件小事', 'Make your briefing more personal': '让您的简报更贴合您', 'Complete profile': '完善个人资料', 'AI briefing': 'AI 简报', 'Based on your records': '根据您的记录', 'Continue with ZyPulse': '继续使用 ZyPulse', 'Log a reading': '记录读数', 'Add a meal': '添加膳食', 'View trends': '查看趋势', 'Ask Coach': '询问健康助手', 'Your record at a glance': '您的记录一览', 'Fasting glucose · 7 days': '空腹血糖 · 7 天', 'Medication · 30 days': '用药 · 30 天', 'Activity · 30 days': '活动 · 30 天', 'active days': '活跃天数', 'See full trends →': '查看完整趋势 →', 'Why this next step': '为什么建议这一步', 'What this cannot tell us:': '这无法说明：',
    'Record Your Self-Care': '记录您的自我照护', Glucose: '血糖', Medication: '用药', Activity: '活动', 'Reading (mmol/L)': '读数 (mmol/L)', When: '时间', 'Fasting (before breakfast)': '空腹（早餐前）', Evening: '晚上', Date: '日期', 'Notes (optional)': '备注（可选）', 'Any observations...': '任何观察…', 'Save Reading': '保存读数', 'Dose Time': '服药时间', Morning: '早上', Status: '状态', Taken: '已服用', Missed: '漏服', Skipped: '跳过', 'Save Status': '保存状态', 'Activity Type': '活动类型', Walking: '步行', Exercise: '锻炼', Stretching: '伸展', Cycling: '骑行', Swimming: '游泳', 'Duration (minutes)': '时长（分钟）', 'Location (optional)': '地点（可选）', 'Save Activity': '保存活动',
    "Hello Mr Tan! I'm ZyPulse, your self-care companion. I can help you understand your glucose trends, track your medication, and support your daily self-care routine. How can I help you today?": '您好，陈先生！我是 ZyPulse，您的自我照护伙伴。我可以帮助您了解血糖趋势、追踪用药并支持您的日常自我照护。今天有什么可以帮您？', 'ZyPulse is thinking...': 'ZyPulse 正在思考…', 'Ask about your trends, log a reading, or get self-care tips...': '询问趋势、记录读数或获取自我照护建议…',
    'Quick Meal Log': '快速膳食记录', 'Estimates are illustrative - not clinically precise': '估算仅供参考，并非临床精确结果', Meal: '膳食', breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐', 'Recent / favourites': '最近 / 收藏', 'Search food / drink': '搜索食物 / 饮料', 'e.g. chicken rice, teh tarik, water': '例如：鸡饭、拉茶、白水', 'sugary drink': '含糖饮料', remove: '移除', carbs: '碳水化合物', sugar: '糖', 'Meal total:': '膳食总计：', 'Scan photo (simulated AI)': '扫描照片（模拟 AI）', 'Note (optional)': '备注（可选）', 'Include this note in visit summary for my doctor': '在给医生的就诊摘要中包含此备注', 'Saving...': '保存中…', 'Update Meal': '更新膳食', 'Save Meal': '保存膳食', 'Cancel edit': '取消编辑', 'Logged Meals': '已记录的膳食', 'No meals logged yet.': '尚未记录膳食。', edit: '编辑', delete: '删除', Custom: '自定义', 'in visit summary': '已加入就诊摘要', meal: '膳食', 'Add at least one food or drink.': '请至少添加一种食物或饮料。', 'Meal saved.': '膳食已保存。', 'Meal updated.': '膳食已更新。', 'Meal deleted.': '膳食已删除。', 'Delete this meal entry?': '删除这条膳食记录？',
    'Editing meal': '正在编辑膳食', 'Save to update.': '保存以更新。', 'SIMULATED recognition - no real vision model is connected. Review and confirm before saving.': '模拟识别——未连接真实视觉模型。请在保存前检查并确认。', Estimated: '估算：', 'sugary drink detected': '检测到含糖饮料', 'Add to meal & review': '添加到膳食并检查', Discard: '丢弃', 'Photo analysis failed: ': '照片分析失败：', 'Simulated photo result added - review portions/values, then save.': '已添加模拟照片结果——请检查份量和数值后保存。',
    'Check in': '请留意', Building: '建立中', Steady: '稳定', 'A few records need your attention': '有几项记录需要您的关注', 'More records will make this clearer': '更多记录会让情况更清晰', 'Your recent record looks consistent': '您最近的记录看起来一致', 'This signal is based on what you logged, not a medical assessment.': '此提示基于您的记录，并非医疗评估。', 'Add your next routine record to strengthen your self-care picture.': '添加下一条日常记录，让您的自我照护概况更完整。', 'Keep logging to maintain a clear picture for yourself and your care team.': '继续记录，让您和照护团队都能清楚了解情况。', 'Add your next meal': '添加下一餐', 'Log a meal': '记录膳食', 'A quick meal entry can make your self-care record more complete.': '快速记录膳食可让您的自我照护记录更完整。', 'There are no recent meal records available, while other parts of your routine have some data.': '目前没有近期膳食记录，但您的日常其他部分已有一些数据。', 'A meal record helps build context, but it cannot show that a meal caused any glucose change.': '膳食记录可提供背景信息，但无法证明某餐造成了任何血糖变化。', 'Log an evening glucose reading': '记录晚间血糖读数', 'If it is part of your usual routine, add your next evening reading.': '如果这是您平时的习惯，请添加下一次晚间读数。', 'With limited readings, ZyPulse cannot identify a reliable trend or explain why a value changed.': '读数有限时，ZyPulse 无法识别可靠趋势或解释数值变化的原因。', 'Record your next medication status': '记录下一次用药状态', 'Log medication': '记录用药', 'A simple status check keeps your record ready for your next care conversation.': '简单的状态确认可让记录为下一次照护沟通做好准备。', 'This record cannot explain why a dose was missed or whether any health outcome was caused by it.': '这项记录无法解释漏服原因，也无法判断是否造成任何健康结果。', 'Keep your routine visible': '持续记录您的日常', 'Add a record': '添加记录', 'Add your next planned self-care record when it is convenient for you.': '方便时添加下一条计划的自我照护记录。', 'These records describe what was logged; they do not diagnose a condition or establish cause and effect.': '这些记录仅描述已记录的内容，不能诊断疾病或确定因果关系。',
    'missed dose': '漏服次数', 'Glucose Trends (7 days)': '血糖趋势（7 天）', 'Fasting average': '空腹平均值', 'Fasting range': '空腹范围', 'Fasting trend': '空腹趋势', Readings: '读数次数', 'Evening average': '晚间平均值', 'Evening range': '晚间范围', 'Evening trend': '晚间趋势', 'Medication Adherence (30 days)': '用药依从性（30 天）', 'Adherence rate': '依从率', 'Doses taken': '已服用剂次', 'Missed doses': '漏服剂次', 'Activity Summary (30 days)': '活动摘要（30 天）', 'Active days': '活跃天数', 'Total duration': '总时长', 'Average per session': '每次平均时长', 'Refresh Trends': '刷新趋势', 'Loading your trends...': '正在加载趋势…', Stable: '稳定', Increasing: '上升', Decreasing: '下降', 'Insufficient data': '数据不足', 'Below target': '低于目标',
    All: '全部', 'My History': '我的历史记录', 'Loading your history...': '正在加载历史记录…', 'No entries yet.': '暂无记录。', Note: '备注', Meal: '膳食', 'Included in visit summary': '已加入就诊摘要', 'In visit summary': '已加入就诊摘要', Fasting: '空腹', Evening: '晚上', Morning: '早上',
    'Nearby Sports Facilities': '附近运动场地', 'Explore sports facilities and the activities they support across Singapore.': '探索新加坡各地的运动场地及可进行的运动。', 'Filter by type': '按类型筛选', 'All types': '全部类型', Badminton: '羽毛球', Swimming: '游泳', Tennis: '网球', Gymnasium: '体育馆', Fitness: '健身', Search: '搜索', 'Loading activities...': '正在加载场地…', 'No activities found. Try a different filter.': '未找到场地。请尝试其他筛选条件。', 'Source: Sport Singapore via data.gov.sg. Facility availability is not shown.': '数据来源：Sport Singapore（经 data.gov.sg）。未显示场地实时可用情况。',
  },
}

export function translateText(language, text) {
  return pageCopy[language]?.[text] || text
}
