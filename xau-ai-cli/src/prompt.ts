import { ScriptRequest } from "./types.js";

export type TemplateId = "short" | "standard" | "long";

const BASE_SYSTEM_PROMPT = `你是「金老师直播助理」，专为黄金（XAUUSD）直播间设计普通话直播讲稿。

核心原則：
- 说话像亲切的普通话真人老师，不要有机械感
- 用中國內地主播常用口語：大家、朋友們、先別急、咱們、这段行情
- 不用粤语口吻，不用港式词，不用生硬书面语
- 直接讲逻辑，不讲玄学
- 始终强调风控和仓位纪律
- 不得预测具体点位，只讲方向和结构
- 内容必须标识为「学习参考，老师最终判断」

硬性结构：
- 开头 3 秒必须有 hook
- 中间 3-5 句讲逻辑
- 至少 1 个互动问题
- 结尾 1-2 句 CTA
- 最后必须加风控提醒`;

const TEMPLATE_RULES: Record<TemplateId, { wordRange: string; extra: string }> = {
  short: {
    wordRange: "80-120 字",
    extra: "语速更快、更短句，信息密度高，结尾 CTA 要更直接。",
  },
  standard: {
    wordRange: "150-250 字",
    extra: "标准节奏：先钩子，再拆逻辑，再互动，再 CTA，再风控。",
  },
  long: {
    wordRange: "250-400 字",
    extra: "允许多一点解释，但不要啰嗦；加一段‘观众常见误区纠正’。",
  },
};

function biasDesc(biasType: ScriptRequest["biasType"]) {
  if (biasType === "up") return "目前偏多思路（等待回踩做多，不追高）";
  if (biasType === "down") return "目前偏空思路（跌破支撑看空，不抄底）";
  return "目前观望（上下没确认，适合讲仓位纪律）";
}

export function resolveTemplateId(input?: string): TemplateId {
  if (!input) return "standard";
  if (input === "short" || input === "standard" || input === "long") return input;
  return "standard";
}

export function buildPrompt(
  req: ScriptRequest,
  opts?: { template?: TemplateId },
): { system: string; user: string } {
  const template = opts?.template ?? "standard";
  const rules = TEMPLATE_RULES[template];

  const system = `${BASE_SYSTEM_PROMPT}\n\n输出要求：\n- 总字数：${rules.wordRange}\n- ${rules.extra}`;

  const user = `当前行情状态：
- 信号类型：${biasDesc(req.biasType)}
- 动能评分：${req.momentum ?? "(未提供)"}/100
- 位置评分：${req.position ?? "(未提供)"}/100
- 风控评分：${req.risk ?? "(未提供)"}/100
- 时间框架：${req.frame || "M5"}
- 直播主题：${req.topic || "今日黄金直播重点"}
- 行动引导：${req.cta || "留言“黄金”领取重点"}
- 账号风格：${req.accountStyle || "educational"}
${req.support ? `- 关键支撑：${req.support}` : ""}
${req.resistance ? `- 关键压力：${req.resistance}` : ""}

请按模板要求生成一段直播讲稿。`;

  return { system, user };
}
